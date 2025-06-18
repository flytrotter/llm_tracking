# Helicone Spending Monitor 💰

A real-time spending monitoring system for Helicone AI requests that automatically tracks your usage costs and sends alerts when you approach spending limits.

## 🌟 Features

- **Real-time monitoring**: Track spending as requests come in via webhooks
- **Configurable alerts**: Set hourly/daily spending limits with automatic notifications
- **Database logging**: Persistent storage of all requests and spending data
- **REST API**: Query spending data and statistics
- **Easy setup**: Simple configuration with environment variables
- **Testing tools**: Built-in scripts to test your setup

## 🏗️ How It Works

1. **Webhook Integration**: Helicone sends request data to your monitoring server via webhooks
2. **Cost Calculation**: The system processes each request and tracks associated costs
3. **Limit Checking**: Compares current spending against your configured limits
4. **Alert System**: Sends notifications when limits are exceeded
5. **Data Storage**: Stores all data in a SQLite database for historical analysis

## 📋 Prerequisites

- Python 3.8 or higher
- A Helicone account ([sign up here](https://helicone.ai))
- ngrok account for webhook testing (optional but recommended)

## 🚀 Quick Start

### Step 1: Clone and Setup

```bash
# Clone or download the project
cd helicone_martini

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn requests python-dotenv ngrok
```

### Step 2: Create Environment Configuration

Create a `.env` file in the project root with your configuration:

```env
EMAIL_USERNAME=<sender email>
EMAIL_PASSWORD=<apps password>
ALERT_EMAIL_TO=<recipient email>
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

HELICONE_API_KEY=<from helicone>
HELICONE_WEBHOOK_SECRET=<configure helicone webhook>
HOURLY_SPEND_LIMIT=10.00

# Slack Configuration
SLACK_WEBHOOK_URL=your_slack_webhook_url_here

# Database
DATABASE_PATH=spending_monitor.db

NGROK_AUTHTOKEN=<for testing>

HOST=<your host>
PORT=<your port>
```

### Step 3: Setup Helicone Webhook

1. **Visit the Helicone Dashboard**: Go to [https://us.helicone.ai/webhooks](https://us.helicone.ai/webhooks)

2. **Create a New Webhook**:
   - Click "Create Webhook" or similar button
   - Set the webhook URL (we'll get this in Step 4)
   - **IMPORTANT**: Copy the HMAC secret key provided
   - Paste this HMAC secret as `HELICONE_WEBHOOK_SECRET` in your `.env` file

3. **Configure Events**: Select the events you want to monitor (typically all request events)

### Step 4: Get Your Webhook URL

#### Option A: Using ngrok (Recommended for Testing)

```bash
# Make sure ngrok is installed and you have an auth token
# Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken

# Start the monitoring server
python run.py
```

In another terminal:
```bash
# Start ngrok tunnel (adjust port if you changed it in .env)
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`) and use this as your webhook URL in Helicone.

#### Option B: Deploy to Production Server

If deploying to a production server, use your server's public URL:
```
https://yourdomain.com/webhook
```

### Step 5: Update Webhook URL in Helicone

1. Go back to [https://us.helicone.ai/webhooks](https://us.helicone.ai/webhooks)
2. Edit your webhook configuration
3. Set the URL to your ngrok URL + `/webhook` (e.g., `https://abc123.ngrok-free.app/webhook`)
4. Save the configuration

### Step 6: Start Monitoring

```bash
# Start the server
python run.py
```

You should see output like:
```
🚀 Starting Helicone Spending Monitor...
✅ All checks passed!
🌐 Starting server on 0.0.0.0:8000
📊 Webhook endpoint: http://0.0.0.0:8000/webhook
🔧 Press Ctrl+C to stop the server
```

## 🧪 Testing Your Setup

### Test 1: Local Testing

```bash
# Run the test script
python test_script.py
```

This will:
- Test the spending monitor logic
- Simulate webhook requests
- Show spending summaries

### Test 2: Webhook Endpoint Testing

1. Make sure your server is running (`python run.py`)
2. Update the `webhook_url` in `test_script.py` with your ngrok URL
3. Run the test script again

### Test 3: Live Testing

1. Make some actual requests through Helicone in your application
2. Check your server logs for incoming webhook data
3. Verify spending is being tracked correctly

## 📊 Monitoring and Usage

### View Real-time Logs

Your server will log all incoming requests:
```
INFO: Request processed - Cost: $0.002, Total hourly: $0.15
WARNING: Approaching hourly limit - $4.80 of $5.00 used
ALERT: Hourly spending limit exceeded! $5.20 of $5.00
```

### API Endpoints

The server provides several endpoints for monitoring:

```bash
# Get spending summary for last hour
curl http://localhost:8000/spending/summary?hours=1

# Get all requests from last 24 hours
curl http://localhost:8000/requests?hours=24

# Health check
curl http://localhost:8000/health
```

### Database Queries

Data is stored in `spending.db`. You can query it directly:

```python
import sqlite3

conn = sqlite3.connect('spending.db')
cursor = conn.cursor()

# Get total spending today
cursor.execute("""
    SELECT SUM(cost) FROM requests 
    WHERE date(timestamp) = date('now')
""")
result = cursor.fetchone()
print(f"Today's spending: ${result[0]:.4f}")
```

## ⚠️ Production Deployment

### Security Considerations

1. **Use HTTPS**: Always use HTTPS endpoints for webhooks
2. **Validate Webhook Signatures**: The system validates HMAC signatures
3. **Environment Variables**: Never commit your `.env` file
4. **Firewall Rules**: Restrict access to your webhook endpoint

### Recommended Production Setup

1. **Use a VPS or Cloud Provider**: Deploy on AWS, DigitalOcean, etc.
2. **Use a Reverse Proxy**: nginx or Apache for HTTPS termination
3. **Process Manager**: Use systemd, PM2, or similar to keep the service running
4. **Database Backup**: Regular backups of your spending.db file
5. **Log Rotation**: Configure log rotation for long-running instances

### Environment Variables for Production

```env
# Production configuration
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@localhost/helicone_monitor  # Optional: Use PostgreSQL
REDIS_URL=redis://localhost:6379  # Optional: For caching
```

## 🔧 Customization

### Adjust Spending Limits

Edit your `.env` file:
```env
HOURLY_SPEND_LIMIT=10.00    # $10 per hour
DAILY_SPEND_LIMIT=100.00    # $100 per day
MONTHLY_SPEND_LIMIT=1000.00 # $1000 per month
```

### Custom Alert Channels

The system supports multiple alert methods. Configure in your `.env`:

```env
# Email alerts
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Slack alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Discord alerts
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK
```

### Custom Cost Calculation

Modify `spending_monitor.py` to implement custom cost calculation logic:

```python
def calculate_custom_cost(self, metadata):
    """Custom cost calculation based on your pricing model"""
    # Implement your custom logic here
    return metadata.get('cost', 0)
```

## 🐛 Troubleshooting

### Common Issues

1. **Webhook not receiving data**:
   - Check your ngrok URL is correct
   - Verify HMAC secret matches
   - Check Helicone webhook configuration

2. **Server won't start**:
   - Check all environment variables are set
   - Verify port isn't already in use
   - Check Python dependencies are installed

3. **Database errors**:
   - Ensure write permissions in project directory
   - Check disk space availability

4. **Cost tracking seems wrong**:
   - Verify Helicone is sending cost data in metadata
   - Check currency settings match your expectations

### Debug Mode

Run with debug logging:
```bash
DEBUG=true python run.py
```

### Getting Help

1. Check the logs in your terminal
2. Verify your `.env` configuration
3. Test with the provided test scripts
4. Check Helicone dashboard for webhook delivery status

## 📝 File Structure

```
helicone_martini/
├── run.py              # Main server startup script
├── main.py             # Core application logic  
├── spending_monitor.py # Spending tracking logic
├── database.py         # Database operations
├── alerts.py           # Alert system
├── test_script.py      # Testing utilities
├── .env               # Environment configuration (create this)
├── spending.db        # SQLite database (auto-created)
└── README.md          # This file
```

## 🤝 Contributing

Feel free to submit issues, feature requests, and pull requests to improve this monitoring system.

## 📄 License

This project is open source. Use it responsibly and ensure you comply with Helicone's terms of service.

---

**Need Help?** Create an issue or check the troubleshooting section above. Happy monitoring! 🎉
