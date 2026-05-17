"""
Mass Trainer - S&P 500 Iteration System
=========================================
Trains models for S&P 500 stocks without crashing.
Features:
- Batch processing with memory management
- Error handling and recovery
- Progress tracking and checkpointing
- Rate limiting to avoid API blocks
"""
import os
import sys
import time
import json
import gc
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MassTrainer")

# S&P 500 tickers (abbreviated list - can be expanded)
S_P_500_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "UNH",
    "JNJ", "V", "XOM", "JPM", "LLY", "PG", "MA", "HD", "CVX", "MRK",
    "ABBV", "PEP", "KO", "COST", "BAC", "AVGO", "TMO", "WMT", "MCD", "CSCO",
    "ACN", "ABT", "DHR", "LIN", "ADBE", "CRM", "AMD", "NFLX", "DIS", "CMCSA",
    "VZ", "INTC", "NKE", "TXN", "PM", "NEE", "RTX", "UNP", "BMY", "HON",
    "ORCL", "QCOM", "IBM", "AMAT", "T", "BA", "CAT", "GE", "SBUX", "AMD",
    "AMGN", "ISRG", "TGT", "LOW", "SPGI", "MDT", "UPS", "GILD", "LMT", "BLK",
    "AXP", "CI", "MMM", "INTU", "SYK", "BAX", "TJX", "CVS", "ADP", "GS",
    "AMAT", "BKNG", "MO", "MDLZ", "CB", "PLD", "REGN", "BDX", "ZTS", "VRTX",
    "MMC", "TMUS", "SCHW", "CNC", "BSX", "EOG", "PNC", "CME", "KLAC", "SO",
    "ITW", "APD", "NSC", "WM", "ICE", "MCO", "MAR", "FI", "CDNS", "SHW",
    "EL", "EW", "ORLY", "PSX", "HCA", "GD", "AJG", "MCHP", "APH", "CTAS",
    "MSI", "EMR", "PCAR", "PAYX", "PRU", "AON", "FCX", "SLB", "MET", "AFL",
    "O", "TFC", "NOC", "CARR", "PH", "CMI", "AMT", "KMB", "WM", "SRE",
    "EQIX", "CMG", "FCX", "ROK", "WM", "TGT", "WM", "SHW", "MCO", "PSA",
    "DG", "APD", "PHM", "TT", "CMI", "ROK", "AMP", "TEL", "BKR", "PCAR",
    "GM", "F", "T", "VIV", "HPQ", "KEYS", "FTNT", "CFL", "ANSS", "SWKS",
    "KEYS", "TER", "CDW", "EXC", "EXC", "XEL", "DTE", "AEP", "SRE", "PEG",
    "ED", "WEC", "CE", "DUK", "LRCX", "KLA", "MRVL", "SNPS", "CDNS", "KEYS",
    "NOW", "WDAY", "SPLK", "ZM", "ZOOM", "DDOG", "SNOW", "CRWD", "NET", "DBX",
    "OKTA", "PANW", "FTNT", "NET", "CRWD", "SPLK", "WDAY", "NOW", "TEAM", "ADSK"
]

