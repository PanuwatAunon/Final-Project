from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from django.db.models import Q
from ..models import Game, GameGuide, GuideComment, Notification, GuideReaction, GuideCommentReaction, REACTION_EMOJIS
from ..forms import GameGuideForm, GuideCommentForm
from .helpers import get_user_friend_ids


@login_required
def like_guide(request, guide_id):
    """กดไลค์ไกด์ (Default reaction: like)"""
    return react_guide(request, guide_id)


@login_required
def react_guide(request, guide_id):
    """กดเลือกอารมณ์ไกด์ (like, laugh, sad, angry)"""
    guide = get_object_or_404(GameGuide, pk=guide_id)
    reaction_type = request.POST.get('reaction_type') or request.GET.get('reaction_type') or 'like'
    
    if reaction_type not in ['like', 'laugh', 'sad', 'angry']:
        reaction_type = 'like'

    existing = GuideReaction.objects.filter(guide=guide, user=request.user).first()
    
    if existing:
        if existing.reaction_type == reaction_type:
            # Clicked same reaction -> Remove reaction
            existing.delete()
            if guide.author != request.user:
                guide.author.profile.points = max(0, guide.author.profile.points - 1)
                guide.author.profile.save()
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
        GuideReaction.objects.create(guide=guide, user=request.user, reaction_type=reaction_type)
        current_user_reaction = reaction_type
        reacted = True
        
        # Notification & Points (+1 point only if not reacting to own guide)
        if guide.author != request.user:
            Notification.objects.create(
                user=guide.author,
                notification_type='like',
                from_user=request.user,
                guide=guide
            )
            guide.author.profile.points += 1
            guide.author.profile.save()

    counts = guide.get_reaction_counts()

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
def create_guide(request, game_id=None):
    """สร้างไกด์เกม - ต้องผูกกับเกมเสมอ (เข้าผ่านหน้าเกม)"""
    if not game_id:
        messages.info(request, 'กรุณาเลือกเกมที่คุณต้องการเขียนไกด์')
        return redirect('community:game_list')

    game = get_object_or_404(Game, pk=game_id)
    
    if request.method == 'POST':
        form = GameGuideForm(request.POST)
        if form.is_valid():
            guide = form.save(commit=False)
            guide.game = game
            guide.author = request.user
            guide.save()
            messages.success(request, f'สร้างไกด์สำหรับเกม "{game.name}" สำเร็จ')
            return redirect('community:guide_detail', guide_id=guide.id)
    else:
        form = GameGuideForm(initial={'game': game})
    
    context = {'form': form, 'game': game}
    return render(request, 'community/create_guide.html', context)


from django.db.models import F

def guide_detail(request, guide_id):
    """รายละเอียดไกด์"""
    guide = GameGuide.objects.filter(pk=guide_id).first()
    if not guide:
        messages.info(request, 'ไม่พบไกด์เกมที่ต้องการ หรือไกด์นี้ถูกลบออกไปแล้ว')
        return redirect('community:home')

    # Visibility Check
    if guide.visibility == 'private':
        if not request.user.is_authenticated or request.user != guide.author:
            messages.error(request, 'คุณไม่มีสิทธิ์เข้าดูไกด์นี้ (เป็นไกด์ส่วนตัว)')
            return redirect('community:home')
    elif guide.visibility == 'friends':
        if not request.user.is_authenticated:
            messages.error(request, 'กรุณาเข้าสู่ระบบเพื่อดูไกด์เฉพาะเพื่อน')
            return redirect('community:login')
        if request.user != guide.author:
            friend_ids = get_user_friend_ids(request.user)
            if guide.author.id not in friend_ids:
                messages.error(request, 'คุณไม่มีสิทธิ์เข้าดูไกด์นี้ (เฉพาะเพื่อนของผู้เขียนเท่านั้น)')
                return redirect('community:home')
    
    # เพิ่มจำนวนการเข้าชม (ป้องกันการปั๊มยอดวิวด้วย Session)
    session_key = f'viewed_guide_{guide_id}'
    if not request.session.get(session_key):
        GameGuide.objects.filter(pk=guide_id).update(views_count=F('views_count') + 1)
        request.session[session_key] = True
        guide.refresh_from_db()

    comments = guide.comments.all()
    comment_form = None
    
    if request.user.is_authenticated:
        if request.method == 'POST' and 'comment_content' in request.POST:
            comment_form = GuideCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.guide = guide
                comment.author = request.user
                comment.save()

                # ให้คะแนนเจ้าของไกด์เมื่อมีคนอื่นมาคอมเมนต์ (+1 แต้ม)
                if guide.author != request.user:
                    Notification.objects.create(
                        user=guide.author,
                        notification_type='reply',
                        from_user=request.user,
                        guide=guide
                    )
                    guide.author.profile.points += 1
                    guide.author.profile.save()

                messages.success(request, 'แสดงความคิดเห็นสำเร็จ')
                return redirect('community:guide_detail', guide_id=guide_id)
        else:
            comment_form = GuideCommentForm()
    
    comments = list(guide.comments.select_related('author').all())
    for c in comments:
        c.user_reaction = c.get_user_reaction(request.user) if request.user.is_authenticated else None

    guide.user_reaction = guide.get_user_reaction(request.user) if request.user.is_authenticated else None
    context = {
        'guide': guide,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'community/guide_detail.html', context)


