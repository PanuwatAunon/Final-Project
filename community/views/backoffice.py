from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator

from ..models import (
    Game, UserProfile, Thread, Comment, GameGuide, 
    GuideComment, GroupChat, Report, UserBan, UserWarning, Notification
)
from ..forms import GameForm


def staff_required(view_func):
    """Decorator ตรวจสอบว่าผู้ใช้ล็อกอินและเป็น Staff หรือ Superuser หรือไม่"""
    def check_staff(user):
        return user.is_authenticated and (user.is_staff or user.is_superuser)
    
    actual_decorator = user_passes_test(
        check_staff,
        login_url='community:login',
    )
    return actual_decorator(view_func)


@login_required
@staff_required
def backoffice_dashboard(request):
    """
    หน้าควบคุมศูนย์หลังบ้านสำหรับ Staff / Admin
    """
    active_tab = request.GET.get('tab', 'overview')
    
    # 1. Overview Metrics
    if request.user.is_superuser:
        total_users = User.objects.count()
    else:
        total_users = User.objects.exclude(is_superuser=True).count()

    total_threads = Thread.objects.count()
    total_comments = Comment.objects.count()
    total_guides = GameGuide.objects.count()
    total_games = Game.objects.count()
    total_groups = GroupChat.objects.count()
    pending_reports_count = Report.objects.filter(status='pending').count()
    banned_users_count = UserBan.objects.count()

    # 2. Users Management
    q_user = request.GET.get('q_user', '').strip()
    user_filter = request.GET.get('user_filter', 'all')
    users_qs = User.objects.select_related('profile', 'ban').prefetch_related('warnings').order_by('-date_joined')
    
    # ซ่อนบัญชีที่มีอำนาจสูงกว่า: บัญชี Staff ทั่วไปจะไม่สามารถมองเห็นบัญชี Superuser ได้
    if not request.user.is_superuser:
        users_qs = users_qs.exclude(is_superuser=True)

    if q_user:
        users_qs = users_qs.filter(Q(username__icontains=q_user) | Q(email__icontains=q_user))
    
    if user_filter == 'banned':
        users_qs = users_qs.filter(ban__isnull=False)
    elif user_filter == 'staff':
        users_qs = users_qs.filter(is_staff=True)
    elif user_filter == 'active':
        users_qs = users_qs.filter(ban__isnull=True)
        
    paginator_users = Paginator(users_qs, 25)
    page_user = request.GET.get('page_user', 1)
    users_page = paginator_users.get_page(page_user)

    # 3. Reports Moderation
    report_status = request.GET.get('report_status', 'pending')
    reports_qs = Report.objects.select_related(
        'reporter', 'reported_user', 'thread', 'comment', 'guide'
    ).order_by('-created_at')
    
    # ไม่ให้ Staff เห็นรายงานที่เกี่ยวกับ Superuser
    if not request.user.is_superuser:
        reports_qs = reports_qs.exclude(reported_user__is_superuser=True)

    if report_status != 'all':
        reports_qs = reports_qs.filter(status=report_status)
        
    paginator_reports = Paginator(reports_qs, 20)
    page_report = request.GET.get('page_report', 1)
    reports_page = paginator_reports.get_page(page_report)

    # 4. Games Management
    q_game = request.GET.get('q_game', '').strip()
    games_qs = Game.objects.annotate(
        threads_count=Count('threads', distinct=True),
        guides_count=Count('guides', distinct=True),
        likes_count=Count('likes', distinct=True)
    ).order_by('name')
    
    if q_game:
        games_qs = games_qs.filter(Q(name__icontains=q_game) | Q(genre__icontains=q_game))
        
    # Forms
    game_form = GameForm()

    context = {
        'active_tab': active_tab,
        'total_users': total_users,
        'total_threads': total_threads,
        'total_comments': total_comments,
        'total_guides': total_guides,
        'total_games': total_games,
        'total_groups': total_groups,
        'pending_reports_count': pending_reports_count,
        'banned_users_count': banned_users_count,
        
        # Lists
        'users_page': users_page,
        'q_user': q_user,
        'user_filter': user_filter,
        
        'reports_page': reports_page,
        'report_status': report_status,
        
        'games': games_qs,
        'q_game': q_game,
        'game_form': game_form,
    }
    return render(request, 'community/backoffice/dashboard.html', context)