# Expanded S&P 500 list
FULL_S_P_500 = [
    "A", "AA", "AAL", "AAP", "AAPL", "ABBV", "ABC", "ABT", "ACN", "ADBE",
    "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIV",
    "AIZ", "AJG", "AKAM", "ALB", "ALGN", "ALK", "ALL", "ALLE", "AMAT", "AMCR",
    "AMD", "AME", "AMG", "AMGN", "AMP", "AMT", "AMZN", "ANET", "ANSS", "ANTM",
    "AON", "AOS", "APA", "APD", "APH", "APTV", "ARE", "ATO", "AVB", "AVGO",
    "AVY", "AWK", "AXP", "AZO", "BA", "BAC", "BALL", "BBY", "BDX", "BEN",
    "BF.B", "BIIB", "BKR", "BLK", "BMY", "BRK.B", "BSX", "BTI", "BWA", "BXP",
    "C", "CAG", "CAH", "CAT", "CB", "CBOE", "CBRE", "CCI", "CDNS", "CE",
    "CF", "CHRW", "CHTR", "CI", "CINF", "CL", "CLX", "CME", "CMG", "CMS",
    "CNC", "CNP", "COF", "COG", "COO", "COP", "COST", "CPRT", "CRL", "CRM",
    "CSCO", "CSX", "CTAS", "CTVA", "CVS", "CVX", "CY", "D", "DAL", "DD",
    "DE", "DFS", "DG", "DHI", "DHR", "DIS", "DISH", "DLR", "DLTR", "DOV",
    "DRI", "DTE", "DUK", "DVA", "DVN", "DXC", "EA", "EBAY", "ECL", "ED",
    "EL", "ELV", "EMN", "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "ES",
    "ETN", "ETR", "EVRG", "EW", "EXC", "EXPE", "EXR", "F", "FANG", "FAST",
    "FCX", "FDS", "FI", "FICO", "FIS", "FISV", "FITB", "FLT", "FMC", "FOX",
    "FOXA", "FRC", "FRT", "FSLR", "FTNT", "FTV", "GD", "GE", "GILD", "GIS",
    "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS",
    "HAL", "HAS", "HBAN", "HCA", "HCP", "HD", "HES", "HIG", "HII", "HLT",
    "HOLX", "HON", "HP", "HPQ", "HRL", "HSIC", "HST", "HWM", "IBM", "ICE",
    "IDXX", "IEX", "IFF", "INCY", "INFO", "INTC", "INTU", "IP", "IPG", "IQV",
    "IR", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT", "JCI", "JKHY", "JNJ",
    "JPM", "K", "KDP", "KEY", "KEYS", "KHC", "KIM", "KLAC", "KMB", "KMI",
    "KMX", "KO", "KR", "L", "LDOS", "LEN", "LH", "LHX", "LIN", "LKQ",
    "LLY", "LMT", "LNC", "LNT", "LOW", "LRCX", "LULU", "LUV", "M", "MA",
    "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "META",
    "MET", "MGM", "MHK", "MIDD", "MKC", "MMC", "MMM", "MO", "MOH", "MOS",
    "MRK", "MRNA", "MS", "MSCI", "MSFT", "MTB", "MU", "NCLH", "NDAQ", "NDSN",
    "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NSC", "NTAP", "NTRS", "NUE",
    "NVDA", "NVR", "NWS", "NWSA", "O", "ODFL", "OHSU", "O", "OKE", "OMV",
    "ORCL", "ORLY", "OXY", "PANW", "PAYX", "PCAR", "PCG", "PEAK", "PEG", "PFE",
    "PGR", "PG", "PH", "PHM", "PKI", "PLD", "PM", "PNC", "PNR", "PNW",
    "POOL", "PPG", "PPL", "PRU", "PSX", "PTC", "PVH", "PWR", "PXD", "PYPL",
    "QCOM", "R", "REG", "REGN", "RF", "RHI", "RJF", "RL", "RMD", "ROK",
    "ROL", "ROP", "ROST", "RSG", "RTX", "RVTY", "SBAC", "SBUX", "SCHW", "SHE",
    "SHW", "SIRI", "SITE", "SIVB", "SJM", "SLB", "SLG", "SNA", "SNPS", "SO",
    "SPG", "SPGI", "SRE", "STE", "STT", "STZ", "SWK", "SWKS", "SYF", "SYK",
    "SYY", "T", "TAP", "TCOM", "TDG", "TEL", "TER", "TFC", "TGT", "TJX",
    "TMO", "TMUS", "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TXN",
    "TYL", "UA", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB",
    "V", "VICI", "VLO", "VMC", "VRSK", "VRSN", "VRTX", "VTR", "VFC", "VICI",
    "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WHR", "WMB",
    "WMT", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XRAY", "XYL", "YUM",
    "Z", "ZBH", "ZION", "ZM", "ZTS",
    # Pakistan Stock Exchange (PSX)
    "LUCK.PSX", "ENGRO.PSX", "SYS.PSX", "HUBC.PSX", "MCB.PSX", 
    "OGDC.PSX", "PPL.PSX", "MARI.PSX", "EFERT.PSX", "TRG.PSX"
]


