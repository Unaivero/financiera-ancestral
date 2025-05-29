#!/usr/bin/env python3
"""
Import SPY historical data from Stooq CSV into financiera_data.db, grouped by decade.
"""
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "financiera_data.db"
CSV_PATH = "spy_us_d.csv"
TICKER = "SPY"
MARKET = "SPDR S&P 500 ETF"

# Load CSV
df = pd.read_csv(CSV_PATH)

# Stooq CSV columns: Date,Open,High,Low,Close,Volume
# Convert Date to datetime
if 'Date' not in df.columns:
    raise ValueError("CSV must have a 'Date' column.")
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values('Date')
df['Year'] = df['Date'].dt.year
def get_decade(year):
    return f"{year//10*10}s"
df['Decade'] = df['Year'].apply(get_decade)

decades = df['Decade'].unique()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
rows_inserted = 0

for decade in decades:
    df_dec = df[df['Decade'] == decade]
    if df_dec.empty:
        continue
    start_row = df_dec.iloc[0]
    end_row = df_dec.iloc[-1]
    start_date = start_row['Date'].strftime('%Y-%m-%d')
    end_date = end_row['Date'].strftime('%Y-%m-%d')
    start_price = float(start_row['Open'])
    end_price = float(end_row['Close'])
    total_return = (end_price - start_price) / start_price * 100
    avg_volume = float(df_dec['Volume'].mean())
    volatility = float(df_dec['Close'].std())
    data_points = len(df_dec)
    cursor.execute('''
        INSERT OR IGNORE INTO stock_data (
            symbol, company_name, sector, market, decade, start_date, end_date,
            start_price, end_price, total_return, avg_volume, volatility, data_points
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        TICKER, 'SPDR S&P 500 ETF', 'ETF', MARKET, decade, start_date, end_date,
        start_price, end_price, total_return, avg_volume, volatility, data_points
    ))
    rows_inserted += 1

conn.commit()
conn.close()
print(f"✓ Imported SPY summary data for {rows_inserted} decades into {DB_PATH}")
