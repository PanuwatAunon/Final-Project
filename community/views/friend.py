from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse

from ..models import Friendship, Notification


@login_required
def api_friend_status(request, username):
    """API สำหรับตรวจสอบสถานะความเป็นเพื่อนแบบ Real-time"""
    user = get_object_or_404(User, username=username)
    is_friend = False
    is_pending = False
    has_incoming_request = False
    incoming_friendship_id = None

    if request.user != user:
        friendship = Friendship.objects.filter(
            Q(from_user=request.user, to_user=user) | 
            Q(from_user=user, to_user=request.user)
        ).first()

        if friendship:
            if friendship.is_accepted:
                is_friend = True
            elif friendship.from_user == request.user:
                is_pending = True
            elif friendship.to_user == request.user:
                has_incoming_request = True
                incoming_friendship_id = friendship.id

    return JsonResponse({
        'username': username,
        'is_friend': is_friend,
        'is_pending': is_pending,
        'has_incoming_request': has_incoming_request,
        'incoming_friendship_id': incoming_friendship_id,
    })


@login_required
def friends_list(request):
    """รายชื่อเพื่อน และค้นหาสมาชิก"""
    # Friend list
    friends = Friendship.objects.filter(
        Q(from_user=request.user, is_accepted=True) |
        Q(to_user=request.user, is_accepted=True)
    )
    pending = Friendship.objects.filter(to_user=request.user, is_accepted=False)
    
    # Search logic
    query = request.GET.get('q', '')
    search_results = User.objects.none()
    
    if query:
        search_results = User.objects.filter(username__icontains=query).exclude(pk=request.user.pk)
    
    context = {
        'friends': friends,
        'pending': pending,
        'query': query,
        'search_results': search_results
    }
    return render(request, 'community/friends_list.html', context)


@login_required
def add_friend(request, username):
    """ขอเพิ่มเพื่อน"""
    user = get_object_or_404(User, username=username)
    
    if user == request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'ไม่สามารถเพิ่มตัวเองเป็นเพื่อน'}, status=400)
        messages.error(request, 'ไม่สามารถเพิ่มตัวเองเป็นเพื่อน')
        return redirect('community:user_profile', username=username)
    
    # ตรวจสอบความสัมพันธ์ที่มีอยู่ทั้งสองทิศทาง
    existing = Friendship.objects.filter(
        Q(from_user=request.user, to_user=user) |
        Q(from_user=user, to_user=request.user)
    ).first()

    if existing:
        if existing.is_accepted:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'info', 'message': 'คุณเป็นเพื่อนกันอยู่แล้ว', 'is_friend': True})
            messages.info(request, 'คุณเป็นเพื่อนกันอยู่แล้ว')
        elif existing.to_user == request.user:
            existing.is_accepted = True
            existing.save()
            Notification.objects.create(
                user=user,
                notification_type='friend_accept',
                from_user=request.user
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': f'ตอบรับคำขอเป็นเพื่อนกับ {user.username} แล้ว', 'is_friend': True})
            messages.success(request, f'ตอบรับคำขอเป็นเพื่อนกับ {user.username} แล้ว')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'info', 'message': 'คุณได้ส่งคำขอเพิ่มเพื่อนไปแล้ว', 'is_pending': True})
            messages.info(request, 'คุณได้ส่งคำขอเพิ่มเพื่อนไปแล้ว')
        return redirect('community:user_profile', username=username)

    # สร้างคำขอใหม่
    Friendship.objects.create(from_user=request.user, to_user=user)
    Notification.objects.create(
        user=user,
        notification_type='friend_request',
        from_user=request.user
    )
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'ส่งคำขอเพิ่มเพื่อนแล้ว', 'is_pending': True})
    messages.success(request, 'ส่งคำขอเพิ่มเพื่อนแล้ว')
    return redirect('community:user_profile', username=username)


@login_required
def accept_friend(request, friendship_id):
    """ยอมรับคำขอเพิ่มเพื่อน"""
    friendship = get_object_or_404(Friendship, pk=friendship_id, to_user=request.user)
    friendship.is_accepted = True
    friendship.save()
    
    # สร้างการแจ้งเตือน
    Notification.objects.create(
        user=friendship.from_user,
        notification_type='friend_accept',
        from_user=request.user
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'status': 'success',
            'message': 'ยอมรับคำขอเพิ่มเพื่อนแล้ว',
            'friendship_id': friendship.id,
            'is_accepted': True,
            'friend_username': friendship.from_user.username
        })
    
    messages.success(request, 'ยอมรับคำขอเพิ่มเพื่อนแล้ว')
    return redirect(request.META.get('HTTP_REFERER', 'community:friends_list'))


@login_required
def reject_friend(request, friendship_id):
    """ปฏิเสธคำขอเพิ่มเพื่อน"""
    friendship = get_object_or_404(Friendship, pk=friendship_id, to_user=request.user)
    friend_username = friendship.from_user.username
    friendship.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'status': 'success',
            'message': 'ปฏิเสธคำขอแล้ว',
            'friend_username': friend_username
        })
    
    messages.success(request, 'ปฏิเสธคำขอแล้ว')
    return redirect(request.META.get('HTTP_REFERER', 'community:friends_list'))


@login_required
def remove_friend(request, username):
    """ลบเพื่อน"""
    user = get_object_or_404(User, username=username)
    Friendship.objects.filter(
        Q(from_user=request.user, to_user=user) |
        Q(from_user=user, to_user=request.user),
        is_accepted=True
    ).delete()
    messages.success(request, 'ลบเพื่อนแล้ว')
    return redirect('community:friends_list')
