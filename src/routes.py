from flask import Blueprint, Flask, jsonify, request

from src.utils.logger import logger

# Create blueprint for public API
public_bp = Blueprint('public', __name__, url_prefix='/api/public')

# Public routes
@public_bp.route('/info', methods=['GET'])
def info():
    """Get public information about the API."""
    return jsonify({
        'success': True,
        'name': 'Varnika API',
        'version': '1.0.0',
        'description': 'AI-powered article generation API'
    })

def register_routes(app: Flask) -> None:
    """
    Register all API routes with the Flask application.
    
    Args:
        app: The Flask application.
    """
    # Register blueprints
    app.register_blueprint(public_bp)
    
    # Add status endpoint
    @app.route('/api/status', methods=['GET'])
    def get_status():
        """Get API status."""
        return jsonify({
            'success': True,
            'status': 'running',
            'message': 'API is operational'
        })
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': 'Not found'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'message': 'Method not allowed'
        }), 405
    
    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500
