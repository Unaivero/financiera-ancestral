#!/usr/bin/env python3
"""
Financiera Ancestral API Server
Secure Flask API for serving financial data with rate limiting and caching
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Dict, Any, Optional

import sqlite3
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_minutes: int = 15):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests = {}
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if client is within rate limits"""
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - self.window_seconds
        self.requests = {
            ip: timestamps for ip, timestamps in self.requests.items()
            if any(ts > cutoff_time for ts in timestamps)
        }
        
        # Update client's request history
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove old timestamps for this client
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] 
            if ts > cutoff_time
        ]
        
        # Check if under limit
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[client_ip].append(current_time)
        return True

class SecurityHeaders:
    """Add security headers to responses"""
    
    @staticmethod
    def add_headers(response):
        """Add security headers to Flask response"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        return response

class DataCache:
    """Simple file-based cache for API responses"""
    
    def __init__(self, cache_dir: str = "cache", ttl_minutes: int = 60):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_minutes * 60
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached data if valid"""
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            # Check if cache is still valid
            if time.time() - cache_file.stat().st_mtime > self.ttl_seconds:
                cache_file.unlink()
                return None
            
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None
    
    def set(self, key: str, data: Dict):
        """Cache data"""
        cache_file = self.cache_dir / f"{key}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, default=str)
        except OSError as e:
            logger.warning(f"Cache write error for {key}: {e}")

