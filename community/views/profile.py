from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

from ..models import Friendship
from ..forms import UserProfileForm, UserUpdateForm


def user_profile(request, username):
    """โปรไฟล์ผู้ใช้"""
    user = get_object_or_404(User, username=username)
    profile = user.profile
    
    # คำนวณอันดับตามคะแนน (ยกเว้นผู้ดูแลระบบ)
    rank = User.objects.exclude(is_staff=True).exclude(is_superuser=True).filter(profile__points__gt=profile.points).count() + 1
    
    is_friend = False
    is_pending = False
    has_incoming_request = False
    incoming_friendship_id = None
    
    if request.user.is_authenticated and request.user != user:
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

    # Visibility Filtering:
    # 1. Profile owner can see all their posts (public, friends, private)
    # 2. Friends can see public and friends-only posts
    # 3. Non-friends/Guests can only see public posts
    if request.user.is_authenticated and request.user == user:
        threads = user.threads.all()
        guides = user.guides.all()
    elif is_friend:
        threads = user.threads.filter(visibility__in=['public', 'friends'])
        guides = user.guides.filter(visibility__in=['public', 'friends'])
    else:
        threads = user.threads.filter(visibility='public')
        guides = user.guides.filter(visibility='public')
    
    context = {
        'user': user,
        'profile': profile,
        'threads': threads,
        'guides': guides,
        'rank': rank,
        'is_friend': is_friend,
        'is_pending': is_pending,
        'has_incoming_request': has_incoming_request,
        'incoming_friendship_id': incoming_friendship_id,
    }
    return render(request, 'community/user_profile.html', context)


@login_required
def edit_profile(request):
    """แก้ไขโปรไฟล์"""
    profile = request.user.profile
    
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserUpdateForm(request.POST, instance=request.user)
        
        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()
            user_form.save()
            messages.success(request, 'อัพเดตโปรไฟล์สำเร็จ')
            return redirect('community:user_profile', username=request.user.username)
    else:
        profile_form = UserProfileForm(instance=profile)
        user_form = UserUpdateForm(instance=request.user)
    
    context = {'profile_form': profile_form, 'user_form': user_form}
    return render(request, 'community/edit_profile.html', context)


def ranking(request):
    """อันดับผู้ใช้"""
    # Exclude admin users from ranking display
    users = User.objects.select_related('profile').exclude(is_staff=True).exclude(is_superuser=True).order_by('-profile__points')[:10]
    
    context = {'users': users}
    return render(request, 'community/ranking.html', context)
