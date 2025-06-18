#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = [
        'fastapi', 'uvicorn', 'requests', 'dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print(f"Install them with: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Create a .env file with the required configuration.")
        return False
    
    required_vars = [
        'HELICONE_API_KEY',
        'HELICONE_WEBHOOK_SECRET',
        'HOURLY_SPEND_LIMIT'
    ]
    
    missing_vars = []
    with open('.env', 'r') as f:
        env_content = f.read()
        for var in required_vars:
            if f"{var}=" not in env_content:
                missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def main():
    print("🚀 Starting Helicone Spending Monitor...")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not check_env_file():
        sys.exit(1)
    
    print("✅ All checks passed!")
    
    # Start the webhook server
    try:
        from webhook_server import app
        import uvicorn
        
        port = int(os.getenv("PORT", 8000))
        host = os.getenv("HOST", "0.0.0.0")
        
        print(f"🌐 Starting server on {host}:{port}")
        print(f"📊 Webhook endpoint: http://{host}:{port}/webhook")
        print("🔧 Press Ctrl+C to stop the server")
        print("-" * 50)
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except ImportError as e:
        print(f"❌ Error importing webhook_server: {e}")
        print("Make sure webhook_server.py exists and is properly configured.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()