@login_required
@staff_required
def backoffice_user_action(request, user_id):
    """
    ดำเนินการกับสมาชิก (ปรับคะแนน, ออกใบเตือน, แบน, ปลดแบน, สลับ Staff, รีเซ็ตรหัสผ่าน)
    """
    if request.method != 'POST':
        return redirect('community:backoffice_dashboard')
        
    target_user = get_object_or_404(User, pk=user_id)
    action = request.POST.get('action')

    # ป้องกันการกระทำกับ Superuser ถ้าคนทำไม่ใช่ Superuser
    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'คุณไม่มีสิทธิ์ดำเนินการกับบัญชีผู้ดูแลระบบสูงสุด (Superuser)')
        return redirect(f"{redirect('community:backoffice_dashboard').url}?tab=users")

    if action == 'adjust_points':
        try:
            delta = int(request.POST.get('delta', 0))
            reason = request.POST.get('reason', '').strip()
            profile = target_user.profile
            profile.points = max(0, profile.points + delta)
            profile.save()
            
            # แจ้งเตือนผู้ใช้
            Notification.objects.create(
                user=target_user,
                notification_type='warning',
                from_user=request.user,
                warning=None
            )
            messages.success(request, f'ปรับคะแนนให้ {target_user.username} {delta:+d} แต้มสำเร็จ (คะแนนปัจจุบัน: {profile.points}) {f"เหตุผล: {reason}" if reason else ""}')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาดในการปรับคะแนน: {e}')

    elif action == 'issue_warning':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'กรุณาระบุเหตุผลในการออกใบเตือน')
        else:
            UserWarning.objects.create(
                user=target_user,
                reason=reason,
                created_by=request.user
            )
            messages.success(request, f'ออกใบเตือนให้กับ {target_user.username} เรียบร้อยแล้ว (ระบบส่งแจ้งเตือนและข้อความส่วนตัวให้อัตโนมัติ)')

    elif action == 'ban_user':
        duration = request.POST.get('duration', 'permanent')
        reason = request.POST.get('reason', 'ละเมิดกฎชุมชน').strip() or 'ละเมิดกฎชุมชน'
        
        banned_until = None
        duration_label = "ถาวร"
        if duration == '1d':
            banned_until = timezone.now() + timedelta(days=1)
            duration_label = "1 วัน"
        elif duration == '3d':
            banned_until = timezone.now() + timedelta(days=3)
            duration_label = "3 วัน"
        elif duration == '7d':
            banned_until = timezone.now() + timedelta(days=7)
            duration_label = "7 วัน"
        elif duration == '30d':
            banned_until = timezone.now() + timedelta(days=30)
            duration_label = "30 วัน"

        ban, _ = UserBan.objects.get_or_create(user=target_user)
        ban.reason = reason
        ban.banned_until = banned_until
        ban.save()
        messages.warning(request, f'ระงับการใช้งานบัญชี {target_user.username} เรียบร้อยแล้ว (ระยะเวลา: {duration_label})')

    elif action == 'unban_user':
        if hasattr(target_user, 'ban'):
            target_user.ban.delete()
            messages.success(request, f'ปลดแบนผู้ใช้ {target_user.username} เรียบร้อยแล้ว สมาชิกสามารถใช้งานระบบได้ตามปกติ')
        else:
            messages.info(request, f'ผู้ใช้ {target_user.username} ไม่ได้ถูกระงับการใช้งาน')

    elif action == 'toggle_staff':
        if target_user == request.user:
            messages.error(request, 'คุณไม่สามารถเปลี่ยนสถานะ Staff ของตนเองได้')
        else:
            target_user.is_staff = not target_user.is_staff
            target_user.save()
            status_text = "แต่งตั้งเป็น Staff" if target_user.is_staff else "ถอดถอนสถานะ Staff"
            messages.success(request, f'{status_text} ของ {target_user.username} เรียบร้อยแล้ว')

    elif action == 'reset_password':
        new_password = request.POST.get('new_password', '').strip()
        if len(new_password) < 6:
            messages.error(request, 'รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 6 ตัวอักษร')
        else:
            target_user.set_password(new_password)
            target_user.save()
            messages.success(request, f'รีเซ็ตรหัสผ่านใหม่สำหรับ {target_user.username} เรียบร้อยแล้ว')

    return redirect(f"{redirect('community:backoffice_dashboard').url}?tab=users&q_user={target_user.username}")


