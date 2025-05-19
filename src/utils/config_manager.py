import os
import json
from dotenv import load_dotenv
from pathlib import Path

class ConfigManager:
    """
    Configuration manager for the application.
    Handles loading configuration from environment variables and config files.
    Supports different environments (development, testing, production).
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config = {}
        self.env = os.getenv('VARNIKA_ENV', 'development')
        
        # Load environment variables
        load_dotenv()
        
        # Load base configuration
        self._load_base_config()
        
        # Load environment-specific configuration
        self._load_env_config()
        
        # Override with environment variables
        self._override_from_env()
    
    def _load_base_config(self):
        """Load base configuration from config/base.json."""
        base_config_path = Path(__file__).parent.parent.parent / 'config' / 'base.json'
        if base_config_path.exists():
            with open(base_config_path, 'r') as f:
                self.config = json.load(f)
    
    def _load_env_config(self):
        """Load environment-specific configuration."""
        env_config_path = Path(__file__).parent.parent.parent / 'config' / f'{self.env}.json'
        if env_config_path.exists():
            with open(env_config_path, 'r') as f:
                env_config = json.load(f)
                self._merge_config(self.config, env_config)
    
    def _merge_config(self, base, override):
        """Recursively merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _override_from_env(self):
        """Override configuration with environment variables."""
        # API keys
        if os.getenv('MISTRAL_API_KEY'):
            self._set_nested_value(self.config, 'api_keys.mistral', os.getenv('MISTRAL_API_KEY'))
        if os.getenv('GROQ_API_KEY'):
            self._set_nested_value(self.config, 'api_keys.groq', os.getenv('GROQ_API_KEY'))
        if os.getenv('SERPER_API_KEY'):
            self._set_nested_value(self.config, 'api_keys.serper', os.getenv('SERPER_API_KEY'))
        
        # Models
        if os.getenv('EXTRACTION_MODEL'):
            self._set_nested_value(self.config, 'models.extraction', os.getenv('EXTRACTION_MODEL'))
        if os.getenv('SUMMARIZER_MODEL'):
            self._set_nested_value(self.config, 'models.summarizer', os.getenv('SUMMARIZER_MODEL'))
        if os.getenv('ARTICLE_WRITER_MODEL'):
            self._set_nested_value(self.config, 'models.article_writer', os.getenv('ARTICLE_WRITER_MODEL'))
        
        # Paths
        if os.getenv('DATA_DIR'):
            data_dir = os.getenv('DATA_DIR')
            self._set_nested_value(self.config, 'paths.data_dir', data_dir)
            self._set_nested_value(self.config, 'paths.context_json', os.path.join(data_dir, 'context.json'))
            self._set_nested_value(self.config, 'paths.context_txt', os.path.join(data_dir, 'context.txt'))
            self._set_nested_value(self.config, 'paths.sources', os.path.join(data_dir, 'sources.txt'))
            self._set_nested_value(self.config, 'paths.writing_style', os.path.join(data_dir, 'writing_style.txt'))
        
        if os.getenv('ARTICLES_DIR'):
            self._set_nested_value(self.config, 'paths.articles_dir', os.getenv('ARTICLES_DIR'))
        
        # Cache
        if os.getenv('CACHE_ENABLED'):
            self._set_nested_value(self.config, 'cache.enabled', os.getenv('CACHE_ENABLED').lower() == 'true')
        if os.getenv('CACHE_TTL'):
            self._set_nested_value(self.config, 'cache.ttl', int(os.getenv('CACHE_TTL')))
        
        # Web crawling
        if os.getenv('WEB_CRAWLING_TIMEOUT'):
            self._set_nested_value(self.config, 'web_crawling.timeout', int(os.getenv('WEB_CRAWLING_TIMEOUT')))
        if os.getenv('WEB_CRAWLING_BACKOFF_FACTOR'):
            self._set_nested_value(self.config, 'web_crawling.backoff_factor', float(os.getenv('WEB_CRAWLING_BACKOFF_FACTOR')))
        
        # Subscription-related settings (for future use)
        if os.getenv('SUBSCRIPTION_ENABLED'):
            self._set_nested_value(self.config, 'subscription.enabled', os.getenv('SUBSCRIPTION_ENABLED').lower() == 'true')
        if os.getenv('FREE_TIER_LIMIT'):
            self._set_nested_value(self.config, 'subscription.free_tier_limit', int(os.getenv('FREE_TIER_LIMIT')))
        if os.getenv('BASIC_TIER_LIMIT'):
            self._set_nested_value(self.config, 'subscription.basic_tier_limit', int(os.getenv('BASIC_TIER_LIMIT')))
        if os.getenv('PREMIUM_TIER_LIMIT'):
            self._set_nested_value(self.config, 'subscription.premium_tier_limit', int(os.getenv('PREMIUM_TIER_LIMIT')))
    
    def _set_nested_value(self, config, path, value):
        """Set a nested value in the configuration dictionary."""
        keys = path.split('.')
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def get(self, path, default=None):
        """
        Get a configuration value by path.
        
        Args:
            path (str): Dot-separated path to the configuration value.
            default: Default value to return if the path is not found.
            
        Returns:
            The configuration value, or the default if not found.
        """
        keys = path.split('.')
        current = self.config
        for key in keys:
            if key not in current:
                return default
            current = current[key]
        return current
    
    def get_all(self):
        """Get the entire configuration dictionary."""
        return self.config
    
    def is_production(self):
        """Check if the current environment is production."""
        return self.env == 'production'
    
    def is_development(self):
        """Check if the current environment is development."""
        return self.env == 'development'
    
    def is_testing(self):
        """Check if the current environment is testing."""
        return self.env == 'testing'

# Create a singleton instance
config_manager = ConfigManager()
