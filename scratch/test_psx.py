from psx import stocks
from datetime import datetime, timedelta
import pandas as pd

try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    # LUCK is Lucky Cement
    df = stocks("LUCK", start=start_date, end=end_date)
    print("Columns:", df.columns.tolist())
    print("Head:")
    print(df.head())
except Exception as e:
    print("Error:", e)
