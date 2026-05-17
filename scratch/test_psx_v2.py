import psxdata
from datetime import datetime, timedelta

try:
    # Get symbols
    # symbols = psxdata.get_symbols()
    # print("Symbols:", symbols[:10])
    
    # Get historical data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=60)
    
    # LUCK is Lucky Cement
    print(f"Fetching LUCK from {start_date} to {end_date}")
    df = psxdata.get_historical_data("LUCK", start_date, end_date)
    
    if df is not None:
        print("Columns:", df.columns.tolist())
        print("Head:")
        print(df.head())
    else:
        print("No data returned")
except Exception as e:
    print("Error:", e)
