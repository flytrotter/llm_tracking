import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class AlertSystem:
    def __init__(self):
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.email_username = os.getenv('EMAIL_USERNAME')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.alert_email_to = os.getenv('ALERT_EMAIL_TO')
    
    def send_slack_alert(self, spending_data: Dict) -> bool:
        """Send alert to Slack"""
        if not self.slack_webhook_url:
            print("Slack webhook URL not configured")
            return False
        
        try:
            message = self._format_slack_message(spending_data)
            
            payload = {
                "text": "🚨 API Spending Alert",
                "attachments": [
                    {
                        "color": "danger",
                        "fields": [
                            {
                                "title": "Hourly Spend Limit Exceeded",
                                "value": message,
                                "short": False
                            }
                        ],
                        "footer": "Helicone Spending Monitor",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook_url, json=payload)
            response.raise_for_status()
            
            print("Slack alert sent successfully")
            return True
            
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return False
    
    def send_email_alert(self, spending_data: Dict) -> bool:
        """Send alert via email"""
        if not all([self.smtp_server, self.email_username, self.email_password, self.alert_email_to]):
            print("Email configuration incomplete")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_username
            msg['To'] = self.alert_email_to
            msg['Subject'] = "🚨 API Spending Alert - Hourly Limit Exceeded"
            
            body = self._format_email_message(spending_data)
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_username, self.email_password)
            
            text = msg.as_string()
            server.sendmail(self.email_username, self.alert_email_to, text)
            server.quit()
            
            print("Email alert sent successfully")
            return True
            
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False
    
    def _format_slack_message(self, data: Dict) -> str:
        """Format message for Slack"""
        return f"""
*Hour:* {data['hour_start'].strftime('%Y-%m-%d %H:00')}
*Total Spend:* ${data['total_spend']:.4f}
*Limit:* ${data['limit']:.2f}
*Overage:* ${data['overage']:.4f}
*Request Count:* {data.get('request_count', 'N/A')}

Your API spending has exceeded the hourly limit. Please review your usage.
        """.strip()
    
    def _format_email_message(self, data: Dict) -> str:
        """Format message for email"""
        return f"""
        <html>
        <body>
            <h2 style="color: #d32f2f;">🚨 API Spending Alert</h2>
            <p>Your API spending has exceeded the hourly limit.</p>
            
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Hour</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{data['hour_start'].strftime('%Y-%m-%d %H:00')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Total Spend</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${data['total_spend']:.4f}</td>
                </tr>
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Hourly Limit</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${data['limit']:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Overage</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: #d32f2f;"><strong>${data['overage']:.4f}</strong></td>
                </tr>
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Request Count</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{data.get('request_count', 'N/A')}</td>
                </tr>
            </table>
            
            <p style="margin-top: 20px;">
                <strong>Action Required:</strong> Please review your API usage and consider implementing rate limiting or optimizing your requests.
            </p>
            
            <p style="color: #666; font-size: 12px;">
                This alert was generated by your Helicone Spending Monitor at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
        </html>
        """

    def send_alerts(self, spending_data: Dict) -> Dict[str, bool]:
        """Send both Slack and email alerts"""
        results = {
            'slack': self.send_slack_alert(spending_data),
            'email': self.send_email_alert(spending_data)
        }
        return results