class MassTrainerConfig:
    """Configuration for mass trainer"""
    def __init__(self):
        self.batch_size = 10  # Process 10 stocks at a time
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.checkpoint_interval = 50  # Save progress every 50 stocks
        self.rate_limit_delay = 1.0  # Delay between API calls
        self.max_memory_mb = 2000  # Memory limit before cleanup
        self.model_dir = os.path.dirname(os.path.abspath(__file__))
        self.checkpoint_file = os.path.join(self.model_dir, "training_checkpoint.json")
        self.log_file = os.path.join(self.model_dir, "mass_trainer.log")
        self.max_training_time = 60  # seconds per stock


class StockTrainer:
    """Individual stock trainer with error handling"""

    def __init__(self, ticker: str, config: MassTrainerConfig):
        self.ticker = ticker.upper()
        self.config = config
        self.model_path = os.path.join(config.model_dir, f"{ticker}_model.pkl")
        self.status = "pending"
        self.error = None
        self.duration = 0

    def train(self) -> Dict:
        """Train model using unified StockPredictor engine"""
        start_time = time.time()

        try:
            from stock_predictor import StockPredictor
            
            # Use the main engine for consistency
            predictor = StockPredictor(self.ticker)
            
            # Train using the standardized pipeline
            test_acc = predictor.train()
            
            # Save using the standardized format
            predictor.save_model(self.model_path)
            
            self.duration = time.time() - start_time
            self.status = "success"

            return {
                "status": "success",
                "ticker": self.ticker,
                "duration": self.duration,
                "test_accuracy": test_acc,
                "samples": len(predictor.data) if predictor.data is not None else 0
            }

        except Exception as e:
            self.error = str(e)
            self.duration = time.time() - start_time
            self.status = "failed"
            return {
                "status": "failed",
                "ticker": self.ticker,
                "error": self.error,
                "duration": self.duration
            }

    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        df = df.copy()

        # Returns
        df['Returns'] = df['Close'].pct_change()

        # Moving averages
        for window in [5, 10, 20, 50]:
            df[f'SMA_{window}'] = df['Close'].rolling(window).mean()
            df[f'Volatility_{window}'] = df['Returns'].rolling(window).std()

        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df['Close'].ewm(span=12).mean()
        ema26 = df['Close'].ewm(span=26).mean()
        df['MACD'] = ema12 - ema26

        # Target: 1 if next day up, 0 if down
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)

        return df


