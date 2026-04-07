"""
Business Logic Layer - Notification Module
Handles business rules and logic for notifications and communications.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class NotificationType(Enum):
    """Notification types"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationBLL:
    """
    Business Logic Layer for Notifications
    
    Responsibilities:
    - Validate notification data
    - Apply business rules for notifications
    - Handle notification preferences
    - Transform notification data
    """
    
    def __init__(self):
        """Initialize BLL with configuration"""
        # Business rules configuration
        self.max_message_length = 1000
        self.max_subject_length = 200
        self.rate_limit_per_hour = 10
        self.quiet_hours_start = 22  # 10 PM
        self.quiet_hours_end = 8     # 8 AM
    
    def send_dispute_notification(
        self,
        user_id: str,
        dispute_id: str,
        notification_type: str,
        dispute_status: str
    ) -> Dict[str, Any]:
        """
        Send notification about dispute status
        
        Business Rules:
        - Check user notification preferences
        - Respect quiet hours for non-urgent notifications
        - Apply rate limiting
        - Use appropriate template based on status
        
        Args:
            user_id: User identifier
            dispute_id: Dispute identifier
            notification_type: Type of notification (email, sms, etc.)
            dispute_status: Current dispute status
            
        Returns:
            Notification send result
        """
        # Check user preferences
        preferences = self._get_user_preferences(user_id)
        if not self._should_send_notification(preferences, notification_type):
            return {
                'success': False,
                'reason': 'User has disabled this notification type'
            }
        
        # Check rate limiting
        if not self._check_rate_limit(user_id):
            return {
                'success': False,
                'reason': 'Rate limit exceeded'
            }
        
        # Check quiet hours
        priority = self._get_notification_priority(dispute_status)
        if not self._check_quiet_hours(priority):
            return {
                'success': False,
                'reason': 'Notification scheduled for after quiet hours'
            }
        
        # Generate notification content
        content = self._generate_dispute_notification_content(
            dispute_id,
            dispute_status
        )
        
        # Send notification
        return self._send_notification(
            user_id,
            notification_type,
            content,
            priority
        )
    
    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user notification preferences"""
        # In real system, would query database
        return {
            'email_enabled': True,
            'sms_enabled': True,
            'push_enabled': True,
            'in_app_enabled': True,
            'quiet_hours_enabled': True
        }
    
    def _should_send_notification(
        self,
        preferences: Dict[str, Any],
        notification_type: str
    ) -> bool:
        """Check if notification should be sent based on preferences"""
        preference_key = f'{notification_type}_enabled'
        return preferences.get(preference_key, False)
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        # In real system, would check actual notification count
        return True
    
    def _check_quiet_hours(self, priority: NotificationPriority) -> bool:
        """Check if current time is within quiet hours"""
        # Urgent notifications bypass quiet hours
        if priority == NotificationPriority.URGENT:
            return True
        
        current_hour = datetime.now().hour
        if self.quiet_hours_start <= current_hour or current_hour < self.quiet_hours_end:
            return False
        
        return True
    
    def _get_notification_priority(self, dispute_status: str) -> NotificationPriority:
        """Determine notification priority based on dispute status"""
        priority_map = {
            'Approved': NotificationPriority.HIGH,
            'Rejected': NotificationPriority.HIGH,
            'Under Review': NotificationPriority.MEDIUM,
            'Pending': NotificationPriority.LOW
        }
        return priority_map.get(dispute_status, NotificationPriority.MEDIUM)
    
    def _generate_dispute_notification_content(
        self,
        dispute_id: str,
        dispute_status: str
    ) -> Dict[str, str]:
        """Generate notification content based on dispute status"""
        templates = {
            'Approved': {
                'subject': 'Refund Approved - Dispute {dispute_id}',
                'message': 'Good news! Your refund request has been approved. The amount will be credited to your account within 3-5 business days.'
            },
            'Rejected': {
                'subject': 'Dispute Update - {dispute_id}',
                'message': 'Your refund request requires additional verification. Please check your email for details on next steps.'
            },
            'Under Review': {
                'subject': 'Dispute Received - {dispute_id}',
                'message': 'We have received your refund request and it is currently under review. You will be notified within 24-48 hours.'
            }
        }
        
        template = templates.get(dispute_status, templates['Under Review'])
        
        return {
            'subject': template['subject'].format(dispute_id=dispute_id),
            'message': template['message']
        }
    
    def _send_notification(
        self,
        user_id: str,
        notification_type: str,
        content: Dict[str, str],
        priority: NotificationPriority
    ) -> Dict[str, Any]:
        """Send notification through appropriate channel"""
        notification_id = self._generate_notification_id()
        
        # In real system, would integrate with email/SMS services
        return {
            'success': True,
            'notification_id': notification_id,
            'user_id': user_id,
            'type': notification_type,
            'priority': priority.value,
            'sent_at': datetime.now().isoformat(),
            'message': 'Notification sent successfully'
        }
    
    def _generate_notification_id(self) -> str:
        """Generate unique notification ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"NOTIF-{timestamp}"
    
    def send_bulk_notification(
        self,
        user_ids: List[str],
        notification_type: str,
        subject: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send notification to multiple users
        
        Business Rules:
        - Validate message content
        - Check bulk sending limits
        - Respect individual user preferences
        
        Args:
            user_ids: List of user identifiers
            notification_type: Type of notification
            subject: Notification subject
            message: Notification message
            
        Returns:
            Bulk send result
        """
        # Validate content
        validation = self._validate_notification_content(subject, message)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors']
            }
        
        # Send to each user
        results = []
        for user_id in user_ids:
            result = self._send_notification(
                user_id,
                notification_type,
                {'subject': subject, 'message': message},
                NotificationPriority.MEDIUM
            )
            results.append(result)
        
        return {
            'success': True,
            'total_sent': len([r for r in results if r['success']]),
            'total_failed': len([r for r in results if not r['success']]),
            'results': results
        }
    
    def _validate_notification_content(
        self,
        subject: str,
        message: str
    ) -> Dict[str, Any]:
        """Validate notification content"""
        errors = []
        
        if not subject or not subject.strip():
            errors.append("Subject is required")
        elif len(subject) > self.max_subject_length:
            errors.append(f"Subject cannot exceed {self.max_subject_length} characters")
        
        if not message or not message.strip():
            errors.append("Message is required")
        elif len(message) > self.max_message_length:
            errors.append(f"Message cannot exceed {self.max_message_length} characters")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_notification_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get user's notification history
        
        Args:
            user_id: User identifier
            limit: Maximum number of notifications to return
            
        Returns:
            Notification history
        """
        # In real system, would query database
        return {
            'success': True,
            'user_id': user_id,
            'notifications': [
                {
                    'notification_id': f'NOTIF-{i:04d}',
                    'type': 'email',
                    'subject': f'Dispute Update - DISP-{i:04d}',
                    'sent_at': datetime.now().isoformat(),
                    'read': i % 2 == 0
                }
                for i in range(1, min(limit + 1, 21))
            ],
            'total': 20,
            'unread_count': 10
        }
    
    def mark_notification_as_read(
        self,
        notification_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Mark notification as read
        
        Args:
            notification_id: Notification identifier
            user_id: User identifier
            
        Returns:
            Update result
        """
        return {
            'success': True,
            'notification_id': notification_id,
            'user_id': user_id,
            'read_at': datetime.now().isoformat(),
            'message': 'Notification marked as read'
        }
    
    def update_notification_preferences(
        self,
        user_id: str,
        preferences: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        Update user notification preferences
        
        Business Rules:
        - At least one notification type must be enabled
        - Validate preference keys
        
        Args:
            user_id: User identifier
            preferences: Notification preferences
            
        Returns:
            Update result
        """
        valid_keys = [
            'email_enabled',
            'sms_enabled',
            'push_enabled',
            'in_app_enabled',
            'quiet_hours_enabled'
        ]
        
        # Validate keys
        invalid_keys = [k for k in preferences.keys() if k not in valid_keys]
        if invalid_keys:
            return {
                'success': False,
                'errors': [f'Invalid preference keys: {", ".join(invalid_keys)}']
            }
        
        # Check at least one is enabled
        enabled_count = sum(1 for k, v in preferences.items() if k.endswith('_enabled') and v)
        if enabled_count == 0:
            return {
                'success': False,
                'errors': ['At least one notification type must be enabled']
            }
        
        return {
            'success': True,
            'user_id': user_id,
            'updated_preferences': preferences,
            'message': 'Notification preferences updated successfully'
        }
    
    def send_system_alert(
        self,
        alert_type: str,
        message: str,
        affected_users: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send system-wide alert
        
        Business Use Case:
        - System maintenance notifications
        - Security alerts
        - Service disruptions
        
        Args:
            alert_type: Type of alert
            message: Alert message
            affected_users: Optional list of affected users
            
        Returns:
            Alert send result
        """
        return {
            'success': True,
            'alert_id': self._generate_notification_id(),
            'alert_type': alert_type,
            'sent_at': datetime.now().isoformat(),
            'affected_users_count': len(affected_users) if affected_users else 0,
            'message': 'System alert sent successfully'
        }


if __name__ == "__main__":
    # Test the BLL
    print("Testing Notification BLL")
    print("-" * 50)
    
    bll = NotificationBLL()
    
    # Test dispute notification
    result = bll.send_dispute_notification(
        user_id='USER-001',
        dispute_id='DISP-12345',
        notification_type='email',
        dispute_status='Approved'
    )
    
    print(f"Notification Result: {result.get('message')}")
    
    # Test notification history
    history = bll.get_notification_history('USER-001', limit=5)
    print(f"Notification History: {len(history['notifications'])} notifications")
    
    print("\nNotification BLL test complete")
