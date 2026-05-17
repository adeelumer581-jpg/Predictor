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
        """Initializes the database and metadata table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_metadata (
                ticker TEXT PRIMARY KEY,
                last_updated TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def get_data(self, ticker: str) -> pd.DataFrame:
        """Retrieves data from the cache if available and up-to-date."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Check when it was last updated
            cursor = conn.cursor()
            cursor.execute("SELECT last_updated FROM cache_metadata WHERE ticker=?", (ticker,))
            row = cursor.fetchone()
            
            if row:
                last_updated = datetime.fromisoformat(row[0])
                # If updated today, use cache
                if last_updated.date() == datetime.now().date():
                    df = pd.read_sql(f'SELECT * FROM "{ticker}"', conn, index_col='Date', parse_dates=['Date'])
                    print(f"[DB Cache] Loaded {len(df)} rows for {ticker} from local database.")
                    return df
            return None
        except Exception as e:
            print(f"[DB Cache] Error retrieving {ticker}: {e}")
            return None
        finally:
            conn.close()

    def save_data(self, ticker: str, df: pd.DataFrame):
        """Saves or updates data in the cache."""
        if df is None or df.empty:
            return
            
        conn = sqlite3.connect(self.db_path)
        try:
            # Save the dataframe
            # Reset index to make 'Date' a column if it is the index
            if df.index.name == 'Date' or 'Date' in df.index.names:
                df_to_save = df.copy()
            else:
                df_to_save = df.copy()
                df_to_save.index.name = 'Date'
                
            df_to_save.to_sql(ticker, conn, if_exists='replace', index=True)
            
            # Update metadata
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO cache_metadata (ticker, last_updated)
                VALUES (?, ?)
            ''', (ticker, datetime.now().isoformat()))
            
            conn.commit()
            print(f"[DB Cache] Saved {len(df)} rows for {ticker} to local database.")
        except Exception as e:
            print(f"[DB Cache] Error saving {ticker}: {e}")
        finally:
            conn.close()

# Singleton instance
db_manager = DatabaseManager()
