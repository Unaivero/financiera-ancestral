# 🏛️ Financiera Ancestral

A comprehensive financial data analysis platform that provides secure API access to historical stock market data across different decades and markets. Features real-time data visualization, performance analytics, and export capabilities.

## 🚀 Features

- **Multi-Market Analysis**: Support for NYSE, Frankfurt, Tokyo, and Hong Kong markets
- **Historical Data**: Decade-by-decade analysis from 1920s to 2020s
- **Performance Metrics**: Total returns, volatility analysis, and top performers
- **Secure API**: Rate limiting, caching, and comprehensive security headers
- **Data Export**: CSV and JSON export capabilities
- **Real-time Visualization**: Interactive charts and statistical dashboards
- **Docker Support**: Containerized deployment with Docker Compose
- **System Integration**: Systemd service files for production deployment

## 📋 Prerequisites

- **Python 3.8+** (required)
- **pip** (Python package manager)
- **Git** (for cloning the repository)
- **Docker** (optional, for containerized deployment)

## 🛠️ Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Unaivero/financiera-ancestral.git
cd financiera-ancestral
```

### 2. Automated Setup
Run the setup script to automatically configure everything:
```bash
python3 setup_script.py
```

This will:
- ✅ Check Python version compatibility
- ✅ Install all required dependencies
- ✅ Create necessary directories (data, cache, logs, backups)
- ✅ Initialize SQLite database with proper schema
- ✅ Generate configuration files
- ✅ Download sample S&P 500 data
- ✅ Create Docker and systemd service files

### 3. Start the Application
```bash
# Using the generated script
./start.sh

# Or directly with Python
python3 api_server.py

# Or with custom parameters
python3 api_server.py --host 0.0.0.0 --port 8000 --debug
```

### 4. Access the Application
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Manual Docker Build
```bash
# Build the image
docker build -t financiera-ancestral .

# Run the container
docker run -d -p 5000:5000 --name financiera financiera-ancestral
```

## 📊 API Endpoints

### Health & Status
- `GET /api/health` - Health check endpoint
- `GET /` - Main application frontend

### Data Retrieval
- `GET /api/data/decades` - List all available decades
- `GET /api/data/markets` - List all available markets
- `GET /api/data/decade/<decade>` - Get all data for a specific decade
- `GET /api/data/market/<market>` - Get all data for a specific market
- `GET /api/data/stock/<symbol>` - Get historical data for a stock symbol

### Analytics
- `GET /api/data/top-performers` - Get top performing stocks
- `GET /api/data/statistics` - Get overall market statistics
- `GET /api/data/export` - Export data in CSV or JSON format

### Query Parameters
- `decade`: Filter by decade (1920s, 1930s, ..., 2020s)
- `market`: Filter by market (NYSE, Frankfurt, Tokyo, Hong Kong)
- `limit`: Limit number of results (max 50)
- `format`: Export format (csv, json)

### Example API Calls
```bash
# Get top 10 performers from the 2010s
curl "http://localhost:5000/api/data/top-performers?decade=2010s&limit=10"

# Get NYSE market statistics
curl "http://localhost:5000/api/data/statistics?market=NYSE"

# Export 1990s data as CSV
curl "http://localhost:5000/api/data/export?decade=1990s&format=csv"
```

## 🗂️ Project Structure

```
financiera-ancestral/
├── api_server.py              # Main Flask API server
├── financiera_frontend_v2.html # Frontend interface
├── setup_script.py            # Automated setup script
├── requirements_v2.txt        # Python dependencies
├── config.ini                 # Configuration file
├── financiera_data.db         # SQLite database
├── spy_us_d.csv              # Sample S&P 500 data
├── import_spy_stooq_csv.py   # Data import utility
├── docker-compose.yml         # Docker Compose configuration
├── Dockerfile                 # Docker container definition
├── financiera_ancestral.service # Systemd service file
├── start.sh                   # Application startup script
├── backup.sh                  # Database backup script
├── data/                      # Data storage directory
├── cache/                     # API response cache
├── logs/                      # Application logs
└── backups/                   # Database backups
```

## ⚙️ Configuration

### Environment Variables
```bash
export SECRET_KEY="your-secret-key-here"
export DATABASE_PATH="financiera_data.db"
export RATE_LIMIT_REQUESTS=100
export RATE_LIMIT_WINDOW=15
export CACHE_TTL=60
export FLASK_ENV=development  # or production
```

### Configuration File (config.ini)
```ini
[API]
rate_limit_delay = 0.2
max_retries = 3
timeout = 30

[DATABASE]
path = financiera_data.db
backup_enabled = true
backup_interval_hours = 24

[SECURITY]
secret_key = changeme

[LOGGING]
level = INFO
log_file = logs/app.log
```

## 🔧 Production Deployment

### Using Systemd (Linux)
```bash
# Copy service file
sudo cp financiera_ancestral.service /etc/systemd/system/

# Enable and start the service
sudo systemctl enable --now financiera_ancestral.service

# Check status
sudo systemctl status financiera_ancestral.service
```

### Using Gunicorn (Recommended for Production)
```bash
# Install Gunicorn (included in requirements)
pip install gunicorn

# Start with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
```

## 🔒 Security Features

- **Rate Limiting**: 100 requests per 15 minutes per IP
- **Security Headers**: CSP, HSTS, XSS protection
- **Input Validation**: Comprehensive parameter validation
- **CORS Protection**: Restricted origins
- **SQL Injection Prevention**: Parameterized queries
- **Error Handling**: Secure error responses

## 📈 Data Import

### Manual Data Import
```python
# Import S&P 500 data from CSV
python3 import_spy_stooq_csv.py

# Import from Yahoo Finance (requires implementation)
python3 import_sp500_yahoo.py
```

### Database Schema
```sql
CREATE TABLE stock_data (
    id INTEGER PRIMARY KEY,
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Maintenance

### Backup Database
```bash
# Manual backup
./backup.sh

# Automated backup (via cron)
0 2 * * * /path/to/project/backup.sh
```

### View Logs
```bash
# Application logs
tail -f logs/app.log

# API server logs
tail -f api_server.log

# Docker logs
docker-compose logs -f
```

### Clear Cache
```bash
# Remove cache files
rm -rf cache/*

# Restart application to clear memory cache
sudo systemctl restart financiera_ancestral.service
```

## 🧪 Development

### Running in Debug Mode
```bash
python3 api_server.py --debug
```

### Running Tests
```bash
# Install test dependencies (included in requirements)
pip install pytest pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=api_server
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues, questions, or contributions:

1. **Check the logs**: `tail -f logs/app.log`
2. **Verify configuration**: Ensure `config.ini` is properly set
3. **Test API endpoints**: Use the health check endpoint
4. **Check Docker status**: `docker-compose ps`
5. **Open an issue**: Create a GitHub issue with details

## 🎯 Roadmap

- [ ] Real-time data streaming
- [ ] Advanced analytics and ML predictions
- [ ] Multi-user authentication
- [ ] Portfolio management features
- [ ] Mobile app development
- [ ] Additional market support

---

**Built with ❤️ for financial data analysis**