@login_required
@staff_required
def backoffice_report_action(request, report_id):
    """
    ดำเนินการกับรายงานปัญหา 1-Click:
    - approve_delete: อนุมัติ + ลบเนื้อหาที่ถูกรายงาน
    - approve_ban: อนุมัติ + ลบเนื้อหา + แบนผู้ใช้
    - reject: ปฏิเสธรายงาน
    """
    if request.method != 'POST':
        return redirect('community:backoffice_dashboard')
        
    report = get_object_or_404(Report, pk=report_id)
    action = request.POST.get('action')
    admin_notes = request.POST.get('admin_notes', '').strip()

    if action in ['approve_delete', 'approve_ban', 'approve_warn']:
        report.status = 'approved'
        report.resolved_at = timezone.now()
        action_desc = ""

        # ลบเนื้อหาที่ถูกรายงาน (เฉพาะกรณีสั่งลบเนื้อหา หรือสั่งแบนผู้ใช้ - ไม่ลบเมื่อตักเตือน)
        if action in ['approve_delete', 'approve_ban']:
            if report.comment:
                action_desc = f"ลบความคิดเห็น '{report.comment.content[:25]}...'"
                target_comment = report.comment
                report.comment = None
                target_comment.delete()
            elif report.thread:
                action_desc = f"ลบกระทู้ '{report.thread.title}'"
                target_thread = report.thread
                report.thread = None
                target_thread.delete()
            elif report.guide:
                action_desc = f"ลบไกด์ '{report.guide.title}'"
                target_guide = report.guide
                report.guide = None
                target_guide.delete()

        # ถ้าเลือกแบนผู้ใช้ด้วย (รองรับแบบกำหนดวัน หรือถาวร)
        if action == 'approve_ban' and report.reported_user:
            if not report.reported_user.is_staff and not report.reported_user.is_superuser:
                duration = request.POST.get('duration', 'permanent')
                custom_reason = request.POST.get('reason', '').strip()
                ban_reason = custom_reason or f"ระงับการใช้งานเนื่องจากถูกรายงานข้อหา: {report.get_report_type_display()} ({report.description})"

                banned_until = None
                duration_label = "ถาวร"
                if duration == '1d':
                    banned_until = timezone.now() + timedelta(days=1)
                    duration_label = "1 วัน"
                elif duration == '3d':
                    banned_until = timezone.now() + timedelta(days=3)
                    duration_label = "3 วัน"
                elif duration == '7d':
                    banned_until = timezone.now() + timedelta(days=7)
                    duration_label = "7 วัน"
                elif duration == '30d':
                    banned_until = timezone.now() + timedelta(days=30)
                    duration_label = "30 วัน"

                ban, _ = UserBan.objects.get_or_create(user=report.reported_user)
                ban.reason = ban_reason
                ban.banned_until = banned_until
                ban.save()
                if action_desc:
                    action_desc += f" และระงับการใช้งานบัญชี {report.reported_user.username} ({duration_label})"
                else:
                    action_desc = f"ระงับการใช้งานบัญชี {report.reported_user.username} ({duration_label})"

        # ถ้าเป็นการตักเตือนผู้ใช้ (ส่งหนังสือเตือน)
        elif action == 'approve_warn' and report.reported_user:
            warn_reason = f"คุณถูกตักเตือนเนื่องจากรายงานข้อหา '{report.get_report_type_display()}': {report.description}"
            UserWarning.objects.create(
                user=report.reported_user,
                reason=warn_reason,
                created_by=request.user
            )
            action_desc = f"ส่งหนังสือตักเตือนไปยัง {report.reported_user.username} (ข้อหา: {report.get_report_type_display()})"

        if not action_desc:
            action_desc = "อนุมัติรับทราบรายงานเรียบร้อยแล้ว"

        report.admin_notes = admin_notes or f"อนุมัติรายงานเรียบร้อยแล้ว ({action_desc})"
        report.save()
        messages.success(request, f'ดำเนินการอนุมัติรายงาน #{report.id} สำเร็จ: {action_desc}')

    elif action == 'reject':
        report.status = 'rejected'
        report.resolved_at = timezone.now()
        report.admin_notes = admin_notes or "ปฏิเสธรายงาน ไม่พบการละเมิดกฎชุมชน"
        report.save()
        messages.info(request, f'ปฏิเสธรายงาน #{report.id} เรียบร้อยแล้ว')

    return redirect(f"{redirect('community:backoffice_dashboard').url}?tab=reports")


