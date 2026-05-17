import sqlite3
import pandas as pd
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'market_data.db')

class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('CREATE TABLE IF NOT EXISTS cache_metadata (ticker TEXT PRIMARY KEY, last_updated TEXT)')
        conn.commit()
        conn.close()

    def get_data(self, ticker: str) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT last_updated FROM cache_metadata WHERE ticker=?", (ticker,))
            row = cursor.fetchone()
            if row:
                last_updated = datetime.fromisoformat(row[0])
                if last_updated.date() == datetime.now().date():
                    df = pd.read_sql(f'SELECT * FROM "{ticker}"', conn, index_col='Date', parse_dates=['Date'])
                    print(f"[DB Cache] Loaded {len(df)} rows for {ticker}")
                    return df
            return None
        except Exception as e:
            print(f"[DB Cache] Error: {e}")
            return None
        finally:
            conn.close()

    def save_data(self, ticker: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        conn = sqlite3.connect(self.db_path)
        try:
            df_to_save = df.copy()
            df_to_save.to_sql(ticker, conn, if_exists='replace', index=True)
            conn.execute('INSERT OR REPLACE INTO cache_metadata (ticker, last_updated) VALUES (?, ?)',
                         (ticker, datetime.now().isoformat()))
            conn.commit()
            print(f"[DB Cache] Saved {len(df)} rows for {ticker}")
        except Exception as e:
            print(f"[DB Cache] Save error: {e}")
        finally:
            conn.close()

db_manager = DatabaseManager()