class MassTrainer:
    """Main mass trainer with checkpointing and memory management"""

    def __init__(self, config: Optional[MassTrainerConfig] = None):
        self.config = config or MassTrainerConfig()
        self.results = []
        self.checkpoint = self._load_checkpoint()
        self.processed = set(self.checkpoint.get("completed", []))
        self.failed = set(self.checkpoint.get("failed", []))

    def _load_checkpoint(self) -> Dict:
        """Load checkpoint if exists and handle self-healing"""
        if os.path.exists(self.config.checkpoint_file):
            try:
                with open(self.config.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    # Self-healing: convert list to dict if needed
                    if isinstance(data, list):
                        logger.info("Converting list-based checkpoint to dict format...")
                        return {"completed": data, "failed": [], "results": []}
                    return data
            except Exception as e:
                logger.error(f"Checkpoint load error: {e}")
        return {"completed": [], "failed": [], "results": []}

    def _save_checkpoint(self):
        """Save checkpoint"""
        checkpoint = {
            "completed": list(self.processed),
            "failed": list(self.failed),
            "results": self.results[-100:],  # Keep last 100
            "last_updated": datetime.now().isoformat()
        }
        with open(self.config.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

    def _check_memory(self):
        """Check and manage memory"""
        try:
            import psutil
            memory_mb = psutil.virtual_memory().used / (1024 * 1024)
            if memory_mb > self.config.max_memory_mb:
                logger.warning(f"Memory usage high: {memory_mb:.0f}MB - running GC")
                gc.collect()
        except:
            pass

    def train_batch(self, tickers: List[str]) -> List[Dict]:
        """Train a batch of stocks"""
        results = []

        for ticker in tickers:
            if ticker in self.processed:
                logger.info(f"Skipping {ticker} - already processed")
                continue

            if ticker in self.failed:
                logger.info(f"Skipping {ticker} - previously failed")
                continue

            logger.info(f"Training {ticker}...")
            trainer = StockTrainer(ticker, self.config)

            # Retry logic
            for attempt in range(self.config.max_retries):
                try:
                    result = trainer.train()
                    results.append(result)

                    if result["status"] == "success":
                        self.processed.add(ticker)
                        logger.info(f"  -> Success: {ticker} ({result['duration']:.1f}s)")
                    else:
                        if attempt < self.config.max_retries - 1:
                            logger.warning(f"  -> Retry {attempt+1}: {ticker}")
                            time.sleep(self.config.retry_delay)
                            continue
                        else:
                            self.failed.add(ticker)
                            logger.error(f"  -> Failed: {ticker} - {result.get('error', 'Unknown')}")

                    break

                except Exception as e:
                    if attempt < self.config.max_retries - 1:
                        logger.warning(f"  -> Error {attempt+1}: {e}")
                        time.sleep(self.config.retry_delay)
                    else:
                        self.failed.add(ticker)
                        results.append({"status": "failed", "ticker": ticker, "error": str(e)})

            self.results.append(results[-1] if results else {})

            # Rate limiting
            time.sleep(self.config.rate_limit_delay)

            # Memory check
            self._check_memory()

            # Checkpoint
            if len(self.processed) % self.config.checkpoint_interval == 0:
                self._save_checkpoint()

        return results

    def train_all(self, tickers: List[str] = None, limit: int = None) -> Dict:
        """Train all stocks in batches"""
        tickers = tickers or FULL_S_P_500[:limit] if limit else FULL_S_P_500

        total = len(tickers)
        logger.info(f"Starting mass training for {total} stocks...")

        batch_size = self.config.batch_size
        batches = [tickers[i:i+batch_size] for i in range(0, len(tickers), batch_size)]

        for i, batch in enumerate(batches):
            logger.info(f"\n{'='*50}")
            logger.info(f"Batch {i+1}/{len(batches)} - {len(batch)} stocks")
            logger.info(f"{'='*50}")

            results = self.train_batch(batch)
            self._save_checkpoint()

            # Summary
            success = sum(1 for r in results if r.get("status") == "success")
            failed = len(results) - success

            logger.info(f"\nBatch {i+1} Summary:")
            logger.info(f"  Success: {success}")
            logger.info(f"  Failed: {failed}")
            logger.info(f"  Total processed: {len(self.processed)}/{total}")

        return self.get_summary()

    def get_summary(self) -> Dict:
        """Get training summary"""
        return {
            "total_tickers": len(FULL_S_P_500),
            "completed": len(self.processed),
            "failed": len(self.failed),
            "success_rate": len(self.processed) / (len(self.processed) + len(self.failed)) * 100 if self.processed or self.failed else 0,
            "checkpoints": self.results[-10:]
        }


def run_mass_trainer():
    """Run the mass trainer"""
    config = MassTrainerConfig()

    print("\n" + "="*60)
    print("  MASS TRAINER - S&P 500")
    print("="*60)
    print(f"\nTotal stocks: {len(FULL_S_P_500)}")
    print(f"Batch size: {config.batch_size}")
    print(f"Checkpoint file: {config.checkpoint_file}")
    print("="*60)

    trainer = MassTrainer(config)

    # Train all stocks
    result = trainer.train_all()

    print("\n" + "="*60)
    print("  TRAINING COMPLETE")
    print("="*60)
    print(f"Completed: {result['completed']}")
    print(f"Failed: {result['failed']}")
    print(f"Success Rate: {result['success_rate']:.1f}%")
    print("="*60)

    return result


if __name__ == "__main__":
    run_mass_trainer()