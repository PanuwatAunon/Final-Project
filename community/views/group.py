from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.urls import reverse

from ..models import Game, GroupChat, GroupMessage
from ..forms import GroupChatForm


@login_required
def group_chat_home(request):
    """เข้ากลุ่มแชทผ่านหน้ารวมเกมเสมอ"""
    return redirect('community:game_list')


@login_required
def create_group(request, game_id=None):
    """สร้างกลุ่มคุย - ต้องผูกกับเกมเสมอ (เข้าผ่านหน้าเกม)"""
    if not game_id:
        messages.info(request, 'กรุณาเลือกเกมที่คุณต้องการสร้างกลุ่มพูดคุย')
        return redirect('community:game_list')

    game = get_object_or_404(Game, pk=game_id)
    
    if request.method == 'POST':
        form = GroupChatForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.game = game
            group.creator = request.user
            group.save()
            group.members.add(request.user)
            messages.success(request, f'สร้างกลุ่มสำหรับเกม "{game.name}" สำเร็จ')
            return redirect('community:group_detail', group_id=group.id)
    else:
        form = GroupChatForm(initial={'game': game})
    
    context = {'form': form, 'game': game}
    return render(request, 'community/create_group.html', context)


def group_detail(request, group_id):
    """รายละเอียดกลุ่ม"""
    group = GroupChat.objects.filter(pk=group_id).first()
    if not group:
        messages.info(request, 'ไม่พบกลุ่มที่ต้องการ หรือกลุ่มถูกลบออกไปแล้ว')
        return redirect('community:game_list')

    total_count = group.messages.count()
    if total_count > 50:
        messages_list = list(group.messages.select_related('sender__profile').order_by('-created_at')[:50])
        messages_list.reverse()
    else:
        messages_list = list(group.messages.select_related('sender__profile').order_by('created_at'))

    is_member = request.user in group.members.all() if request.user.is_authenticated else False
    last_message_id = messages_list[-1].id if messages_list else 0
    
    context = {
        'group': group,
        'chat_messages': messages_list,
        'is_member': is_member,
        'last_message_id': last_message_id,
        'total_messages_count': total_count,
    }
    return render(request, 'community/group_detail.html', context)


@login_required
@require_POST
def delete_group_message(request, group_id, message_id):
    """ยกเลิกข้อความในกลุ่ม (Unsend / Soft Delete)"""
    group = get_object_or_404(GroupChat, pk=group_id)
    message = get_object_or_404(GroupMessage, pk=message_id, group=group)

    # Only the sender or staff can delete a group message
    if request.user != message.sender and not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
            return JsonResponse({'status': 'error', 'message': 'คุณไม่มีสิทธิยกเลิกข้อความนี้'}, status=403)
        messages.error(request, 'คุณไม่มีสิทธิลบข้อความนี้')
        return redirect('community:group_detail', group_id=group_id)

    message.is_deleted = True
    if message.image:
        try:
            message.image.delete(save=False)
        except Exception:
            pass
        message.image = None
    if message.video:
        try:
            message.video.delete(save=False)
        except Exception:
            pass
        message.video = None
    message.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
        return JsonResponse({'status': 'success', 'message_id': message_id, 'is_deleted': True})

    messages.success(request, 'ยกเลิกข้อความในกลุ่มเรียบร้อยแล้ว')
    return redirect('community:group_detail', group_id=group_id)


@login_required
def join_group(request, group_id):
    """เข้าร่วมกลุ่ม"""
    group = get_object_or_404(GroupChat, pk=group_id)
    group.members.add(request.user)
    messages.success(request, 'เข้าร่วมกลุ่มสำเร็จ')
    return redirect('community:group_detail', group_id=group_id)


@login_required
def leave_group(request, group_id):
    """ออกจากกลุ่ม"""
    group = GroupChat.objects.filter(pk=group_id).first()
    if not group:
        messages.info(request, 'ไม่พบกลุ่ม หรือกลุ่มถูกลบไปแล้ว')
        return redirect('community:game_list')

    group.members.remove(request.user)
    messages.success(request, 'ออกจากกลุ่มสำเร็จ')
    if group.game:
        return redirect('community:game_detail', game_id=group.game.id)
    return redirect('community:game_list')


@login_required
def delete_group(request, group_id):
    """ลบกลุ่มที่สร้างโดยผู้สร้างหรือผู้ดูแลระบบ"""
    group = GroupChat.objects.filter(pk=group_id).first()
    if not group:
        messages.info(request, 'ไม่พบกลุ่ม หรือกลุ่มถูกลบไปแล้ว')
        return redirect('community:game_list')

    # Only the creator or staff may delete the group
    if request.user != group.creator and not request.user.is_staff:
        messages.error(request, 'คุณไม่มีสิทธิลบกลุ่มนี้')
        return redirect('community:group_detail', group_id=group_id)

    game_id = group.game.id if group.game else None
    group.delete()
    messages.success(request, 'ลบกลุ่มเรียบร้อยแล้ว')
    if game_id:
        return redirect('community:game_detail', game_id=game_id)
    return redirect('community:game_list')


@login_required
def get_group_messages(request, group_id):
    """API สำหรับดึงข้อความใหม่ในกลุ่มแชทแบบ Polling (ทุกๆ 3 วิ)"""
    group = GroupChat.objects.filter(pk=group_id).first()
    if not group:
        return JsonResponse({
            'error': 'กลุ่มนี้ถูกลบไปแล้ว',
            'redirect_url': reverse('community:game_list')
        }, status=404)

    if request.user not in group.members.all():
        return JsonResponse({'error': 'คุณไม่ได้เป็นสมาชิกในกลุ่มนี้'}, status=403)

    last_id = request.GET.get('last_id')
    messages_qs = group.messages.select_related('sender__profile')
    
    deleted_ids = list(group.messages.filter(is_deleted=True).values_list('id', flat=True))

    if last_id:
        try:
            last_id_int = int(last_id)
            messages_qs = messages_qs.filter(id__gt=last_id_int)
        except ValueError:
            pass
        
    messages_list = messages_qs.order_by('created_at')[:50]
    
    data = []
    for msg in messages_list:
        data.append({
            'id': msg.id,
            'sender_username': msg.sender.username,
            'sender_avatar': msg.sender.profile.avatar.url if (hasattr(msg.sender, 'profile') and msg.sender.profile.avatar) else None,
            'content': msg.content,
            'image_url': msg.image.url if msg.image else None,
            'video_url': msg.video.url if msg.video else None,
            'created_at': msg.created_at.strftime('%d %b %H:%M'),
            'is_me': msg.sender == request.user,
            'is_deleted': msg.is_deleted,
            'can_delete': msg.sender == request.user or request.user.is_staff
        })
        
    return JsonResponse({
        'messages': data,
        'deleted_ids': deleted_ids,
        'member_count': group.members.count(),
        'total_messages': group.messages.count()
    })
