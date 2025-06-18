import os
import json
import hmac
import hashlib
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from spending_monitor import SpendingMonitor
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Helicone Spending Monitor", version="1.0.0")
monitor = SpendingMonitor()

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the webhook signature from Helicone"""
    if not signature or not secret:
        return False
    
    # Create HMAC signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures securely
    return hmac.compare_digest(expected_signature, signature)

@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming webhooks from Helicone"""
    try:
        # Get the raw body and signature
        body = await request.body()
        signature = request.headers.get("helicone-signature")
        webhook_secret = os.getenv("HELICONE_WEBHOOK_SECRET")
        
        # Verify the signature
        if not verify_webhook_signature(body, signature, webhook_secret):
            print("❌ Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse the JSON payload
        try:
            webhook_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        print(f"✅ Received valid webhook at {datetime.now()}")
        print(f"Request ID: {webhook_data.get('request_id', 'N/A')}")
        
        # Process the webhook data
        success = monitor.process_webhook_data(webhook_data)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={"message": "Webhook processed successfully"}
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"message": "Failed to process webhook"}
            )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error processing webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"}
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/spending-summary")
async def get_spending_summary(hours: int = 24):
    """Get spending summary for the last N hours"""
    try:
        summary = monitor.get_spending_summary(hours)
        return {
            "status": "success",
            "data": summary,
            "hourly_limit": monitor.hourly_limit
        }
    except Exception as e:
        print(f"Error getting spending summary: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get spending summary"}
        )

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "Helicone Spending Monitor",
        "version": "1.0.0",
        "status": "running",
        "hourly_limit": monitor.hourly_limit,
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health",
            "spending_summary": "/spending-summary"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting Helicone Spending Monitor on {host}:{port}")
    print(f"💰 Hourly spending limit: ${monitor.hourly_limit:.2f}")
    
    uvicorn.run(app, host=host, port=port)