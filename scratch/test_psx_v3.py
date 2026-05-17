import psxdata
from datetime import datetime, timedelta

try:
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    
    print(f"Fetching LUCK from {start_date} to {end_date}")
    df = psxdata.stocks("LUCK", start=start_date, end=end_date)
    
    if df is not None:
        print("Columns:", df.columns.tolist())
        print("Head:")
        print(df.head())
    else:
        print("No data returned")
except Exception as e:
    print("Error:", e)