@login_required
@staff_required
def backoffice_game_create(request):
    """เพิ่มเกมใหม่ผ่านฟอร์มหน้าเว็บ"""
    if request.method == 'POST':
        form = GameForm(request.POST, request.FILES)
        if form.is_valid():
            game = form.save()
            messages.success(request, f'เพิ่มเกม "{game.name}" เข้าสู่ระบบเรียบร้อยแล้ว')
        else:
            for field, err in form.errors.items():
                messages.error(request, f'ข้อมูลไม่ถูกต้อง ({field}): {err[0]}')
    return redirect(f"{redirect('community:backoffice_dashboard').url}?tab=games")


@login_required
@staff_required
def backoffice_game_edit(request, game_id):
    """แก้ไขข้อมูลเกม"""
    game = get_object_or_404(Game, pk=game_id)
    if request.method == 'POST':
        form = GameForm(request.POST, request.FILES, instance=game)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขข้อมูลเกม "{game.name}" เรียบร้อยแล้ว')
        else:
            messages.error(request, 'เกิดข้อผิดพลาดในการแก้ไขข้อมูลเกม')
    return redirect(f"{redirect('community:backoffice_dashboard').url}?tab=games")


@login_required
@staff_required
def backoffice_game_delete(request, game_id):
    """ลบเกมออกจากระบบ"""
    if request.method == 'POST':
        game = get_object_or_404(Game, pk=game_id)
        game_name = game.name
        game.delete()
        messages.warning(request, f'ลบเกม "{game_name}" ออกจากระบบเรียบร้อยแล้ว')
    return redirect(f"{redirect('community:backoffice_dashboard').url}?tab=games")


@login_required
@staff_required
def backoffice_thread_delete(request, thread_id):
    """ลบกระทู้โดยผู้ดูแลระบบ"""
    if request.method == 'POST':
        thread = get_object_or_404(Thread, pk=thread_id)
        title = thread.title
        thread.delete()
        messages.warning(request, f'ลบกระทู้ "{title}" เรียบร้อยแล้ว')
    return redirect('community:backoffice_dashboard')


@login_required
@staff_required
def backoffice_comment_delete(request, comment_id):
    """ลบความคิดเห็นโดยผู้ดูแลระบบ"""
    if request.method == 'POST':
        comment = get_object_or_404(Comment, pk=comment_id)
        comment.delete()
        messages.warning(request, 'ลบความคิดเห็นเรียบร้อยแล้ว')
    return redirect('community:backoffice_dashboard')


@login_required
@staff_required
def backoffice_guide_delete(request, guide_id):
    """ลบไกด์โดยผู้ดูแลระบบ"""
    if request.method == 'POST':
        guide = get_object_or_404(GameGuide, pk=guide_id)
        title = guide.title
        guide.delete()
        messages.warning(request, f'ลบไกด์ "{title}" เรียบร้อยแล้ว')
    return redirect('community:backoffice_dashboard')


@login_required
@staff_required
def backoffice_group_delete(request, group_id):
    """ลบกลุ่มสนทนาโดยผู้ดูแลระบบ"""
    if request.method == 'POST':
        group = get_object_or_404(GroupChat, pk=group_id)
        name = group.name
        group.delete()
        messages.warning(request, f'ลบกลุ่มสนทนา "{name}" เรียบร้อยแล้ว')
    return redirect('community:backoffice_dashboard')
