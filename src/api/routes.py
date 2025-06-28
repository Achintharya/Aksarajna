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
    
    # Add a simple run endpoint for the frontend
    @app.route('/api/run', methods=['POST'])
    def run_process():
        """Run the article generation process."""
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        query = data.get('query')
        components = data.get('components', [])
        article_type = data.get('article_type', 'detailed')
        filename = data.get('filename', 'article')
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Query is required'
            }), 400
        
        # For now, return a success response
        # In a real implementation, this would start the actual processing
        logger.info(f"Starting process for query: {query}")
        logger.info(f"Components: {components}")
        logger.info(f"Article type: {article_type}")
        logger.info(f"Filename: {filename}")
        
        return jsonify({
            'success': True,
            'message': 'Process started successfully',
            'task_id': 'demo-task-123'
        })
    
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
