from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from ..models import Thread, Game, Notification, ThreadReaction, REACTION_EMOJIS
from ..forms import ThreadForm, CommentForm
from .helpers import get_user_friend_ids




def thread_detail(request, thread_id):
    """รายละเอียดกระทู้"""
    thread = Thread.objects.filter(pk=thread_id).first()
    if not thread:
        messages.info(request, 'ไม่พบกระทู้ที่ต้องการ หรือกระทู้นี้ถูกลบออกไปแล้ว')
        return redirect('community:home')

    # Visibility Check
    if thread.visibility == 'private':
        if not request.user.is_authenticated or request.user != thread.author:
            messages.error(request, 'คุณไม่มีสิทธิ์เข้าดูโพสต์นี้ (เป็นโพสต์ส่วนตัว)')
            return redirect('community:home')
    elif thread.visibility == 'friends':
        if not request.user.is_authenticated:
            messages.error(request, 'กรุณาเข้าสู่ระบบเพื่อดูโพสต์เฉพาะเพื่อน')
            return redirect('community:login')
        if request.user != thread.author:
            friend_ids = get_user_friend_ids(request.user)
            if thread.author.id not in friend_ids:
                messages.error(request, 'คุณไม่มีสิทธิ์เข้าดูโพสต์นี้ (เฉพาะเพื่อนของผู้โพสต์เท่านั้น)')
                return redirect('community:home')


    thread.user_reaction = thread.get_user_reaction(request.user) if request.user.is_authenticated else None
    comments = list(thread.comments.select_related('author').all())
    for c in comments:
        c.user_reaction = c.get_user_reaction(request.user) if request.user.is_authenticated else None
    
    context = {
        'thread': thread,
        'comments': comments,
        'comment_form': CommentForm(),
    }
    return render(request, 'community/thread_detail.html', context)


@login_required
def create_thread(request, game_id=None):
    """สร้างกระทู้ (โพสต์จากหน้าหลัก)"""
    if request.method == 'POST':
        post_data = request.POST.copy()
        if not post_data.get('content') and post_data.get('title'):
            post_data['content'] = post_data.get('title')
        elif not post_data.get('title') and post_data.get('content'):
            post_data['title'] = post_data.get('content')[:250]
            
        form = ThreadForm(post_data, request.FILES)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.author = request.user
            thread.save()
            form.save_m2m()
            
            messages.success(request, 'สร้างกระทู้สำเร็จ')
            return redirect('community:home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
            return redirect('community:home')
    
    return redirect('community:home')


@login_required
def edit_thread(request, thread_id):
    """แก้ไขกระทู้"""
    thread = Thread.objects.filter(pk=thread_id).first()
    if not thread:
        messages.info(request, 'ไม่พบกระทู้ที่ต้องการ หรือกระทู้นี้ถูกลบออกไปแล้ว')
        return redirect('community:home')
    
    # Check permissions
    if request.user != thread.author and not request.user.is_staff:
        messages.error(request, 'คุณไม่มีสิทธิแก้ไขกระทู้นี้')
        return redirect('community:thread_detail', thread_id=thread.id)
    
    if request.method == 'POST':
        form = ThreadForm(request.POST, instance=thread)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขกระทู้สำเร็จ')
            return redirect('community:thread_detail', thread_id=thread.id)
    else:
        form = ThreadForm(instance=thread)
    
    context = {'form': form, 'thread': thread}
    return render(request, 'community/edit_thread.html', context)


@login_required
def like_thread(request, thread_id):
    """กดไลค์กระทู้ (Default reaction: like)"""
    return react_thread(request, thread_id)


@login_required
def react_thread(request, thread_id):
    """กดเลือกอารมณ์กระทู้ (like, laugh, sad, angry)"""
    thread = get_object_or_404(Thread, pk=thread_id)
    reaction_type = request.POST.get('reaction_type') or request.GET.get('reaction_type') or 'like'
    
    if reaction_type not in ['like', 'laugh', 'sad', 'angry']:
        reaction_type = 'like'

    existing = ThreadReaction.objects.filter(thread=thread, user=request.user).first()
    
    if existing:
        if existing.reaction_type == reaction_type:
            # Clicked same reaction -> Remove reaction
            existing.delete()
            if thread.author != request.user:
                thread.author.profile.points = max(0, thread.author.profile.points - 1)
                thread.author.profile.save()
            current_user_reaction = None
            reacted = False
        else:
            # Changed reaction type
            existing.reaction_type = reaction_type
            existing.save()
            current_user_reaction = reaction_type
            reacted = True
    else:
        # New reaction
        ThreadReaction.objects.create(thread=thread, user=request.user, reaction_type=reaction_type)
        current_user_reaction = reaction_type
        reacted = True
        
        # Notification & Points (only if not reacting to own thread)
        if thread.author != request.user:
            Notification.objects.create(
                user=thread.author,
                notification_type='like',
                from_user=request.user,
                thread=thread
            )
            thread.author.profile.points += 1
            thread.author.profile.save()

    counts = thread.get_reaction_counts()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'liked': reacted,
            'user_reaction': current_user_reaction,
            'likes': counts['total'],
            'counts': counts,
            'emoji': REACTION_EMOJIS.get(current_user_reaction, '') if current_user_reaction else ''
        })
    return redirect(request.META.get('HTTP_REFERER', 'community:home'))


@login_required
def delete_thread(request, thread_id):
    """ลบกระทู้"""
    thread = Thread.objects.filter(pk=thread_id).first()
    if not thread:
        messages.info(request, 'ไม่พบกระทู้ที่ต้องการ หรือกระทู้นี้ถูกลบออกไปแล้ว')
        return redirect('community:home')
    
    if request.user != thread.author and not request.user.is_staff:
        messages.error(request, 'คุณไม่มีสิทธิลบกระทู้นี้')
        return redirect('community:thread_detail', thread_id=thread_id)
    
    thread.delete()
    messages.success(request, 'ลบกระทู้สำเร็จ')
    return redirect('community:home')


from django.urls import reverse

def get_thread_updates(request, thread_id):
    """API สำหรับตรวจสอบสถานะกระทู้แบบ Real-time Polling (ทุกๆ 3 วิ)"""
    thread = Thread.objects.filter(pk=thread_id).first()
    if not thread:
        return JsonResponse({
            'deleted': True,
            'redirect_url': reverse('community:home'),
            'message': 'กระทู้นี้ถูกลบไปแล้ว'
        }, status=404)
        
    counts = thread.get_reaction_counts()
    return JsonResponse({
        'deleted': False,
        'likes': counts['total'],
        'comments_count': thread.comments.count()
    })
