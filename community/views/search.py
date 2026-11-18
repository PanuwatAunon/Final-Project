from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Q

from ..models import Game, Thread
from .helpers import get_user_friend_ids


def search(request):
    """ค้นหาผู้ใช้ หรือเกม"""
    query = request.GET.get('q', '')
    users = User.objects.none()
    games = Game.objects.none()
    threads = Thread.objects.none()
    
    if query:
        users = User.objects.filter(username__icontains=query)
        games = Game.objects.filter(Q(name__icontains=query) | Q(genre__icontains=query))
        threads_qs = Thread.objects.filter(Q(title__icontains=query) | Q(content__icontains=query))
        
        if request.user.is_authenticated:
            friend_ids = get_user_friend_ids(request.user)
            threads = threads_qs.filter(
                Q(author=request.user) |
                (Q(author__id__in=friend_ids) & Q(visibility__in=['public', 'friends'])) |
                (~Q(author=request.user) & ~Q(author__id__in=friend_ids) & Q(visibility='public'))
            )
        else:
            threads = threads_qs.filter(visibility='public')
    
    context = {
        'query': query,
        'users': users,
        'games': games,
        'threads': threads,
    }
    return render(request, 'community/search.html', context)


def search_users(request):
    """ค้นหาผู้ใช้โดยเฉพาะ"""
    query = request.GET.get('q', '')
    users = User.objects.none()
    
    if query:
        users = User.objects.filter(username__icontains=query).select_related('profile')
    
    context = {
        'query': query,
        'users': users,
    }
    return render(request, 'community/search_users.html', context)
