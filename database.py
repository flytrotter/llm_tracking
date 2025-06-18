import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class SpendingDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv('DATABASE_PATH', 'spending_monitor.db')
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table to store individual API requests and their costs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                timestamp DATETIME NOT NULL,
                cost_usd REAL NOT NULL,
                model TEXT,
                provider TEXT,
                user_id TEXT,
                tokens_total INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table to store hourly spending aggregates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hourly_spending (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour_start DATETIME NOT NULL,
                total_cost_usd REAL NOT NULL,
                request_count INTEGER NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(hour_start)
            )
        ''')
        
        # Table to track alerts sent
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour_start DATETIME NOT NULL,
                alert_type TEXT NOT NULL,
                total_spend REAL NOT NULL,
                limit_exceeded REAL NOT NULL,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_request(self, request_data: Dict) -> bool:
        """Add a new API request to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO api_requests 
                (request_id, timestamp, cost_usd, model, provider, user_id, tokens_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                request_data['request_id'],
                request_data['timestamp'],
                request_data['cost_usd'],
                request_data.get('model'),
                request_data.get('provider'),
                request_data.get('user_id'),
                request_data.get('tokens_total')
            ))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error adding request: {e}")
            return False
        finally:
            conn.close()
    
    def get_hourly_spending(self, hour_start: datetime) -> float:
        """Get total spending for a specific hour"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        hour_end = hour_start + timedelta(hours=1)
        
        cursor.execute('''
            SELECT COALESCE(SUM(cost_usd), 0) as total_cost
            FROM api_requests 
            WHERE timestamp >= ? AND timestamp < ?
        ''', (hour_start, hour_end))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0.0
    
    def update_hourly_aggregate(self, hour_start: datetime):
        """Update the hourly spending aggregate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        hour_end = hour_start + timedelta(hours=1)
        
        # Get aggregated data for the hour
        cursor.execute('''
            SELECT 
                COALESCE(SUM(cost_usd), 0) as total_cost,
                COUNT(*) as request_count
            FROM api_requests 
            WHERE timestamp >= ? AND timestamp < ?
        ''', (hour_start, hour_end))
        
        result = cursor.fetchone()
        total_cost, request_count = result if result else (0.0, 0)
        
        # Insert or update the hourly aggregate
        cursor.execute('''
            INSERT OR REPLACE INTO hourly_spending 
            (hour_start, total_cost_usd, request_count, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (hour_start, total_cost, request_count))
        
        conn.commit()
        conn.close()
        
        return total_cost
    
    def was_alert_sent(self, hour_start: datetime, alert_type: str) -> bool:
        """Check if an alert was already sent for this hour"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM alerts_sent 
            WHERE hour_start = ? AND alert_type = ?
        ''', (hour_start, alert_type))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] > 0 if result else False
    
    def record_alert_sent(self, hour_start: datetime, alert_type: str, 
                         total_spend: float, limit_exceeded: float):
        """Record that an alert was sent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts_sent 
            (hour_start, alert_type, total_spend, limit_exceeded)
            VALUES (?, ?, ?, ?)
        ''', (hour_start, alert_type, total_spend, limit_exceeded))
        
        conn.commit()
        conn.close()