from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr

class SubscriptionTier(str, Enum):
    """Subscription tier enum."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"

class Subscription(BaseModel):
    """Subscription model."""
    tier: SubscriptionTier = Field(default=SubscriptionTier.FREE)
    start_date: datetime = Field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    is_active: bool = Field(default=True)
    payment_id: Optional[str] = None
    
    # Usage tracking
    monthly_quota: int = Field(default=0)
    monthly_usage: int = Field(default=0)
    last_reset_date: datetime = Field(default_factory=datetime.now)

class User(BaseModel):
    """User model."""
    id: str
    email: EmailStr
    name: str
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    subscription: Subscription = Field(default_factory=Subscription)
    
    # API key for programmatic access
    api_key: Optional[str] = None
    
    # Usage history
    usage_history: List[Dict] = Field(default_factory=list)
    
    def can_use_service(self) -> bool:
        """Check if the user can use the service."""
        if not self.is_active:
            return False
        
        if not self.subscription.is_active:
            return False
        
        # Check if subscription has expired
        if self.subscription.end_date and self.subscription.end_date < datetime.now():
            return False
        
        # Check if user has exceeded monthly quota
        if self.subscription.monthly_usage >= self.subscription.monthly_quota:
            return False
        
        return True
    
    def increment_usage(self) -> bool:
        """
        Increment the user's usage counter.
        
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        # Check if we need to reset the monthly usage
        now = datetime.now()
        if (now.year > self.subscription.last_reset_date.year or 
            now.month > self.subscription.last_reset_date.month):
            self.subscription.monthly_usage = 0
            self.subscription.last_reset_date = now
        
        # Check if the user can use the service
        if not self.can_use_service():
            return False
        
        # Increment usage
        self.subscription.monthly_usage += 1
        
        # Add to usage history
        self.usage_history.append({
            "timestamp": now,
            "action": "api_call"
        })
        
        return True
