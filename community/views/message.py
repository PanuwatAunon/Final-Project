from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.timesince import timesince

from ..models import DirectMessage, Notification, Friendship, GroupChat, GroupMessage


def check_are_friends(user1, user2):
    """ตรวจสอบว่าผู้ใช้สองคนเป็นเพื่อนกันหรือไม่ (หรือคนใดคนหนึ่งเป็น Staff/Superuser สำหรับติดต่อผู้ใช้)"""
    if user1.is_staff or user1.is_superuser or user2.is_staff or user2.is_superuser:
        return True
    return Friendship.objects.filter(
        (Q(from_user=user1, to_user=user2) | Q(from_user=user2, to_user=user1)),
        is_accepted=True
    ).exists()


@login_required
def get_new_messages(request, username):
    """API สำหรับดึงข้อความใหม่และสถานะการยกเลิกข้อความ (Polling)"""
    other_user = get_object_or_404(User, username=username)
    if not check_are_friends(request.user, other_user):
        return JsonResponse({'error': 'You must be friends to chat'}, status=403)

    last_id = request.GET.get('last_id')

    
    # Query conversation messages
    conv_qs = DirectMessage.objects.filter(
        (Q(from_user=request.user, to_user=other_user) | 
         Q(from_user=other_user, to_user=request.user))
    )

    deleted_ids = list(conv_qs.filter(is_deleted=True).values_list('id', flat=True))

    new_messages = conv_qs
    if last_id:
        new_messages = new_messages.filter(id__gt=last_id)
        
    new_messages = new_messages.select_related('from_user__profile').order_by('created_at')
    
    data = []
    for msg in new_messages:
        # Mark as read if from other user
        if msg.from_user == other_user and not msg.is_read:
            msg.is_read = True
            msg.save()
            
        data.append({
            'id': msg.id,
            'content': msg.content,
            'image_url': msg.image.url if msg.image else None,
            'video_url': msg.video.url if msg.video else None,
            'created_at': msg.created_at.strftime('%H:%M'),
            'is_me': msg.from_user == request.user,
            'is_deleted': msg.is_deleted,
            'sender_avatar': msg.from_user.profile.avatar.url if (hasattr(msg.from_user, 'profile') and msg.from_user.profile.avatar) else None
        })
        
    has_prof = hasattr(other_user, 'profile')
    return JsonResponse({
        'messages': data,
        'deleted_ids': deleted_ids,
        'is_online': other_user.profile.is_online if has_prof else False,
        'last_activity': timesince(other_user.profile.last_activity).split(',')[0] if (has_prof and other_user.profile.last_activity) else None
    })


@login_required
def inbox(request):
    """กล่องข้อความ"""
    # SQLite (and some other backends) don't support DISTINCT ON fields.
    # Query all messages involving the user ordered by newest first and
    # pick the first message per conversation partner in Python.
    qs = DirectMessage.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).select_related('from_user', 'to_user').order_by('-created_at')

    conversations = []
    seen_partner_ids = set()
    for msg in qs:
        # determine the conversation partner (the other user)
        partner = msg.to_user if msg.from_user == request.user else msg.from_user
        if partner.id in seen_partner_ids:
            continue
        seen_partner_ids.add(partner.id)
        conversations.append(msg)

    context = {'conversations': conversations}
    return render(request, 'community/inbox.html', context)


@login_required
def chat(request, username):
    """แชทกับผู้ใช้"""
    other_user = get_object_or_404(User, username=username)
    is_friend = check_are_friends(request.user, other_user)

    messages_list = DirectMessage.objects.filter(
        Q(from_user=request.user, to_user=other_user) |
        Q(from_user=other_user, to_user=request.user)
    ).order_by('created_at')

    # หากไม่ได้เป็นเพื่อนและไม่มีประวัติการคุยกันมาก่อน ให้บล็อกไม่ให้เริ่มแชทใหม่
    if not is_friend and not messages_list.exists():
        messages.warning(request, f'คุณต้องเป็นเพื่อนกับ {other_user.username} ก่อน จึงจะสามารถส่งข้อความได้')
        return redirect('community:user_profile', username=username)

    # ทำให้ข้อความอ่านแล้ว
    DirectMessage.objects.filter(from_user=other_user, to_user=request.user).update(is_read=True)

    context = {
        'other_user': other_user, 
        'chat_messages': messages_list,
        'is_friend': is_friend
    }
    return render(request, 'community/chat.html', context)


