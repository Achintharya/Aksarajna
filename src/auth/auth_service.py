import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import jwt
from pydantic import EmailStr

from src.models.user import User, Subscription, SubscriptionTier
from src.utils.config_manager import config_manager
from src.utils.logger import logger

class AuthService:
    """
    Authentication service for the application.
    Handles user authentication, registration, and token management.
    """
    
    def __init__(self):
        """Initialize the authentication service."""
        self.config = config_manager
        self.secret_key = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
        self.token_expiry = int(os.getenv('JWT_TOKEN_EXPIRY', '86400'))  # Default: 24 hours
        
        # In-memory user store (replace with database in production)
        self.users: Dict[str, User] = {}
        self.email_to_id: Dict[str, str] = {}
        self.api_keys: Dict[str, str] = {}  # API key to user ID mapping
        
        # Load subscription tier quotas from config
        self.tier_quotas = {
            SubscriptionTier.FREE: self.config.get('subscription.free_tier_limit', 5),
            SubscriptionTier.BASIC: self.config.get('subscription.basic_tier_limit', 20),
            SubscriptionTier.PREMIUM: self.config.get('subscription.premium_tier_limit', 100)
        }
        
        logger.info("Authentication service initialized")
    
    def _hash_password(self, password: str) -> str:
        """
        Hash a password using a secure algorithm.
        
        Args:
            password (str): The password to hash.
            
        Returns:
            str: The hashed password.
        """
        # In a real implementation, use a proper password hashing library like bcrypt
        salt = os.getenv('PASSWORD_SALT', 'default_salt')
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def _generate_api_key(self) -> str:
        """
        Generate a new API key.
        
        Returns:
            str: The generated API key.
        """
        return secrets.token_urlsafe(32)
    
    def register_user(self, email: EmailStr, name: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user.
        
        Args:
            email (EmailStr): The user's email.
            name (str): The user's name.
            password (str): The user's password.
            
        Returns:
            Tuple[bool, str, Optional[User]]: A tuple containing:
                - bool: True if registration was successful, False otherwise.
                - str: A message describing the result.
                - Optional[User]: The registered user, or None if registration failed.
        """
        # Check if email is already registered
        if email.lower() in self.email_to_id:
            return False, "Email already registered", None
        
        # Create a new user
        user_id = str(uuid.uuid4())
        api_key = self._generate_api_key()
        
        # Create subscription with appropriate quota
        subscription = Subscription(
            tier=SubscriptionTier.FREE,
            monthly_quota=self.tier_quotas[SubscriptionTier.FREE]
        )
        
        user = User(
            id=user_id,
            email=email,
            name=name,
            hashed_password=self._hash_password(password),
            subscription=subscription,
            api_key=api_key
        )
        
        # Store the user
        self.users[user_id] = user
        self.email_to_id[email.lower()] = user_id
        self.api_keys[api_key] = user_id
        
        logger.info(f"User registered: {email}")
        return True, "User registered successfully", user
    
    def authenticate(self, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        Authenticate a user with email and password.
        
        Args:
            email (str): The user's email.
            password (str): The user's password.
            
        Returns:
            Tuple[bool, str, Optional[str]]: A tuple containing:
                - bool: True if authentication was successful, False otherwise.
                - str: A message describing the result.
                - Optional[str]: The JWT token if authentication was successful, None otherwise.
        """
        # Check if email exists
        email_lower = email.lower()
        if email_lower not in self.email_to_id:
            return False, "Invalid email or password", None
        
        # Get the user
        user_id = self.email_to_id[email_lower]
        user = self.users[user_id]
        
        # Check password
        if user.hashed_password != self._hash_password(password):
            return False, "Invalid email or password", None
        
        # Check if user is active
        if not user.is_active:
            return False, "Account is inactive", None
        
        # Update last login
        user.last_login = datetime.now()
        
        # Generate JWT token
        token = self._generate_token(user)
        
        logger.info(f"User authenticated: {email}")
        return True, "Authentication successful", token
    
    def authenticate_with_api_key(self, api_key: str) -> Tuple[bool, str, Optional[User]]:
        """
        Authenticate a user with an API key.
        
        Args:
            api_key (str): The API key.
            
        Returns:
            Tuple[bool, str, Optional[User]]: A tuple containing:
                - bool: True if authentication was successful, False otherwise.
                - str: A message describing the result.
                - Optional[User]: The authenticated user if successful, None otherwise.
        """
        # Check if API key exists
        if api_key not in self.api_keys:
            return False, "Invalid API key", None
        
        # Get the user
        user_id = self.api_keys[api_key]
        user = self.users[user_id]
        
        # Check if user is active
        if not user.is_active:
            return False, "Account is inactive", None
        
        logger.info(f"User authenticated with API key: {user.email}")
        return True, "Authentication successful", user
    
    def _generate_token(self, user: User) -> str:
        """
        Generate a JWT token for a user.
        
        Args:
            user (User): The user to generate a token for.
            
        Returns:
            str: The generated JWT token.
        """
        payload = {
            'sub': user.id,
            'email': user.email,
            'name': user.name,
            'exp': datetime.utcnow() + timedelta(seconds=self.token_expiry)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Tuple[bool, str, Optional[User]]:
        """
        Verify a JWT token.
        
        Args:
            token (str): The JWT token to verify.
            
        Returns:
            Tuple[bool, str, Optional[User]]: A tuple containing:
                - bool: True if the token is valid, False otherwise.
                - str: A message describing the result.
                - Optional[User]: The user associated with the token if valid, None otherwise.
        """
        try:
            # Decode the token
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Get the user
            user_id = payload['sub']
            if user_id not in self.users:
                return False, "Invalid token", None
            
            user = self.users[user_id]
            
            # Check if user is active
            if not user.is_active:
                return False, "Account is inactive", None
            
            return True, "Token is valid", user
            
        except jwt.ExpiredSignatureError:
            return False, "Token has expired", None
        except jwt.InvalidTokenError:
            return False, "Invalid token", None
    
    def update_subscription(self, user_id: str, tier: SubscriptionTier, 
                           months: int = 1, payment_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update a user's subscription.
        
        Args:
            user_id (str): The user's ID.
            tier (SubscriptionTier): The subscription tier.
            months (int, optional): The number of months to add to the subscription. Defaults to 1.
            payment_id (str, optional): The payment ID. Defaults to None.
            
        Returns:
            Tuple[bool, str]: A tuple containing:
                - bool: True if the update was successful, False otherwise.
                - str: A message describing the result.
        """
        # Check if user exists
        if user_id not in self.users:
            return False, "User not found"
        
        user = self.users[user_id]
        
        # Update subscription
        now = datetime.now()
        
        # If the subscription is expired, start from now
        start_date = now
        if user.subscription.is_active and user.subscription.end_date and user.subscription.end_date > now:
            start_date = user.subscription.end_date
        
        end_date = start_date + timedelta(days=30 * months)
        
        user.subscription = Subscription(
            tier=tier,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            payment_id=payment_id,
            monthly_quota=self.tier_quotas[tier],
            monthly_usage=0,
            last_reset_date=now
        )
        
        logger.info(f"Subscription updated for user {user.email}: {tier.value} for {months} months")
        return True, f"Subscription updated to {tier.value} for {months} months"

# Create a singleton instance
auth_service = AuthService()
