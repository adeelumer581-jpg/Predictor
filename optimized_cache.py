
"""
Optimized Data Cache - Reduces API calls and improves performance
"""
import os
import time
import json
import hashlib

class OptimizedCache:
    def __init__(self, cache_dir=".cache", ttl=3600):
        self.cache_dir = cache_dir
        self.ttl = ttl
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, ticker, period):
        return hashlib.md5(f"{ticker}_{period}".encode()).hexdigest()

    def get(self, ticker, period):
        """Get cached data if valid"""
        key = self._get_cache_key(ticker, period)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")

        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < self.ttl:
                with open(cache_file, 'r') as f:
                    return json.load(f)
        return None

    def set(self, ticker, period, data):
        """Cache data"""
        key = self._get_cache_key(ticker, period)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")

        # Convert DataFrame to dict for JSON serialization
        if hasattr(data, 'to_dict'):
            data = data.to_dict()

        with open(cache_file, 'w') as f:
            json.dump(data, f)

    def clear(self):
        """Clear old cache files"""
        current_time = time.time()
        for filename in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.isfile(filepath):
                if current_time - os.path.getmtime(filepath) > self.ttl:
                    os.remove(filepath)
