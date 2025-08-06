import os
from flask import Flask

from src.routes import register_routes
from src.utils.config_manager import config_manager
from src.utils.logger import logger

def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: The configured Flask application.
    """
    # Create the Flask application
    app = Flask(__name__)
    
    # Configure the application
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
    app.config['DEBUG'] = config_manager.get('server.debug', False)
    
    # Register routes
    register_routes(app)
    
    logger.info(f"Flask application created in {config_manager.env} mode")
    return app

def run_app():
    """
    Run the Flask application.
    """
    app = create_app()
    
    host = config_manager.get('server.host', '0.0.0.0')
    port = int(config_manager.get('server.port', 5000))
    debug = config_manager.get('server.debug', False)
    
    logger.info(f"Starting server on {host}:{port} (debug: {debug})")
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_app()
