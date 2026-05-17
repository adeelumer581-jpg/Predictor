import time
import warnings
from duckduckgo_search import DDGS
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime

warnings.filterwarnings('ignore', module='duckduckgo_search')


class BossAgent:
    def __init__(self):
        # Master list of diverse assets (Tech, Finance, Commodities, Indices)
        self.master_list = {
            'AAPL': 'Apple',
            'MSFT': 'Microsoft',
            'NVDA': 'Nvidia',
            'TSLA': 'Tesla',
            'AMZN': 'Amazon',
            'JPM': 'JPMorgan',
            'XOM': 'ExxonMobil',
            'GC=F': 'Gold',
            'CL=F': 'Crude Oil',
            'SI=F': 'Silver',
            'HG=F': 'Copper',
            'ZC=F': 'Corn',
            'SPY': 'S&P 500 ETF',
            'QQQ': 'Nasdaq ETF'
        }
        self.analyzer = SentimentIntensityAnalyzer()
        
    def gather_market_intelligence(self, ticker, company_name):
        """Fetches recent news for a ticker and calculates sentiment."""
        query = f"{company_name} stock OR market news"
        if "=" in ticker: # Handle commodity tickers
            query = f"{company_name} commodity price news"
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Boss is researching {company_name} ({ticker})...")
        
        try:
            with DDGS() as ddgs:
                # Get top 5 recent news articles
                results = list(ddgs.text(query, timelimit='d', max_results=5))
                
            if not results:
                return 0.0
                
            total_sentiment = 0.0
            for r in results:
                text = r.get('title', '') + " " + r.get('body', '')
                score = self.analyzer.polarity_scores(text)
                total_sentiment += score['compound']
                
            return total_sentiment / len(results)
            
        except Exception as e:
            print(f"Error researching {ticker}: {e}")
            return 0.0

    def issue_daily_orders(self, num_assets=5):
        """Analyzes all assets and picks the top N most interesting ones (high absolute sentiment)."""
        print("\n" + "="*60)
        print(f"BOSS AGENT: Waking up at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("BOSS AGENT: Scanning global markets and reading news...")
        print("="*60)
        
        sentiment_scores = {}
        
        for ticker, name in self.master_list.items():
            score = self.gather_market_intelligence(ticker, name)
            sentiment_scores[ticker] = score
            time.sleep(1) # Polite delay for search engine
            
        # Sort by absolute sentiment (we want strong trends, either bullish or bearish)
        sorted_assets = sorted(sentiment_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        top_assets = sorted_assets[:num_assets]
        
        print("\n" + "="*60)
        print("BOSS AGENT: Daily Analysis Complete.")
        print("BOSS AGENT: Selected the following highly volatile/trending assets:")
        
        orders = []
        for ticker, score in top_assets:
            sentiment_label = "BULLISH" if score > 0 else "BEARISH"
            print(f" -> {ticker:5} | {self.master_list[ticker]:15} | Sentiment: {sentiment_label} ({score:+.2f})")
            orders.append(ticker)
            
        print("="*60 + "\n")
        
        return orders

if __name__ == "__main__":
    boss = BossAgent()
    boss.issue_daily_orders()
