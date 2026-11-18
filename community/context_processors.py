from .models import Notification, DirectMessage

def notification_count(request):
    """Context Processor สำหรับจำนวนการแจ้งเตือนและข้อความที่ยังไม่อ่าน"""
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).exclude(notification_type='message').count()
        
        unread_messages = DirectMessage.objects.filter(
            to_user=request.user, 
            is_read=False
        ).count()
    else:
        unread_notifications = 0
        unread_messages = 0
        
    return {
        'unread_notifications_count': unread_notifications,
        'unread_messages_count': unread_messages,
    }
