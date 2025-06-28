import os
from flask import Flask
from flask_socketio import SocketIO

from src.api.routes import register_routes
from src.utils.config_manager import config_manager
from src.utils.logger import logger

def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: The configured Flask application.
    """
    # Create the Flask application
    app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
    
    # Configure the application
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
    app.config['DEBUG'] = config_manager.get('server.debug', False)
    
    # Register routes
    register_routes(app)
    
    # Add a route to serve the React app
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        """Serve the React app."""
        if path != "" and os.path.exists(app.static_folder + '/' + path):
            return app.send_static_file(path)
        return app.send_static_file('index.html')
    
    logger.info(f"Flask application created in {config_manager.env} mode")
    return app

def create_socketio(app):
    """
    Create and configure the SocketIO instance.
    
    Args:
        app: The Flask application.
        
    Returns:
        SocketIO: The configured SocketIO instance.
    """
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Define SocketIO event handlers
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.debug('Client connected')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.debug('Client disconnected')
    
    logger.info("SocketIO initialized")
    return socketio

def run_app():
    """
    Run the Flask application with SocketIO.
    """
    app = create_app()
    socketio = create_socketio(app)
    
    host = config_manager.get('server.host', '0.0.0.0')
    port = int(config_manager.get('server.port', 5000))
    debug = config_manager.get('server.debug', False)
    
    logger.info(f"Starting server on {host}:{port} (debug: {debug})")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    run_app()
