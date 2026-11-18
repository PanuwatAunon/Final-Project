from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from ..models import Thread, Comment, GameGuide, Report
from ..forms import ReportForm


@login_required
def create_report(request):
    """สร้างการรายงาน"""
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.save()
            messages.success(request, 'ส่งรายงานแล้ว')
            return redirect('community:home')
    else:
        form = ReportForm()
    
    context = {
        'form': form, 
        'title': 'รายงานปัญหาทั่วไป',
        'description': 'แจ้งปัญหาเกี่ยวกับการใช้งาน สแปม หรือข้อผิดพลาดอื่นๆ'
    }
    return render(request, 'community/report_form.html', context)


@login_required
def report_thread(request, thread_id):
    """รายงานกระทู้"""
    thread = get_object_or_404(Thread, pk=thread_id)
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.thread = thread
            report.reported_user = thread.author
            report.save()
            messages.success(request, 'ส่งรายงานแล้ว')
            return redirect('community:thread_detail', thread_id=thread_id)
    else:
        form = ReportForm()
    
    context = {
        'form': form, 
        'thread': thread,
        'title': f'รายงานกระทู้: {thread.title}',
        'description': 'หากเนื้อหาในกระทู้นี้ละเมิดกฎชุมชน โปรดแจ้งให้เราทราบ'
    }
    return render(request, 'community/report_form.html', context)


@login_required
def report_guide(request, guide_id):
    """รายงานไกด์"""
    guide = get_object_or_404(GameGuide, pk=guide_id)
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.guide = guide
            report.reported_user = guide.author
            report.save()
            messages.success(request, 'ส่งรายงานแล้ว')
            return redirect('community:guide_detail', guide_id=guide_id)
    else:
        form = ReportForm()
    
    context = {
        'form': form, 
        'guide': guide,
        'title': f'รายงานไกด์: {guide.title}',
        'description': 'หากเนื้อหาในไกด์นี้ละเมิดกฎชุมชน โปรดแจ้งให้เราทราบ'
    }
    return render(request, 'community/report_form.html', context)


@login_required
def report_comment(request, comment_id):
    """รายงานความเห็น"""
    comment = get_object_or_404(Comment, pk=comment_id)
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.comment = comment
            report.reported_user = comment.author
            report.save()
            messages.success(request, 'ส่งรายงานแล้ว')
            return redirect('community:thread_detail', thread_id=comment.thread.id)
    else:
        form = ReportForm()
    
    context = {
        'form': form, 
        'comment': comment,
        'title': 'รายงานความคิดเห็น',
        'description': 'รายงานความคิดเห็นที่ไม่เหมาะสม'
    }
    return render(request, 'community/report_form.html', context)


@login_required
def report_user(request, username):
    """รายงานผู้ใช้"""
    user = get_object_or_404(User, username=username)
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = user
            report.save()
            messages.success(request, 'ส่งรายงานแล้ว')
            return redirect('community:user_profile', username=username)
    else:
        form = ReportForm()
    
    context = {
        'form': form, 
        'reported_user': user,
        'title': f'รายงานผู้ใช้: {user.username}',
        'description': 'หากผู้ใช้นี้มีพฤติกรรมไม่เหมาะสม โปรดแจ้งให้เราทราบ'
    }
    return render(request, 'community/report_form.html', context)
