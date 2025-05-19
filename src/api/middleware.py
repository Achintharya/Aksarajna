from functools import wraps
from typing import Callable, Dict, Optional, TypeVar, cast

from flask import Flask, Request, Response, jsonify, request

from src.auth.auth_service import auth_service
from src.models.user import User
from src.utils.logger import logger

# Type variable for the return type of the decorated function
T = TypeVar('T')

def auth_required(f: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to require authentication for an API endpoint.
    
    Args:
        f: The function to decorate.
        
    Returns:
        The decorated function.
    """
    @wraps(f)
    def decorated(*args: Dict, **kwargs: Dict) -> T:
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return cast(T, jsonify({
                'success': False,
                'message': 'Authorization header is missing'
            }), 401)
        
        # Check if it's a Bearer token
        parts = auth_header.split()
        if parts[0].lower() != 'bearer':
            return cast(T, jsonify({
                'success': False,
                'message': 'Authorization header must start with Bearer'
            }), 401)
        
        if len(parts) == 1:
            return cast(T, jsonify({
                'success': False,
                'message': 'Token not found'
            }), 401)
        
        if len(parts) > 2:
            return cast(T, jsonify({
                'success': False,
                'message': 'Authorization header must be Bearer token'
            }), 401)
        
        token = parts[1]
        
        # Verify the token
        success, message, user = auth_service.verify_token(token)
        if not success:
            return cast(T, jsonify({
                'success': False,
                'message': message
            }), 401)
        
        # Add the user to the request context
        request.user = user
        
        return f(*args, **kwargs)
    
    return decorated

def api_key_required(f: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to require API key authentication for an API endpoint.
    
    Args:
        f: The function to decorate.
        
    Returns:
        The decorated function.
    """
    @wraps(f)
    def decorated(*args: Dict, **kwargs: Dict) -> T:
        # Check for API key header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return cast(T, jsonify({
                'success': False,
                'message': 'API key is missing'
            }), 401)
        
        # Verify the API key
        success, message, user = auth_service.authenticate_with_api_key(api_key)
        if not success:
            return cast(T, jsonify({
                'success': False,
                'message': message
            }), 401)
        
        # Add the user to the request context
        request.user = user
        
        return f(*args, **kwargs)
    
    return decorated

def subscription_required(f: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to require an active subscription for an API endpoint.
    Must be used after auth_required or api_key_required.
    
    Args:
        f: The function to decorate.
        
    Returns:
        The decorated function.
    """
    @wraps(f)
    def decorated(*args: Dict, **kwargs: Dict) -> T:
        # Get the user from the request context
        user: Optional[User] = getattr(request, 'user', None)
        if not user:
            return cast(T, jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401)
        
        # Check if the user can use the service
        if not user.can_use_service():
            return cast(T, jsonify({
                'success': False,
                'message': 'Active subscription required'
            }), 403)
        
        # Increment usage
        if not user.increment_usage():
            return cast(T, jsonify({
                'success': False,
                'message': 'Usage limit exceeded'
            }), 403)
        
        return f(*args, **kwargs)
    
    return decorated

def setup_middleware(app: Flask) -> None:
    """
    Set up middleware for the Flask application.
    
    Args:
        app: The Flask application.
    """
    @app.before_request
    def before_request() -> Optional[Response]:
        """
        Before request middleware.
        
        Returns:
            Optional[Response]: A response if the request should be aborted, None otherwise.
        """
        # Log the request
        logger.debug(f"Request: {request.method} {request.path}")
        
        # Check if the subscription feature is enabled
        if not app.config.get('SUBSCRIPTION_ENABLED', False):
            return None
        
        # Skip authentication for public endpoints
        if request.path.startswith('/api/public'):
            return None
        
        # Skip authentication for auth endpoints
        if request.path.startswith('/api/auth'):
            return None
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return None
        
        # Check for API key
        api_key = request.headers.get('X-API-Key')
        if api_key:
            success, message, user = auth_service.authenticate_with_api_key(api_key)
            if success:
                request.user = user
                return None
        
        # Check for JWT token
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
                success, message, user = auth_service.verify_token(token)
                if success:
                    request.user = user
                    return None
        
        # If we get here, authentication failed
        return jsonify({
            'success': False,
            'message': 'Authentication required'
        }), 401
    
    @app.after_request
    def after_request(response: Response) -> Response:
        """
        After request middleware.
        
        Args:
            response: The response to be sent.
            
        Returns:
            Response: The modified response.
        """
        # Add CORS headers
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Key')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        # Log the response
        logger.debug(f"Response: {response.status}")
        
        return response