@login_required
def edit_guide(request, guide_id):
    """แก้ไขไกด์ (เฉพาะผู้เขียนหรือสตาฟ)"""
    guide = GameGuide.objects.filter(pk=guide_id).first()
    if not guide:
        messages.info(request, 'ไม่พบไกด์เกมที่ต้องการ หรือไกด์นี้ถูกลบออกไปแล้ว')
        return redirect('community:home')

    if request.user != guide.author and not request.user.is_staff:
        messages.error(request, 'คุณไม่มีสิทธิเข้าแก้ไขไกด์นี้')
        return redirect('community:guide_detail', guide_id=guide_id)

    game = guide.game
    if request.method == 'POST':
        form = GameGuideForm(request.POST, instance=guide)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดตไกด์สำเร็จ')
            return redirect('community:guide_detail', guide_id=guide.id)
    else:
        form = GameGuideForm(instance=guide)

    context = {'form': form, 'game': game}
    return render(request, 'community/create_guide.html', context)


@login_required
def delete_guide(request, guide_id):
    """ลบไกด์"""
    guide = GameGuide.objects.filter(pk=guide_id).first()
    if not guide:
        messages.info(request, 'ไม่พบไกด์เกมที่ต้องการ หรือไกด์นี้ถูกลบออกไปแล้ว')
        return redirect('community:home')
    game = guide.game
    
    if request.user != guide.author and not request.user.is_staff:
        messages.error(request, 'คุณไม่มีสิทธิลบไกด์นี้')
        return redirect('community:guide_detail', guide_id=guide_id)
    
    guide.delete()
    messages.success(request, 'ลบไกด์สำเร็จ')
    if game:
        return redirect('community:game_detail', game_id=game.id)
    return redirect('community:home')


def game_guides(request, game_id):
    """ไกด์ของเกมเฉพาะ"""
    game = get_object_or_404(Game, pk=game_id)
    if request.user.is_authenticated:
        friend_ids = get_user_friend_ids(request.user)
        guides = game.guides.filter(
            Q(author=request.user) |
            (Q(author__id__in=friend_ids) & Q(visibility__in=['public', 'friends'])) |
            (~Q(author=request.user) & ~Q(author__id__in=friend_ids) & Q(visibility='public'))
        ).select_related('author').order_by('-created_at')
    else:
        guides = game.guides.filter(visibility='public').select_related('author').order_by('-created_at')
    
    context = {'game': game, 'guides': guides}
    return render(request, 'community/game_guides.html', context)


@login_required
@require_POST
def delete_guide_comment(request, comment_id):
    """ลบความเห็นในไกด์ (เฉพาะผู้เขียนหรือสตาฟ)"""
    comment = get_object_or_404(GuideComment, pk=comment_id)
    guide_id = comment.guide.id
    
    if request.user != comment.author and not request.user.is_staff:
        messages.error(request, 'คุณไม่มีสิทธิลบความเห็นนี้')
        return redirect('community:guide_detail', guide_id=guide_id)
    
    if comment.author != comment.guide.author:
        comment.guide.author.profile.points = max(0, comment.guide.author.profile.points - 1)
        comment.guide.author.profile.save()

    comment.delete()
    messages.success(request, 'ลบความเห็นสำเร็จ')
    return redirect('community:guide_detail', guide_id=guide_id)


@login_required
def like_guide_comment(request, comment_id):
    """กดไลค์ความเห็นในไกด์ (Default reaction: like)"""
    return react_guide_comment(request, comment_id)


@login_required
def react_guide_comment(request, comment_id):
    """กดเลือกอารมณ์ความเห็นในไกด์ (like, laugh, sad, angry)"""
    comment = get_object_or_404(GuideComment, pk=comment_id)
    reaction_type = request.POST.get('reaction_type') or request.GET.get('reaction_type') or 'like'

    if reaction_type not in ['like', 'laugh', 'sad', 'angry']:
        reaction_type = 'like'

    existing = GuideCommentReaction.objects.filter(comment=comment, user=request.user).first()

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
        GuideCommentReaction.objects.create(comment=comment, user=request.user, reaction_type=reaction_type)
        current_user_reaction = reaction_type
        reacted = True

        if comment.author != request.user:
            Notification.objects.create(
                user=comment.author,
                notification_type='like',
                from_user=request.user,
                guide=comment.guide
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


from django.urls import reverse

def get_guide_updates(request, guide_id):
    """API สำหรับตรวจสอบสถานะไกด์แบบ Real-time Polling (ทุกๆ 3 วิ)"""
    guide = GameGuide.objects.filter(pk=guide_id).first()
    if not guide:
        return JsonResponse({
            'deleted': True,
            'redirect_url': reverse('community:home'),
            'message': 'ไกด์นี้ถูกลบไปแล้ว'
        }, status=404)
        
    counts = guide.get_reaction_counts()
    return JsonResponse({
        'deleted': False,
        'likes': counts['total'],
        'comments_count': guide.comments.count()
    })
