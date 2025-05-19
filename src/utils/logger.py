import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.utils.config_manager import config_manager

class LoggerSetup:
    """
    Logger setup for the application.
    Configures logging based on the application configuration.
    """
    
    def __init__(self):
        """Initialize the logger setup."""
        self.config = config_manager
        self.setup_logging()
    
    def setup_logging(self):
        """Set up logging based on configuration."""
        log_level = self._get_log_level()
        log_format = self.config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = self.config.get('logging.file', './logs/application.log')
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                RotatingFileHandler(
                    log_file,
                    maxBytes=10485760,  # 10MB
                    backupCount=5
                ),
                logging.StreamHandler()
            ]
        )
        
        # Set up specific loggers
        self._setup_library_loggers()
        
        # Create and return the application logger
        self.logger = logging.getLogger('varnika')
        self.logger.setLevel(log_level)
        
        self.logger.info(f"Logging initialized with level {log_level}")
        self.logger.info(f"Environment: {self.config.env}")
    
    def _get_log_level(self):
        """Get the log level from configuration."""
        log_level_str = self.config.get('logging.level', 'INFO')
        return getattr(logging, log_level_str)
    
    def _setup_library_loggers(self):
        """Set up loggers for third-party libraries."""
        # Set up specific loggers for libraries
        libraries = {
            'werkzeug': logging.WARNING,
            'urllib3': logging.WARNING,
            'aiohttp': logging.WARNING,
            'requests': logging.WARNING,
            'crawl4ai': logging.INFO,
            'crewai': logging.INFO
        }
        
        for lib, level in libraries.items():
            logging.getLogger(lib).setLevel(level)

# Create a singleton instance
logger_setup = LoggerSetup()
logger = logger_setup.logger
