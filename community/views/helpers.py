from ..models import Report, Friendship


def pending_reports_badge(request):
    """Badge callback สำหรับแสดงจำนวนรายงานที่รอตรวจสอบบน Sidebar"""
    count = Report.objects.filter(status='pending').count()
    return str(count) if count > 0 else ""


def get_user_friend_ids(user):
    """คืนค่ารายชื่อ ID ของเพื่อนทั้งหมดของผู้ใช้"""
    if not user or not user.is_authenticated:
        return []
    friends_1 = Friendship.objects.filter(from_user=user, is_accepted=True).values_list('to_user_id', flat=True)
    friends_2 = Friendship.objects.filter(to_user=user, is_accepted=True).values_list('from_user_id', flat=True)
    return list(friends_1) + list(friends_2)