@login_required
@require_POST
def send_message(request):
    """ส่งข้อความโดยตรง"""
    # Support both direct messages and group messages.
    content = request.POST.get('content')
    group_id = request.POST.get('group_id')

    # If group_id is present, create a GroupMessage
    if group_id:
        try:
            group = GroupChat.objects.get(pk=group_id)
        except GroupChat.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'ไม่พบกลุ่มที่ต้องการส่งข้อความ'}, status=404)
            messages.error(request, 'ไม่พบกลุ่มที่ต้องการส่งข้อความ')
            return redirect(request.META.get('HTTP_REFERER', 'community:inbox'))

        # Check membership
        if request.user not in group.members.all():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'คุณไม่มีสิทธิส่งข้อความในกลุ่มนี้'}, status=403)
            messages.error(request, 'คุณไม่มีสิทธิส่งข้อความในกลุ่มนี้')
            return redirect('community:group_detail', group_id=group_id)

        image_file = request.FILES.get('image')
        video_file = request.FILES.get('video')
        if not content and not image_file and not video_file:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'กรุณากรอกข้อความหรือแนบไฟล์'}, status=400)
            return redirect('community:group_detail', group_id=group_id)

        msg = GroupMessage.objects.create(
            group=group,
            sender=request.user,
            content=content if content else '',
            image=image_file,
            video=video_file
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': {
                    'id': msg.id,
                    'sender_username': msg.sender.username,
                    'sender_avatar': msg.sender.profile.avatar.url if (hasattr(msg.sender, 'profile') and msg.sender.profile.avatar) else None,
                    'content': msg.content,
                    'image_url': msg.image.url if msg.image else None,
                    'video_url': msg.video.url if msg.video else None,
                    'created_at': msg.created_at.strftime('%d %b %H:%M'),
                    'is_me': True,
                    'is_deleted': False,
                    'can_delete': True
                }
            })

        # Optionally create notifications for group members (skipped for now)
        messages.success(request, 'ส่งข้อความในกลุ่มเรียบร้อยแล้ว')
        return redirect('community:group_detail', group_id=group_id)

    # Otherwise handle direct message
    to_username = request.POST.get('to_user')
    # Validate recipient
    if not to_username:
        messages.error(request, 'ไม่พบผู้รับข้อความ กรุณาลองอีกครั้ง')
        return redirect(request.META.get('HTTP_REFERER', 'community:inbox'))

    try:
        to_user = User.objects.get(username=to_username)
    except User.DoesNotExist:
        messages.error(request, f'ไม่พบผู้ใช้: {to_username}')
        return redirect(request.META.get('HTTP_REFERER', 'community:inbox'))

    if not check_are_friends(request.user, to_user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': f'คุณต้องเป็นเพื่อนกับ {to_user.username} ก่อนจึงจะสามารถส่งข้อความได้'}, status=403)
        messages.warning(request, f'คุณต้องเป็นเพื่อนกับ {to_user.username} ก่อน จึงจะสามารถส่งข้อความได้')
        return redirect('community:user_profile', username=to_username)

    DirectMessage.objects.create(
        from_user=request.user,
        to_user=to_user,
        content=content if content else '',
        image=request.FILES.get('image'),
        video=request.FILES.get('video')
    )

    return redirect('community:chat', username=to_username)


@login_required
def delete_message(request, message_id):
    """ยกเลิกข้อความแชท (Unsend / Soft Delete)"""
    msg = get_object_or_404(DirectMessage, pk=message_id)
    if msg.from_user == request.user:
        msg.is_deleted = True
        msg.image = None
        msg.video = None
        msg.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
            return JsonResponse({'status': 'success', 'message_id': message_id, 'is_deleted': True})
        messages.success(request, 'ยกเลิกข้อความเรียบร้อยแล้ว')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
            return JsonResponse({'status': 'error', 'message': 'คุณสามารถยกเลิกได้เฉพาะข้อความที่คุณเป็นผู้ส่งเท่านั้น'}, status=403)
        messages.error(request, 'คุณสามารถยกเลิกได้เฉพาะข้อความที่คุณเป็นผู้ส่งเท่านั้น')

    return redirect(request.META.get('HTTP_REFERER', 'community:inbox'))


@login_required
def delete_conversation(request, username):
    """ลบการสนทนาทั้งหมดกับผู้ใช้คนหนึ่ง"""
    other_user = get_object_or_404(User, username=username)
    deleted_count, _ = DirectMessage.objects.filter(
        (Q(from_user=request.user, to_user=other_user) | Q(from_user=other_user, to_user=request.user))
    ).delete()
    
    messages.success(request, f'ลบประวัติการสนทนากับ {other_user.username} เรียบร้อยแล้ว')
    return redirect('community:inbox')
