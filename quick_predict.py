"""
Quick Stock Scanner
===================
Instant predictions for multiple popular stocks.
"""

from stock_predictor import StockPredictor

STOCKS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'AMD', 'JPM', 'V', 'SPY', 'QQQ']

print("\n" + "="*60)
print("QUICK STOCK SCANNER")
print("="*60 + "\n")

results = []

for ticker in STOCKS:
    try:
        predictor = StockPredictor(ticker, lookback_days=365)
        predictor.train()
        result = predictor.predict_next()
        results.append(result)

        direction = "↑" if result['prediction'] == 'UP' else "↓"
        print(f"{ticker:6} ${result['current_price']:>8.2f}  {direction} {result['prediction']:3}  "
              f"Conf: {result['confidence']:5.1f}%")
    except Exception as e:
        print(f"{ticker:6} - Error: {str(e)[:30]}")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
up = [r for r in results if r['prediction'] == 'UP']
down = [r for r in results if r['prediction'] == 'DOWN']

print(f"BULLISH: {len(up)} stocks  |  BEARISH: {len(down)} stocks")

if up:
    print(f"UP: {', '.join(r['ticker'] for r in up)}")
if down:
    print(f"DOWN: {', '.join(r['ticker'] for r in down)}")

avg = sum(r['confidence'] for r in results) / len(results)
print(f"Avg Confidence: {avg:.1f}%")
print("="*60)