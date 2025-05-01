import os
from dotenv import load_dotenv
import logging
import json
from pathlib import Path

# Load environment variables
load_dotenv(dotenv_path='./config/.env')

# Configure logging
def setup_logging(level=logging.INFO):
    """Set up logging configuration"""
    log_dir = Path('./logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / 'application.log')
        ]
    )
    return logging.getLogger()

# Default configuration
DEFAULT_CONFIG = {
    # API Keys (loaded from environment variables)
    "api_keys": {
        "groq": os.getenv("GROQ_API_KEY"),
        "mistral": os.getenv("MISTRAL_API_KEY"),
        "serper": os.getenv("SERPER_API_KEY"),
    },
    
    # Models
    "models": {
        "summarizer": "groq/llama-3.1-8b-instant",
        "article_writer": "mistral",
        "extraction": "mistral/mistral-small-latest"
    },
    
    # File paths
    "paths": {
        "context_json": "./data/context.json",
        "context_txt": "./data/context.txt",
        "writing_style": "./data/writing_style.txt",
        "sources": "./data/sources.txt",
        "articles_dir": "./articles"
    },
    
    # Web crawling settings
    "web_crawling": {
        "max_results": 6,
        "max_retries": 5,
        "backoff_factor": 1,
        "timeout": 30,
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    },
    
    # Cache settings
    "cache": {
        "enabled": True,
        "ttl": 3600,  # Time to live in seconds (1 hour)
        "max_size": 100  # Maximum number of items in cache
    }
}

class Config:
    """Configuration manager for the application"""
    
    def __init__(self, config_file=None):
        self.config = DEFAULT_CONFIG.copy()
        
        # Load from config file if provided
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    self._merge_configs(self.config, file_config)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error loading config file: {e}")
    
    def _merge_configs(self, base, override):
        """Recursively merge override dict into base dict"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value
    
    def get(self, key, default=None):
        """Get a configuration value using dot notation (e.g., 'web_crawling.max_results')"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key, value):
        """Set a configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self, config_file):
        """Save the current configuration to a file"""
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception:
            return False

# Create a simple in-memory cache
class SimpleCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, ttl=3600, max_size=100):
        self.cache = {}
        self.ttl = ttl
        self.max_size = max_size
        self.timestamps = {}
        import time
        self.time = time
    
    def get(self, key):
        """Get a value from the cache if it exists and hasn't expired"""
        if key in self.cache:
            # Check if the item has expired
            if self.time.time() - self.timestamps[key] > self.ttl:
                # Remove expired item
                del self.cache[key]
                del self.timestamps[key]
                return None
            return self.cache[key]
        return None
    
    def set(self, key, value):
        """Set a value in the cache"""
        # If cache is full, remove the oldest item
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.timestamps, key=self.timestamps.get)
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        
        self.cache[key] = value
        self.timestamps[key] = self.time.time()
    
    def clear(self):
        """Clear the cache"""
        self.cache.clear()
        self.timestamps.clear()

# Create global instances
config = Config()
cache = SimpleCache(
    ttl=config.get('cache.ttl', 3600),
    max_size=config.get('cache.max_size', 100)
)
logger = setup_logging()

# Ensure directories exist
def ensure_directories():
    """Ensure all required directories exist"""
    Path(config.get('paths.articles_dir')).mkdir(exist_ok=True)
    Path('./data').mkdir(exist_ok=True)
    Path('./config').mkdir(exist_ok=True)

ensure_directories()
