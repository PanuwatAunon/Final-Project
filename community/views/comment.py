from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from ..models import Thread, Comment, Notification, CommentReaction, REACTION_EMOJIS
from ..forms import CommentForm


@login_required
def add_comment(request, thread_id):
    """เพิ่มความเห็น"""
    thread = get_object_or_404(Thread, pk=thread_id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.thread = thread
            comment.author = request.user
            comment.save()
            
            # สร้างการแจ้งเตือน & ให้คะแนนเจ้าของกระทู้เมื่อมีคนมาคอมเมนต์ (+1 แต้ม)
            if thread.author != request.user:
                Notification.objects.create(
                    user=thread.author,
                    notification_type='reply',
                    from_user=request.user,
                    comment=comment
                )
                thread.author.profile.points += 1
                thread.author.profile.save()
            
            messages.success(request, 'เพิ่มความเห็นสำเร็จ')
            return redirect('community:thread_detail', thread_id=thread_id)
    
    return redirect('community:thread_detail', thread_id=thread_id)


@login_required
def like_comment(request, comment_id):
    """กดไลค์ความเห็น (Default reaction: like)"""
    return react_comment(request, comment_id)


@login_required
def react_comment(request, comment_id):
    """กดเลือกอารมณ์ความเห็นกระทู้ (like, laugh, sad, angry)"""
    comment = get_object_or_404(Comment, pk=comment_id)
    reaction_type = request.POST.get('reaction_type') or request.GET.get('reaction_type') or 'like'

    if reaction_type not in ['like', 'laugh', 'sad', 'angry']:
        reaction_type = 'like'

    existing = CommentReaction.objects.filter(comment=comment, user=request.user).first()

    if existing:
        if existing.reaction_type == reaction_type:
            existing.delete()
            if comment.author != request.user:
                comment.author.profile.points = max(0, comment.author.profile.points - 1)
                comment.author.profile.save()
            current_user_reaction = None
            reacted = False
        else:
            existing.reaction_type = reaction_type
            existing.save()
            current_user_reaction = reaction_type
            reacted = True
    else:
        CommentReaction.objects.create(comment=comment, user=request.user, reaction_type=reaction_type)
        current_user_reaction = reaction_type
        reacted = True

        if comment.author != request.user:
            Notification.objects.create(
                user=comment.author,
                notification_type='like',
                from_user=request.user,
                comment=comment
            )
            comment.author.profile.points += 1
            comment.author.profile.save()

    counts = comment.get_reaction_counts()

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
def delete_comment(request, comment_id):
    """ลบความเห็น"""
    comment = get_object_or_404(Comment, pk=comment_id)
    thread_id = comment.thread.id
    
    if request.user != comment.author and not request.user.is_staff:
        messages.error(request, 'คุณไม่มีสิทธิลบความเห็นนี้')
        return redirect('community:thread_detail', thread_id=thread_id)
    
    if comment.author != comment.thread.author:
        comment.thread.author.profile.points = max(0, comment.thread.author.profile.points - 1)
        comment.thread.author.profile.save()

    comment.delete()
    messages.success(request, 'ลบความเห็นสำเร็จ')
    return redirect('community:thread_detail', thread_id=thread_id)
