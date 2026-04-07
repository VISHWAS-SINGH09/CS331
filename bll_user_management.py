"""
Business Logic Layer - User Management Module
Handles business rules and logic for user operations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import re


class UserManagementBLL:
    """
    Business Logic Layer for User Management
    
    Responsibilities:
    - Validate user data
    - Apply business rules for user operations
    - Handle authentication and authorization
    - Transform user data between layers
    """
    
    def __init__(self):
        """Initialize BLL with configuration"""
        # Business rules configuration
        self.min_password_length = 8
        self.max_login_attempts = 5
        self.session_timeout_minutes = 30
        self.min_username_length = 3
        self.max_username_length = 50
    
    def validate_user_registration(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate user registration data
        
        Business Rules:
        - Username must be unique and valid format
        - Email must be valid format
        - Password must meet security requirements
        - Phone number must be valid format (if provided)
        
        Args:
            user_data: Dictionary containing user registration data
            
        Returns:
            Validation result with errors if any
        """
        errors = []
        
        # Validate username
        username = user_data.get('username', '').strip()
        if not username:
            errors.append("Username is required")
        elif len(username) < self.min_username_length:
            errors.append(f"Username must be at least {self.min_username_length} characters")
        elif len(username) > self.max_username_length:
            errors.append(f"Username cannot exceed {self.max_username_length} characters")
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append("Username can only contain letters, numbers, and underscores")
        
        # Validate email
        email = user_data.get('email', '').strip()
        if not email:
            errors.append("Email is required")
        elif not self._is_valid_email(email):
            errors.append("Invalid email format")
        
        # Validate password
        password = user_data.get('password', '')
        password_errors = self._validate_password(password)
        errors.extend(password_errors)
        
        # Validate phone (optional)
        phone = user_data.get('phone', '').strip()
        if phone and not self._is_valid_phone(phone):
            errors.append("Invalid phone number format")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_password(self, password: str) -> List[str]:
        """
        Validate password meets security requirements
        
        Business Rules:
        - Minimum length
        - Must contain uppercase letter
        - Must contain lowercase letter
        - Must contain number
        - Must contain special character
        """
        errors = []
        
        if len(password) < self.min_password_length:
            errors.append(f"Password must be at least {self.min_password_length} characters")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return errors
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        # Remove common separators
        phone = re.sub(r'[\s\-\(\)]', '', phone)
        # Check if it's 10 digits (US format) or starts with + for international
        return re.match(r'^(\+\d{1,3})?\d{10}$', phone) is not None
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user with business logic
        
        Business Logic Flow:
        1. Validate user data
        2. Check if username/email already exists
        3. Hash password
        4. Create user record
        5. Transform for presentation
        
        Args:
            user_data: User registration data
            
        Returns:
            Registration result
        """
        # Step 1: Validate
        validation = self.validate_user_registration(user_data)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors']
            }
        
        # Step 2: Check uniqueness (in real system, query database)
        # For now, assume unique
        
        # Step 3: Hash password
        password_hash = self._hash_password(user_data['password'])
        
        # Step 4: Create user record
        user_id = self._generate_user_id()
        
        # Step 5: Transform for presentation
        return {
            'success': True,
            'user_id': user_id,
            'username': user_data['username'],
            'email': user_data['email'],
            'created_at': datetime.now().isoformat(),
            'message': 'User registered successfully'
        }
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user credentials
        
        Business Rules:
        - Check login attempts
        - Validate credentials
        - Create session
        - Update last login
        
        Args:
            username: Username or email
            password: User password
            
        Returns:
            Authentication result with session token
        """
        # In real system, would:
        # 1. Check login attempts
        # 2. Query database for user
        # 3. Verify password hash
        # 4. Create session token
        
        # Mock successful authentication
        return {
            'success': True,
            'user_id': 'USER-001',
            'username': username,
            'session_token': self._generate_session_token(),
            'expires_at': self._calculate_session_expiry(),
            'message': 'Authentication successful'
        }
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"USER-{timestamp}"
    
    def _generate_session_token(self) -> str:
        """Generate session token"""
        timestamp = str(datetime.now().timestamp())
        return hashlib.sha256(timestamp.encode()).hexdigest()
    
    def _calculate_session_expiry(self) -> str:
        """Calculate session expiry time"""
        from datetime import timedelta
        expiry = datetime.now() + timedelta(minutes=self.session_timeout_minutes)
        return expiry.isoformat()
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile with business logic
        
        Business Rules:
        - Hide sensitive information
        - Include user statistics
        - Transform for presentation
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            User profile data
        """
        # In real system, would query database
        return {
            'success': True,
            'user_id': user_id,
            'username': 'john_doe',
            'email': 'john@example.com',
            'phone': '+1234567890',
            'created_at': '2024-01-01T00:00:00',
            'last_login': datetime.now().isoformat(),
            'statistics': {
                'total_disputes': 5,
                'approved_disputes': 3,
                'pending_disputes': 1,
                'rejected_disputes': 1,
                'trust_rating': 'Good'
            }
        }
    
    def update_user_profile(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user profile with validation
        
        Business Rules:
        - Validate updated fields
        - Don't allow username change
        - Require password for email change
        
        Args:
            user_id: User identifier
            update_data: Fields to update
            
        Returns:
            Update result
        """
        errors = []
        
        # Validate email if being updated
        if 'email' in update_data:
            if not self._is_valid_email(update_data['email']):
                errors.append("Invalid email format")
        
        # Validate phone if being updated
        if 'phone' in update_data:
            if not self._is_valid_phone(update_data['phone']):
                errors.append("Invalid phone number format")
        
        if errors:
            return {
                'success': False,
                'errors': errors
            }
        
        return {
            'success': True,
            'user_id': user_id,
            'updated_fields': list(update_data.keys()),
            'message': 'Profile updated successfully'
        }
    
    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Change user password with validation
        
        Business Rules:
        - Verify old password
        - Validate new password
        - Don't allow reuse of old password
        
        Args:
            user_id: User identifier
            old_password: Current password
            new_password: New password
            
        Returns:
            Password change result
        """
        # Validate new password
        password_errors = self._validate_password(new_password)
        if password_errors:
            return {
                'success': False,
                'errors': password_errors
            }
        
        # Check if new password is same as old
        if old_password == new_password:
            return {
                'success': False,
                'errors': ['New password must be different from old password']
            }
        
        # In real system, would verify old password and update
        return {
            'success': True,
            'user_id': user_id,
            'message': 'Password changed successfully'
        }
    
    def get_user_dispute_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get user's dispute history
        
        Business Rules:
        - Show only user's own disputes
        - Include summary statistics
        - Transform for presentation
        
        Args:
            user_id: User identifier
            limit: Maximum number of disputes to return
            
        Returns:
            Dispute history
        """
        # In real system, would query database
        return {
            'success': True,
            'user_id': user_id,
            'disputes': [
                {
                    'dispute_id': f'DISP-{i:04d}',
                    'order_id': f'ORD-{i:04d}',
                    'status': 'Approved' if i % 3 == 0 else 'Under Review',
                    'amount': 25.00 + i * 5,
                    'created_at': datetime.now().isoformat()
                }
                for i in range(1, min(limit + 1, 11))
            ],
            'summary': {
                'total': 10,
                'approved': 4,
                'pending': 3,
                'rejected': 3
            }
        }
    
    def calculate_user_trust_rating(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate user's overall trust rating
        
        Business Rules:
        - Based on dispute history
        - Approved disputes increase rating
        - Rejected disputes decrease rating
        - New users start with neutral rating
        
        Args:
            user_id: User identifier
            
        Returns:
            Trust rating information
        """
        # In real system, would calculate from actual history
        return {
            'success': True,
            'user_id': user_id,
            'trust_rating': 'Good',
            'trust_score': 75,
            'factors': {
                'total_disputes': 10,
                'approval_rate': 0.70,
                'account_age_days': 180,
                'fraud_flags': 0
            },
            'rating_explanation': 'Good standing based on dispute history'
        }


if __name__ == "__main__":
    # Test the BLL
    print("Testing User Management BLL")
    print("-" * 50)
    
    bll = UserManagementBLL()
    
    # Test registration validation
    test_user = {
        'username': 'john_doe',
        'email': 'john@example.com',
        'password': 'SecurePass123!',
        'phone': '1234567890'
    }
    
    validation = bll.validate_user_registration(test_user)
    print(f"Validation Result: {validation}")
    
    if validation['valid']:
        result = bll.register_user(test_user)
        print(f"Registration Result: {result.get('message')}")
    
    print("\nUser Management BLL test complete")
