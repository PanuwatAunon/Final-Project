from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse
from itertools import chain
from operator import attrgetter

from ..models import Game, Thread, GameGuide
from ..forms import ThreadForm
from .helpers import get_user_friend_ids


def home(request):
    """หน้าแรก (Main Feed)"""
    # 1. Games for sidebar/header — ordered by popularity (likes) - Top 10
    games = Game.objects.annotate(likes_count=Count('likes')).order_by('-likes_count')[:10]

    # 2. Feed Logic
    if request.user.is_authenticated:
        # User Logged In
        friend_ids = get_user_friend_ids(request.user)
        
        # Visibility Logic:
        # - Show own posts (all visibility)
        # - Show friends' posts (public OR friends)
        # - Show others' posts (public only)
        
        # Complex queries for Threads
        threads = Thread.objects.filter(
            Q(author=request.user) |  # Own posts
            (Q(author__id__in=friend_ids) & Q(visibility__in=['public', 'friends'])) |  # Friend posts
            (~Q(author=request.user) & ~Q(author__id__in=friend_ids) & Q(visibility='public'))  # Public posts
        ).select_related('author', 'game')

        # Complex queries for Guides
        guides = GameGuide.objects.filter(
            Q(author=request.user) |
            (Q(author__id__in=friend_ids) & Q(visibility__in=['public', 'friends'])) |
            (~Q(author=request.user) & ~Q(author__id__in=friend_ids) & Q(visibility='public'))
        ).select_related('author', 'game')

    else:
        # Guest User: Public only
        threads = Thread.objects.filter(visibility='public').select_related('author', 'game')
        guides = GameGuide.objects.filter(visibility='public').select_related('author', 'game')

    # Assign types and user reactions
    threads = list(threads)
    guides = list(guides)
    for t in threads:
        t.type = 'Thread'
        t.user_reaction = t.get_user_reaction(request.user) if request.user.is_authenticated else None
    for g in guides:
        g.type = 'Guide'
        g.user_reaction = g.get_user_reaction(request.user) if request.user.is_authenticated else None

    # Combined activity feed
    activities = sorted(
        chain(threads, guides),
        key=attrgetter('created_at'),
        reverse=True
    )
    
    # Form for Quick Post
    form = ThreadForm()
    
    context = {
        'activities': activities,
        'games': games,
        'form': form,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('poll') == '1':
        return render(request, 'community/includes/activity_feed_partial.html', context)

    return render(request, 'community/home.html', context)


def game_list(request):
    """รายการเกมทั้งหมด"""
    games = Game.objects.annotate(likes_count=Count('likes')).order_by('-likes_count')
    
    # ค้นหา
    query = request.GET.get('q')
    if query:
        games = games.filter(Q(name__icontains=query) | Q(genre__icontains=query))
    
    context = {'games': games, 'query': query}
    return render(request, 'community/game_list.html', context)


def game_detail(request, game_id):
    """รายละเอียดเกม"""
    game = get_object_or_404(Game, pk=game_id)
    
    if request.user.is_authenticated:
        friend_ids = get_user_friend_ids(request.user)
        threads = game.threads.filter(
            Q(author=request.user) |
            (Q(author__id__in=friend_ids) & Q(visibility__in=['public', 'friends'])) |
            (~Q(author=request.user) & ~Q(author__id__in=friend_ids) & Q(visibility='public'))
        ).select_related('author')
        
        guides = game.guides.filter(
            Q(author=request.user) |
            (Q(author__id__in=friend_ids) & Q(visibility__in=['public', 'friends'])) |
            (~Q(author=request.user) & ~Q(author__id__in=friend_ids) & Q(visibility='public'))
        )[:5]
    else:
        threads = game.threads.filter(visibility='public').select_related('author')
        guides = game.guides.filter(visibility='public')[:5]

    for g in guides:
        g.user_reaction = g.get_user_reaction(request.user) if request.user.is_authenticated else None

    groups = game.chat_groups.all()
    
    context = {
        'game': game,
        'threads': threads,
        'groups': groups,
        'guides': guides,
    }
    return render(request, 'community/game_detail.html', context)


@login_required
def like_game(request, game_id):
    """ไลค์/ยกเลิกไลค์เกม"""
    game = get_object_or_404(Game, pk=game_id)
    
    if request.user in game.likes.all():
        game.likes.remove(request.user)
        liked = False
    else:
        game.likes.add(request.user)
        liked = True
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': liked,
            'likes_count': game.likes.count()
        })
    
    return redirect(request.META.get('HTTP_REFERER', 'community:game_list'))

