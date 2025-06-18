import json
import requests
from datetime import datetime
from spending_monitor import SpendingMonitor

def test_spending_monitor():
    """Test the spending monitor with sample data"""
    monitor = SpendingMonitor()
    
    # Sample webhook data that would come from Helicone
    sample_webhook_data = {
        "request_id": f"test-request-{datetime.now().timestamp()}",
        "user_id": "test-user-123",
        "model": "gpt-4",
        "provider": "openai",
        "metadata": {
            "cost": 0.05,  # $0.05 per request
            "promptTokens": 100,
            "completionTokens": 50,
            "totalTokens": 150,
            "latencyMs": 1200
        }
    }
    
    print("🧪 Testing spending monitor...")
    print(f"Sample cost per request: ${sample_webhook_data['metadata']['cost']}")
    print(f"Hourly limit: ${monitor.hourly_limit}")
    
    # Process multiple requests to exceed the limit
    requests_to_send = int(monitor.hourly_limit / sample_webhook_data['metadata']['cost']) + 5
    print(f"Sending {requests_to_send} requests to exceed limit...")
    
    for i in range(requests_to_send):
        # Create unique request ID for each test
        test_data = sample_webhook_data.copy()
        test_data['request_id'] = f"test-request-{datetime.now().timestamp()}-{i}"
        
        success = monitor.process_webhook_data(test_data)
        print(f"Request {i+1}: {'✅' if success else '❌'}")
        
        # Add small delay to see progression
        import time
        time.sleep(0.1)
    
    # Get spending summary
    summary = monitor.get_spending_summary(1)  # Last 1 hour
    print("\n📊 Spending Summary:")
    print(f"Total requests: {summary.get('total_requests', 0)}")
    print(f"Total cost: ${summary.get('total_cost', 0):.4f}")
    print(f"Average cost per request: ${summary.get('avg_cost_per_request', 0):.4f}")

def test_webhook_endpoint():
    """Test the webhook endpoint locally"""
    webhook_url = ""
    
    # Sample webhook payload
    payload = {
        "request_id": f"webhook-test-{datetime.now().timestamp()}",
        "user_id": "webhook-test-user",
        "model": "gpt-3.5-turbo",
        "provider": "openai",
        "metadata": {
            "cost": 0.002,
            "promptTokens": 50,
            "completionTokens": 25,
            "totalTokens": 75,
            "latencyMs": 800
        }
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Webhook test response: {response.status_code}")
        print(f"Response body: {response.text}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to webhook endpoint. Make sure the server is running.")
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")

if __name__ == "__main__":
    print("🧪 Running tests...")
    
    # Test the spending monitor logic
    test_spending_monitor()
    
    print("\n" + "="*50)
    
    # Test the webhook endpoint (requires server to be running)
    print("Testing webhook endpoint...")
    test_webhook_endpoint()