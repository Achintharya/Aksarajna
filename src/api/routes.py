from flask import Blueprint, Flask, jsonify, request

from src.api.middleware import auth_required, api_key_required, subscription_required
from src.auth.auth_service import auth_service
from src.models.user import SubscriptionTier
from src.utils.logger import logger

# Create blueprints for different API sections
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
public_bp = Blueprint('public', __name__, url_prefix='/api/public')
user_bp = Blueprint('user', __name__, url_prefix='/api/user')
article_bp = Blueprint('article', __name__, url_prefix='/api/article')

# Auth routes
@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.json
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')
    
    if not email or not name or not password:
        return jsonify({
            'success': False,
            'message': 'Email, name, and password are required'
        }), 400
    
    success, message, user = auth_service.register_user(email, name, password)
    
    if not success:
        return jsonify({
            'success': False,
            'message': message
        }), 400
    
    return jsonify({
        'success': True,
        'message': message,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'api_key': user.api_key
        }
    })

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user."""
    data = request.json
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({
            'success': False,
            'message': 'Email and password are required'
        }), 400
    
    success, message, token = auth_service.authenticate(email, password)
    
    if not success:
        return jsonify({
            'success': False,
            'message': message
        }), 401
    
    return jsonify({
        'success': True,
        'message': message,
        'token': token
    })

# Public routes
@public_bp.route('/info', methods=['GET'])
def info():
    """Get public information about the API."""
    return jsonify({
        'success': True,
        'name': 'Varnika API',
        'version': '1.0.0',
        'description': 'AI-powered article generation API',
        'subscription_tiers': {
            'free': {
                'name': 'Free',
                'description': 'Basic access with limited usage',
                'monthly_quota': auth_service.tier_quotas[SubscriptionTier.FREE]
            },
            'basic': {
                'name': 'Basic',
                'description': 'Standard access with moderate usage',
                'monthly_quota': auth_service.tier_quotas[SubscriptionTier.BASIC]
            },
            'premium': {
                'name': 'Premium',
                'description': 'Premium access with high usage',
                'monthly_quota': auth_service.tier_quotas[SubscriptionTier.PREMIUM]
            }
        }
    })

# User routes
@user_bp.route('/me', methods=['GET'])
@auth_required
def get_user():
    """Get the current user's information."""
    user = request.user
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'subscription': {
                'tier': user.subscription.tier,
                'is_active': user.subscription.is_active,
                'monthly_quota': user.subscription.monthly_quota,
                'monthly_usage': user.subscription.monthly_usage
            }
        }
    })

@user_bp.route('/subscription', methods=['GET'])
@auth_required
def get_subscription():
    """Get the current user's subscription information."""
    user = request.user
    
    return jsonify({
        'success': True,
        'subscription': {
            'tier': user.subscription.tier,
            'start_date': user.subscription.start_date.isoformat(),
            'end_date': user.subscription.end_date.isoformat() if user.subscription.end_date else None,
            'is_active': user.subscription.is_active,
            'monthly_quota': user.subscription.monthly_quota,
            'monthly_usage': user.subscription.monthly_usage,
            'last_reset_date': user.subscription.last_reset_date.isoformat()
        }
    })

@user_bp.route('/usage', methods=['GET'])
@auth_required
def get_usage():
    """Get the current user's usage information."""
    user = request.user
    
    return jsonify({
        'success': True,
        'usage': {
            'monthly_quota': user.subscription.monthly_quota,
            'monthly_usage': user.subscription.monthly_usage,
            'remaining': max(0, user.subscription.monthly_quota - user.subscription.monthly_usage),
            'last_reset_date': user.subscription.last_reset_date.isoformat(),
            'history': user.usage_history
        }
    })

# Article routes
@article_bp.route('/generate', methods=['POST'])
@api_key_required
@subscription_required
def generate_article():
    """Generate an article."""
    data = request.json
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    query = data.get('query')
    article_type = data.get('article_type', 'detailed')
    
    if not query:
        return jsonify({
            'success': False,
            'message': 'Query is required'
        }), 400
    
    # This is a placeholder for the actual article generation logic
    # In a real implementation, this would call the article generation service
    
    return jsonify({
        'success': True,
        'message': 'Article generation started',
        'task_id': '123456789'
    })

@article_bp.route('/status/<task_id>', methods=['GET'])
@api_key_required
def get_article_status(task_id):
    """Get the status of an article generation task."""
    # This is a placeholder for the actual status checking logic
    # In a real implementation, this would check the status of the task
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': 'completed',
        'progress': 100
    })

def register_routes(app: Flask) -> None:
    """
    Register all API routes with the Flask application.
    
    Args:
        app: The Flask application.
    """
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(article_bp)
    
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
