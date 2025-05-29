#!/usr/bin/env python3
"""
Setup script for Financiera Ancestral
Handles installation, configuration, and initial setup
"""

import os
import sys
import sqlite3
import subprocess
from pathlib import Path

REQUIREMENTS_FILE = "requirements_v2.txt"
DB_PATH = "financiera_data.db"
CONFIG_FILE = "config.ini"

# 1. Check Python version
def check_python_version():
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version.split()[0]} detected")

# 2. Install dependencies
def install_dependencies():
    print("Installing dependencies from requirements_v2.txt ...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE
        ])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

# 3. Create necessary directories
def create_directories():
    directories = ['data', 'cache', 'logs', 'backups']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")

# 4. Create default config file
def create_config_file():
    config_content = f"""[API]
rate_limit_delay = 0.2
max_retries = 3
timeout = 30

[DATABASE]
path = {DB_PATH}
backup_enabled = true
backup_interval_hours = 24

[SECURITY]
secret_key = changeme

[LOGGING]
level = INFO
log_file = logs/app.log
"""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    with open(CONFIG_FILE, 'w') as f:
        f.write(config_content)
    print(f"✓ Created config file: {CONFIG_FILE}")

# 5. Initialize the SQLite database
def initialize_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                company_name TEXT,
                sector TEXT,
                market TEXT,
                decade TEXT,
                start_date TEXT,
                end_date TEXT,
                start_price REAL,
                end_price REAL,
                total_return REAL,
                avg_volume REAL,
                volatility REAL,
                data_points INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, decade, market)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decade TEXT NOT NULL,
                market TEXT NOT NULL,
                total_stocks INTEGER,
                avg_return REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(decade, market)
            )
        ''')
        # Create indexes
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_symbol_decade ON stock_data(symbol, decade)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_market_decade ON stock_data(market, decade)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_total_return ON stock_data(total_return DESC)''')
        conn.commit()
        conn.close()
        print(f"✓ Database initialized: {DB_PATH}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

# 6. Download sample S&P 500 data from Yahoo Finance (yahoosp500)
def create_sample_data():
    print("Fetching S&P 500 sample data from Yahoo Finance ...")
    try:
        import yfinance as yf
        sp500 = yf.Ticker("^GSPC")
        hist = sp500.history(period="10y")
        hist.to_csv("data/sample_sp500_10y.csv")
        print("✓ Sample S&P 500 data saved to data/sample_sp500_10y.csv")
    except Exception as e:
        print(f"Warning: Could not fetch sample data: {e}")

# 7. (Optional) Create systemd and Docker helpers
def create_systemd_service():
    service_file = "financiera_ancestral.service"
    service_content = f"""[Unit]
Description=Financiera Ancestral API Service
After=network.target

[Service]
Type=simple
WorkingDirectory={os.getcwd()}
ExecStart={sys.executable} {os.path.join(os.getcwd(), 'api_server.py')}
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
    with open(service_file, 'w') as f:
        f.write(service_content)
    print(f"✓ Created systemd service file: {service_file}")

def create_docker_files():
    dockerfile_content = f"""FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r {REQUIREMENTS_FILE}
EXPOSE 5000
CMD [\"python\", \"api_server.py\"]
"""
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile_content)
    print("✓ Created Dockerfile")
    docker_compose_content = """version: '3.8'
services:
  financiera:
    build: .
    ports:
      - '5000:5000'
    volumes:
      - .:/app
    restart: unless-stopped
"""
    with open('docker-compose.yml', 'w') as f:
        f.write(docker_compose_content)
    print("✓ Created docker-compose.yml")

def create_scripts():
    start_script = """#!/bin/bash\npython3 api_server.py\n"""
    backup_script = """#!/bin/bash\ntar -czvf backups/financiera_backup_$(date +%Y%m%d_%H%M%S).tar.gz financiera_data.db logs/\n"""
    with open('start.sh', 'w') as f:
        f.write(start_script)
    with open('backup.sh', 'w') as f:
        f.write(backup_script)
    os.chmod('start.sh', 0o755)
    os.chmod('backup.sh', 0o755)
    print("✓ Created start.sh and backup.sh")

# 8. Print next steps
def print_next_steps():
    print("\nSetup complete!\n")
    print("Next steps:")
    print("  - To start the API server: ./start.sh")
    print("  - To access the app: http://127.0.0.1:5000")
    print("  - To backup: ./backup.sh")
    print("  - To run with Docker: docker-compose up -d")
    print("  - To enable systemd: sudo cp financiera_ancestral.service /etc/systemd/system && sudo systemctl enable --now financiera_ancestral.service")
    print("\nFor help, see the README or ask your AI assistant!")

# Main orchestrator
def main():
    print("="*60)
    print("🏛️  FINANCIERA ANCESTRAL SETUP")
    print("="*60)
    check_python_version()
    install_dependencies()
    create_directories()
    create_config_file()
    initialize_database()
    create_sample_data()
    create_systemd_service()
    create_docker_files()
    create_scripts()
    print_next_steps()

if __name__ == '__main__':
    main()
