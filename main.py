import os
import json
import hmac
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
import requests
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

load_dotenv()

app = FastAPI()

# Configuration
WEBHOOK_SECRET = os.getenv("HELICONE_WEBHOOK_SECRET")
HOURLY_THRESHOLD = float(os.getenv("HOURLY_SPENDING_THRESHOLD", "10.00"))
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

class SpendingTracker:
    def __init__(self, db_path: str = "spending.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for tracking spending"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spending_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE,
                timestamp DATETIME,
                hour_bucket TEXT,
                cost REAL,
                model TEXT,
                user_id TEXT,
                tokens_total INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour_bucket TEXT UNIQUE,
                total_cost REAL,
                alert_sent BOOLEAN DEFAULT FALSE,
                alert_sent_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_hour_bucket(self, timestamp: datetime) -> str:
        """Get hour bucket string (YYYY-MM-DD-HH format)"""
        return timestamp.strftime("%Y-%m-%d-%H")
    
    def log_spending(self, request_data: Dict) -> float:
        """Log spending and return current hourly total"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            timestamp = datetime.now()
            hour_bucket = self.get_hour_bucket(timestamp)
            
            # Extract data from webhook
            request_id = request_data.get("request_id")
            cost = request_data.get("metadata", {}).get("cost", 0.0)
            model = request_data.get("model", "unknown")
            user_id = request_data.get("user_id")
            total_tokens = request_data.get("metadata", {}).get("totalTokens", 0)
            
            # Insert spending record
            cursor.execute("""
                INSERT OR REPLACE INTO spending_log 
                (request_id, timestamp, hour_bucket, cost, model, user_id, tokens_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (request_id, timestamp, hour_bucket, cost, model, user_id, total_tokens))
            
            # Calculate current hourly total
            cursor.execute("""
                SELECT SUM(cost) FROM spending_log 
                WHERE hour_bucket = ?
            """, (hour_bucket,))
            
            hourly_total = cursor.fetchone()[0] or 0.0
            
            # Update hourly summary
            cursor.execute("""
                INSERT OR REPLACE INTO hourly_alerts 
                (hour_bucket, total_cost)
                VALUES (?, ?)
            """, (hour_bucket, hourly_total))
            
            conn.commit()
            return hourly_total
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def check_and_send_alert(self, hour_bucket: str, current_total: float) -> bool:
        """Check if alert should be sent and send it"""
        if current_total <= HOURLY_THRESHOLD:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if alert already sent for this hour
            cursor.execute("""
                SELECT alert_sent FROM hourly_alerts 
                WHERE hour_bucket = ? AND alert_sent = TRUE
            """, (hour_bucket,))
            
            if cursor.fetchone():
                return False  # Alert already sent
            
            # Send alert
            alert_sent = self.send_alert(hour_bucket, current_total)
            
            if alert_sent:
                # Mark alert as sent
                cursor.execute("""
                    UPDATE hourly_alerts 
                    SET alert_sent = TRUE, alert_sent_at = CURRENT_TIMESTAMP
                    WHERE hour_bucket = ?
                """, (hour_bucket,))
                conn.commit()
            
            return alert_sent
            
        finally:
            conn.close()
    
    def send_alert(self, hour_bucket: str, current_total: float) -> bool:
        """Send alert via multiple channels"""
        message = f"""
🚨 SPENDING ALERT 🚨

Hourly spending threshold exceeded!

📊 Details:
• Hour: {hour_bucket}
• Current Total: ${current_total:.4f}
• Threshold: ${HOURLY_THRESHOLD:.2f}
• Overage: ${current_total - HOURLY_THRESHOLD:.4f}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        success = False
        
        # Send Slack notification
        if SLACK_WEBHOOK_URL:
            success |= self.send_slack_alert(message)
        
        # Send email notification
        if EMAIL_USERNAME and EMAIL_PASSWORD:
            success |= self.send_email_alert(message, hour_bucket, current_total)
        
        # Log to console
        print(f"ALERT: {message}")
        
        return success
    
    def send_slack_alert(self, message: str) -> bool:
        """Send alert to Slack"""
        try:
            payload = {
                "text": message,
                "username": "Helicone Spending Bot",
                "icon_emoji": ":warning:"
            }
            
            response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return False
    
    def send_email_alert(self, message: str, hour_bucket: str, current_total: float) -> bool:
        """Send email alert"""
        try:
            msg = MimeMultipart()
            msg['From'] = EMAIL_USERNAME
            msg['To'] = EMAIL_USERNAME  # Send to yourself
            msg['Subject'] = f"Helicone Spending Alert - ${current_total:.2f} in hour {hour_bucket}"
            
            msg.attach(MimeText(message, 'plain'))
            
            server = smtplib.SMTP(EMAIL_SMTP_SERVER, 587)
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_USERNAME, EMAIL_USERNAME, text)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False
    
    def get_hourly_summary(self, hours_back: int = 24) -> List[Dict]:
        """Get spending summary for the last N hours"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                hour_bucket,
                total_cost,
                alert_sent,
                COUNT(*) as request_count
            FROM hourly_alerts h
            LEFT JOIN spending_log s ON h.hour_bucket = s.hour_bucket
            WHERE h.hour_bucket >= datetime('now', '-{} hours')
            GROUP BY h.hour_bucket, h.total_cost, h.alert_sent
            ORDER BY h.hour_bucket DESC
        """.format(hours_back))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "hour": row[0],
                "total_cost": row[1],
                "alert_sent": bool(row[2]),
                "request_count": row[3]
            })
        
        conn.close()
        return results

# Initialize tracker
tracker = SpendingTracker()

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature from Helicone"""
    if not WEBHOOK_SECRET:
        print("Warning: No webhook secret configured")
        return True  # Allow for testing
    
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle incoming webhooks from Helicone"""
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get("helicone-signature", "")
        
        # Verify signature
        if not verify_webhook_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON
        webhook_data = json.loads(body.decode())
        
        # Log spending
        hour_bucket = tracker.get_hour_bucket(datetime.now())
        current_total = tracker.log_spending(webhook_data)
        
        # Check for alerts
        alert_sent = tracker.check_and_send_alert(hour_bucket, current_total)
        
        print(f"Request logged: ${webhook_data.get('metadata', {}).get('cost', 0):.4f}, "
              f"Hourly total: ${current_total:.4f}, Alert sent: {alert_sent}")
        
        return JSONResponse({
            "status": "success",
            "hourly_total": current_total,
            "threshold": HOURLY_THRESHOLD,
            "alert_sent": alert_sent
        })
        
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "threshold": HOURLY_THRESHOLD}

@app.get("/summary")
async def get_summary():
    """Get spending summary"""
    summary = tracker.get_hourly_summary(24)
    return {
        "threshold": HOURLY_THRESHOLD,
        "last_24_hours": summary
    }

if __name__ == "__main__":
    print(f"Starting Helicone spending tracker with ${HOURLY_THRESHOLD} hourly threshold")
    uvicorn.run(app, host="0.0.0.0", port=8000)