import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from database import SpendingDatabase
from alerts import AlertSystem
from dotenv import load_dotenv

load_dotenv()

class SpendingMonitor:
    def __init__(self):
        self.db = SpendingDatabase()
        self.alert_system = AlertSystem()
        self.hourly_limit = float(os.getenv('HOURLY_SPEND_LIMIT', 10.0))
    
    def process_webhook_data(self, webhook_data: Dict) -> bool:
        """Process incoming webhook data and check for spending limits"""
        try:
            # Extract cost information from webhook metadata
            metadata = webhook_data.get('metadata', {})
            cost = metadata.get('cost', 0.0)
            
            if cost <= 0:
                print("No cost data in webhook, skipping...")
                return True
            
            # Prepare request data for database
            request_data = {
                'request_id': webhook_data.get('request_id'),
                'timestamp': datetime.now(),
                'cost_usd': cost,
                'model': webhook_data.get('model'),
                'provider': webhook_data.get('provider'),
                'user_id': webhook_data.get('user_id'),
                'tokens_total': metadata.get('totalTokens')
            }
            
            # Add to database
            # Add to database
            if not self.db.add_request(request_data):
                print("Request already processed, skipping...")
                return True
            
            # Get the current hour (rounded down)
            current_hour = self.get_current_hour()
            
            # Update hourly aggregate and get total spending
            total_hourly_spend = self.db.update_hourly_aggregate(current_hour)
            
            print(f"Current hour: {current_hour}")
            print(f"Total hourly spend: ${total_hourly_spend:.4f}")
            print(f"Hourly limit: ${self.hourly_limit:.2f}")
            
            # Check if limit is exceeded
            if total_hourly_spend > self.hourly_limit:
                self.handle_limit_exceeded(current_hour, total_hourly_spend)
            
            return True
            
        except Exception as e:
            print(f"Error processing webhook data: {e}")
            return False
    
    def get_current_hour(self) -> datetime:
        """Get the current hour rounded down (e.g., 14:35 -> 14:00)"""
        now = datetime.now()
        return now.replace(minute=0, second=0, microsecond=0)
    
    def handle_limit_exceeded(self, hour_start: datetime, total_spend: float):
        """Handle when spending limit is exceeded"""
        alert_type = "hourly_limit_exceeded"
        
        # Check if we already sent an alert for this hour
        if self.db.was_alert_sent(hour_start, alert_type):
            print(f"Alert already sent for hour {hour_start}, skipping...")
            return
        
        overage = total_spend - self.hourly_limit
        
        # Get request count for this hour
        hour_end = hour_start + timedelta(hours=1)
        request_count = self.get_request_count_for_hour(hour_start, hour_end)
        
        spending_data = {
            'hour_start': hour_start,
            'total_spend': total_spend,
            'limit': self.hourly_limit,
            'overage': overage,
            'request_count': request_count
        }
        
        print(f"🚨 ALERT: Hourly spending limit exceeded!")
        print(f"Hour: {hour_start}")
        print(f"Spend: ${total_spend:.4f} (Limit: ${self.hourly_limit:.2f})")
        print(f"Overage: ${overage:.4f}")
        
        # Send alerts
        alert_results = self.alert_system.send_alerts(spending_data)
        
        # Record that alerts were sent (even if they failed)
        self.db.record_alert_sent(
            hour_start, alert_type, total_spend, overage
        )
        
        print(f"Alert results: {alert_results}")
    
    def get_request_count_for_hour(self, hour_start: datetime, hour_end: datetime) -> int:
        """Get the number of requests for a specific hour"""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM api_requests 
            WHERE timestamp >= ? AND timestamp < ?
        ''', (hour_start, hour_end))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def get_spending_summary(self, hours_back: int = 24) -> Dict:
        """Get spending summary for the last N hours"""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        start_time = datetime.now() - timedelta(hours=hours_back)
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(SUM(cost_usd), 0) as total_cost,
                COALESCE(AVG(cost_usd), 0) as avg_cost_per_request,
                MIN(timestamp) as first_request,
                MAX(timestamp) as last_request
            FROM api_requests 
            WHERE timestamp >= ?
        ''', (start_time,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_requests': result[0],
                'total_cost': result[1],
                'avg_cost_per_request': result[2],
                'first_request': result[3],
                'last_request': result[4],
                'hours_analyzed': hours_back
            }
        
        return {}