def create_app(config: Dict[str, Any] = None) -> Flask:
    """Create and configure Flask application"""
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-key-change-in-production'),
        'DATABASE_PATH': os.environ.get('DATABASE_PATH', 'financiera_data.db'),
        'DATA_DIR': os.environ.get('DATA_DIR', 'data'),
        'RATE_LIMIT_REQUESTS': int(os.environ.get('RATE_LIMIT_REQUESTS', '100')),
        'RATE_LIMIT_WINDOW': int(os.environ.get('RATE_LIMIT_WINDOW', '15')),
        'CACHE_TTL': int(os.environ.get('CACHE_TTL', '60')),
        'DEBUG': os.environ.get('FLASK_ENV') == 'development'
    })
    
    if config:
        app.config.update(config)
    
    # Initialize components
    rate_limiter = RateLimiter(
        max_requests=app.config['RATE_LIMIT_REQUESTS'],
        window_minutes=app.config['RATE_LIMIT_WINDOW']
    )
    
    cache = DataCache(ttl_minutes=app.config['CACHE_TTL'])
    
    # Enable CORS with security settings
    CORS(app, 
         origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
         supports_credentials=False,
         max_age=3600)
    
    def require_rate_limit(f):
        """Decorator to enforce rate limiting"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            if not rate_limiter.is_allowed(client_ip):
                logger.warning(f"Rate limit exceeded for {client_ip}")
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {app.config["RATE_LIMIT_REQUESTS"]} requests per {app.config["RATE_LIMIT_WINDOW"]} minutes'
                })
                response.status_code = 429
                return SecurityHeaders.add_headers(response)
            
            return f(*args, **kwargs)
        return decorated_function
    
    def validate_decade(decade: str) -> bool:
        """Validate decade parameter"""
        valid_decades = ['1920s', '1930s', '1940s', '1950s', '1960s', '1970s', 
                        '1980s', '1990s', '2000s', '2010s', '2020s']
        return decade in valid_decades
    
    def validate_market(market: str) -> bool:
        """Validate market parameter"""
        valid_markets = ['NYSE', 'Frankfurt', 'Tokyo', 'Hong Kong']
        return market in valid_markets
    
    def get_db_connection():
        """Get database connection"""
        try:
            conn = sqlite3.connect(app.config['DATABASE_PATH'])
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    @app.after_request
    def after_request(response):
        """Add security headers to all responses"""
        return SecurityHeaders.add_headers(response)
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        response = jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found'
        })
        response.status_code = 404
        return response
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        response = jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        })
        response.status_code = 500
        return response
    
    @app.route('/')
    def index():
        """Serve main application"""
        return send_from_directory('.', 'financiera_frontend_v2.html')
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Check database connection
            with get_db_connection() as conn:
                conn.execute('SELECT 1').fetchone()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '2.0'
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            response = jsonify({
                'status': 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            })
            response.status_code = 503
            return response
    
    @app.route('/api/data/decades')
    @require_rate_limit
    def get_decades():
        """Get list of available decades"""
        cache_key = "decades_list"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    'SELECT DISTINCT decade FROM stock_data ORDER BY decade'
                )
                decades = [row['decade'] for row in cursor.fetchall()]
            
            data = {
                'decades': decades,
                'count': len(decades),
                'timestamp': datetime.now().isoformat()
            }
            
            cache.set(cache_key, data)
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"Error fetching decades: {e}")
            return jsonify({'error': 'Failed to fetch decades'}), 500
    
    @app.route('/api/data/markets')
    @require_rate_limit
    def get_markets():
        """Get list of available markets"""
        cache_key = "markets_list"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    'SELECT DISTINCT market FROM stock_data ORDER BY market'
                )
                markets = [row['market'] for row in cursor.fetchall()]
            
            data = {
                'markets': markets,
                'count': len(markets),
                'timestamp': datetime.now().isoformat()
            }
            
            cache.set(cache_key, data)
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return jsonify({'error': 'Failed to fetch markets'}), 500
    
    @app.route('/api/data/decade/<decade>')
    @require_rate_limit
    def get_decade_data(decade):
        """Get all data for a specific decade"""
        if not validate_decade(decade):
            return jsonify({'error': 'Invalid decade parameter'}), 400
        
        cache_key = f"decade_{decade}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM stock_data 
                    WHERE decade = ? 
                    ORDER BY market, symbol
                ''', (decade,))
                
                stocks = []
                for row in cursor.fetchall():
                    stocks.append(dict(row))
            
            if not stocks:
                return jsonify({'error': 'No data found for this decade'}), 404
            
            # Group by market
            markets = {}
            for stock in stocks:
                market = stock['market']
                if market not in markets:
                    markets[market] = {
                        'name': market,
                        'stocks': [],
                        'total_stocks': 0
                    }
                markets[market]['stocks'].append(stock)
                markets[market]['total_stocks'] += 1
            
            data = {
                'decade': decade,
                'markets': markets,
                'total_stocks': len(stocks),
                'timestamp': datetime.now().isoformat()
            }
            
            cache.set(cache_key, data)
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"Error fetching decade data: {e}")
            return jsonify({'error': 'Failed to fetch decade data'}), 500
    
    @app.route('/api/data/market/<market>')
    @require_rate_limit
    def get_market_data(market):
        """Get all data for a specific market"""
        if not validate_market(market):
            return jsonify({'error': 'Invalid market parameter'}), 400
        
        decade = request.args.get('decade')
        if decade and not validate_decade(decade):
            return jsonify({'error': 'Invalid decade parameter'}), 400
        
        cache_key = f"market_{market}_{decade or 'all'}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        try:
            query = 'SELECT * FROM stock_data WHERE market = ?'
            params = [market]
            
            if decade:
                query += ' AND decade = ?'
                params.append(decade)
            
            query += ' ORDER BY decade, symbol'
            
            with get_db_connection() as conn:
                cursor = conn.execute(query, params)
                stocks = [dict(row) for row in cursor.fetchall()]
            
            if not stocks:
                return jsonify({'error': 'No data found for this market'}), 404
            
            data = {
                'market': market,
                'decade': decade,
                'stocks': stocks,
                'total_stocks': len(stocks),
                'timestamp': datetime.now().isoformat()
            }
            
            cache.set(cache_key, data)
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return jsonify({'error': 'Failed to fetch market data'}), 500
    
    @app.route('/api/data/stock/<symbol>')
    @require_rate_limit
    def get_stock_data(symbol):
        """Get historical data for a specific stock"""
        if not symbol or len(symbol) > 10:
            return jsonify({'error': 'Invalid symbol parameter'}), 400
        
        cache_key = f"stock_{symbol.upper()}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM stock_data 
                    WHERE UPPER(symbol) = UPPER(?) 
                    ORDER BY decade
                ''', (symbol,))
                
                stocks = [dict(row) for row in cursor.fetchall()]
            
            if not stocks:
                return jsonify({'error': 'No data found for this stock'}), 404
            
            data = {
                'symbol': symbol.upper(),
                'company_name': stocks[0].get('company_name', ''),
                'historical_data': stocks,
                'decades_count': len(stocks),
                'timestamp': datetime.now().isoformat()
            }
            
            cache.set(cache_key, data)
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"Error fetching stock data: {e}")
            return jsonify({'error': 'Failed to fetch stock data'}), 500
    
    @app.route('/api/data/top-performers')
    @require_rate_limit
    def get_top_performers():
        """Get top performing stocks"""
        decade = request.args.get('decade')
        market = request.args.get('market')
        limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 results
        
        if decade and not validate_decade(decade):
            return jsonify({'error': 'Invalid decade parameter'}), 400
        
        if market and not validate_market(market):
            return jsonify({'error': 'Invalid market parameter'}), 400
        
        cache_key = f"top_performers_{decade or 'all'}_{market or 'all'}_{limit}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        try:
            query = 'SELECT * FROM stock_data WHERE 1=1'
            params = []
            
            if decade:
                query += ' AND decade = ?'
                params.append(decade)
            
            if market:
                query += ' AND market = ?'
                params.append(market)
            
            query += ' ORDER BY total_return DESC LIMIT ?'
            params.append(limit)
            
            with get_db_connection() as conn:
                cursor = conn.execute(query, params)
                stocks = [dict(row) for row in cursor.fetchall()]
            
            data = {
                'top_performers': stocks,
                'filters': {
                    'decade': decade,
                    'market': market,
                    'limit': limit
                },
                'count': len(stocks),
                'timestamp': datetime.now().isoformat()
            }
            
            cache.set(cache_key, data)
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"Error fetching top performers: {e}")
            return jsonify({'error': 'Failed to fetch top performers'}), 500
    
    @app.route('/api/data/statistics')
    @require_rate_limit
    def get_statistics():
        """Get overall statistics"""
        decade = request.args.get('decade')
        market = request.args.get('market')
        
        if decade and not validate_decade(decade):
            return jsonify({'error': 'Invalid decade parameter'}), 400
        
        if market and not validate_market(market):
            return jsonify({'error': 'Invalid market parameter'}), 400
        
        cache_key = f"statistics_{decade or 'all'}_{market or 'all'}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        try:
            query = '''
                SELECT 
                    COUNT(*) as total_stocks,
                    AVG(total_return) as avg_return,
                    MAX(total_return) as max_return,
                    MIN(total_return) as min_return,
                    AVG(volatility) as avg_volatility,
                    COUNT(DISTINCT market) as markets_count,
                    COUNT(DISTINCT decade) as decades_count
                FROM stock_data WHERE 1=1
            '''
            params = []
            
            if decade:
                query += ' AND decade = ?'
                params.append(decade)
            
            if market:
                query += ' AND market = ?'
                params.append(market)
            
            with get_db_connection() as conn:
                cursor = conn.execute(query, params)
                stats = dict(cursor.fetchone())
            
            # Round numeric values
            for key in ['avg_return', 'max_return', 'min_return', 'avg_volatility']:
                if stats[key] is not None:
                    stats[key] = round(stats[key], 2)
            
            data = {
                'statistics': stats,
                'filters': {
                    'decade': decade,
                    'market': market
                },
                'timestamp': datetime.now().isoformat()
            }
            
            cache.set(cache_key, data)
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"Error fetching statistics: {e}")
            return jsonify({'error': 'Failed to fetch statistics'}), 500
    
    @app.route('/api/data/export')
    @require_rate_limit
    def export_data():
        """Export data as CSV"""
        decade = request.args.get('decade')
        market = request.args.get('market')
        format_type = request.args.get('format', 'csv').lower()
        
        if format_type not in ['csv', 'json']:
            return jsonify({'error': 'Invalid format. Use csv or json'}), 400
        
        if decade and not validate_decade(decade):
            return jsonify({'error': 'Invalid decade parameter'}), 400
        
        if market and not validate_market(market):
            return jsonify({'error': 'Invalid market parameter'}), 400
        
        try:
            query = 'SELECT * FROM stock_data WHERE 1=1'
            params = []
            
            if decade:
                query += ' AND decade = ?'
                params.append(decade)
            
            if market:
                query += ' AND market = ?'
                params.append(market)
            
            query += ' ORDER BY decade, market, symbol'
            
            with get_db_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                return jsonify({'error': 'No data found for export'}), 404
            
            if format_type == 'csv':
                csv_data = df.to_csv(index=False)
                response = app.response_class(
                    csv_data,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename=financiera_data_{decade or "all"}_{market or "all"}.csv'
                    }
                )
                return response
            else:  # json
                json_data = df.to_json(orient='records', indent=2)
                response = app.response_class(
                    json_data,
                    mimetype='application/json',
                    headers={
                        'Content-Disposition': f'attachment; filename=financiera_data_{decade or "all"}_{market or "all"}.json'
                    }
                )
                return response
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return jsonify({'error': 'Failed to export data'}), 500
    
    return app

def main():
    """Main function to run the server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Financiera Ancestral API Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Load configuration if provided
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Create and run app
    app = create_app(config)
    
    logger.info(f"Starting Financiera Ancestral API Server on {args.host}:{args.port}")
    logger.info(f"Debug mode: {args.debug}")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=args.debug
    )

if __name__ == '__main__':
    main()