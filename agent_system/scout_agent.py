import os
import json
import logging
import time
from datetime import datetime
from duckduckgo_search import DDGS
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TheScout")

class ScoutAgent:
    def __init__(self):
        self.name = "The Scout"
        logger.info("Initializing FinBERT microscopic sentiment brain...")
        try:
            self.sentiment_pipe = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        except Exception as e:
            logger.warning(f"FinBERT initialization failed: {e}. Falling back to basic mode.")
            self.sentiment_pipe = None
        
    def execute(self, ticker: str) -> dict:
        logger.info(f"Scouting live data for {ticker}...")
        queries = [
            f"{ticker} stock live price news catalysts",
            f"{ticker} earnings call transcript news",
            f"{ticker} microscopic market sentiment"
        ]
        
        articles = []
        with DDGS() as ddgs:
            for query in queries:
                try:
                    results = list(ddgs.text(query, max_results=3))
                    articles.extend(results)
                except:
                    pass
        
        # Microscopic Sentiment Analysis via FinBERT
        finbert_scores = []
        if self.sentiment_pipe:
            for art in articles:
                text = f"{art['title']} {art['body']}"[:512] # FinBERT limit
                try:
                    result = self.sentiment_pipe(text)[0]
                    # Convert label to score: positive=1, negative=-1, neutral=0
                    label = result['label']
                    score = result['score']
                    if label == 'positive':
                        finbert_scores.append(score)
                    elif label == 'negative':
                        finbert_scores.append(-score)
                    else:
                        finbert_scores.append(0.0)
                except:
                    pass
        
        avg_sentiment = sum(finbert_scores) / len(finbert_scores) if finbert_scores else 0.0
        logger.info(f"Microscopic FinBERT Sentiment Score: {avg_sentiment:.2f}")
                    
        return {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "news_payload": articles,
            "finbert_sentiment": avg_sentiment
        }

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    scout = ScoutAgent()
    print(json.dumps(scout.execute(ticker), indent=2))
