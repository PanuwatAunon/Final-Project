from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from ..models import Notification, DirectMessage


@login_required
def api_unread_counts(request):
    """API สำหรับดึงจำนวนแจ้งเตือนและข้อความที่ยังไม่อ่านแบบ Real-time พร้อมข้อมูลแจ้งเตือนล่าสุด"""
    unread_notifs_qs = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).exclude(notification_type='message').select_related('from_user__profile', 'warning')
    
    unread_notifications = unread_notifs_qs.count()
    
    latest_notif = unread_notifs_qs.order_by('-created_at').first()
    latest_notif_data = None
    if latest_notif:
        title = latest_notif.from_user.username if latest_notif.from_user else 'ระบบ'
        desc = 'มีการแจ้งเตือนใหม่'
        if latest_notif.notification_type == 'friend_accept':
            desc = f'{title} ยอมรับคำขอเพิ่มเพื่อนของคุณแล้ว'
        elif latest_notif.notification_type == 'friend_request':
            desc = f'{title} ส่งคำขอเพิ่มเพื่อนถึงคุณ'
        elif latest_notif.notification_type == 'like':
            desc = f'{title} ชอบสิ่งที่คุณสร้าง'
        elif latest_notif.notification_type == 'reply':
            desc = f'{title} ตอบกลับกระทู้ของคุณ'
        elif latest_notif.notification_type == 'warning':
            reason = latest_notif.warning.reason if latest_notif.warning else ''
            desc = f'แจ้งเตือนคุณ: {reason}'

        latest_notif_data = {
            'id': latest_notif.id,
            'type': latest_notif.notification_type,
            'from_user': latest_notif.from_user.username if latest_notif.from_user else None,
            'title': title,
            'message': desc,
            'avatar': latest_notif.from_user.profile.avatar.url if (latest_notif.from_user and hasattr(latest_notif.from_user, 'profile') and latest_notif.from_user.profile.avatar) else None
        }

    unread_messages = DirectMessage.objects.filter(
        to_user=request.user, 
        is_read=False
    ).count()

    return JsonResponse({
        'unread_notifications_count': unread_notifications,
        'unread_messages_count': unread_messages,
        'latest_notification': latest_notif_data,
    })


@login_required
def notifications(request):
    """การแจ้งเตือน"""
    notifications_list = request.user.notifications.all().order_by('-created_at')
    
    context = {'notifications_list': notifications_list}
    return render(request, 'community/notifications.html', context)


@login_required
def read_notification(request, notification_id):
    """อ่านการแจ้งเตือน"""
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        unread_count = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).exclude(notification_type='message').count()
        return JsonResponse({
            'status': 'ok',
            'unread_notifications_count': unread_count
        })

    # เปลี่ยนเส้นทางตามประเภทการแจ้งเตือน
    if notification.notification_type in ['friend_request', 'friend_accept']:
        if notification.from_user:
            return redirect('community:user_profile', username=notification.from_user.username)
        return redirect('community:friends_list')
    elif notification.notification_type == 'message':
        if notification.from_user:
            return redirect('community:chat', username=notification.from_user.username)
        return redirect('community:inbox')
    elif notification.notification_type == 'warning':
        return redirect('community:notifications')
    elif notification.thread:
        return redirect('community:thread_detail', thread_id=notification.thread.id)
    elif notification.comment:
        return redirect('community:thread_detail', thread_id=notification.comment.thread.id)
    elif notification.guide:
        return redirect('community:guide_detail', guide_id=notification.guide.id)
    elif notification.from_user:
        return redirect('community:user_profile', username=notification.from_user.username)
    
    return redirect('community:notifications')


@login_required
def delete_notification(request, notification_id):
    """ลบการแจ้งเตือน"""
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    notification.delete()
    messages.success(request, 'ลบการแจ้งเตือนแล้ว')
    return redirect('community:notifications')


@login_required
def clear_notifications(request):
    """ล้างการแจ้งเตือนทั้งหมด"""
    request.user.notifications.all().delete()
    messages.success(request, 'ล้างการแจ้งเตือนทั้งหมดแล้ว')
    return redirect('community:notifications')
