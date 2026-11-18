from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.models import User, Group
from unfold.admin import ModelAdmin
from .models import (
    Game, UserProfile, Thread, Comment,
    GameGuide, GuideComment, GroupChat, GroupMessage, Friendship, DirectMessage,
    Notification, Report, UserBan, UserWarning
)

admin.site.unregister(User)
admin.site.unregister(Group)

# อนุญาตให้เข้าถึงหน้า Django Admin (/admin/) ได้เฉพาะ Superuser เท่านั้น (พนักงานทั่วไปใช้ /backoffice/)
admin.site.has_permission = lambda request: request.user.is_active and request.user.is_superuser


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    actions = ['ban_users', 'unban_users']

    def ban_users(self, request, queryset):
        banned_count = 0
        for user in queryset:
            if user.is_superuser or user.is_staff:
                continue
            if not hasattr(user, 'ban'):
                UserBan.objects.create(user=user, reason="ระงับการใช้งานโดยผู้ดูแลระบบ")
                banned_count += 1
            else:
                ban = user.ban
                if not ban.is_active():
                    ban.banned_until = None
                    ban.reason = "ระงับการใช้งานโดยผู้ดูแลระบบ"
                    ban.save()
                    banned_count += 1
        self.message_user(request, f'ระงับการใช้งานผู้ใช้ {banned_count} คนเรียบร้อยแล้ว (ถาวร)')
    ban_users.short_description = 'ระงับการใช้งานผู้ใช้ที่เลือก (ถาวร)'

    def unban_users(self, request, queryset):
        unbanned_count = 0
        for user in queryset:
            if hasattr(user, 'ban'):
                user.ban.delete()
                unbanned_count += 1
        self.message_user(request, f'ปลดแบนผู้ใช้ {unbanned_count} คนเรียบร้อยแล้ว')
    unban_users.short_description = 'ปลดแบนผู้ใช้ที่เลือก'


@admin.register(Game)
class GameAdmin(ModelAdmin):
    list_display = ('cover_thumbnail', 'name', 'genre', 'created_at')
    search_fields = ('name', 'genre')
    list_filter = ('genre', 'created_at')

    def cover_thumbnail(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 8px;" />', obj.cover_image.url)
        return "ไม่มีภาพ"
    cover_thumbnail.short_description = 'รูปปก'


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'points', 'ban_status', 'created_at')
    search_fields = ('user__username',)
    list_filter = ('created_at',)
    autocomplete_fields = ('user',)

    def ban_status(self, obj):
        if hasattr(obj.user, 'ban') and obj.user.ban.is_active():
            return "ถูกระงับการใช้งาน"
        return "ปกติ"
    ban_status.short_description = 'สถานะบัญชี'

@admin.register(UserWarning)
class UserWarningAdmin(ModelAdmin):
    list_display = ('user', 'reason', 'created_by', 'created_at')
    search_fields = ('user__username', 'reason')
    list_filter = ('created_at', 'created_by')
    readonly_fields = ('created_at', 'created_by')
    autocomplete_fields = ('user',)
    
    def get_fields(self, request, obj=None):
        if obj:
            return ('user', 'reason', 'created_by', 'created_at')
        return ('user', 'reason')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserBan)
class UserBanAdmin(ModelAdmin):
    list_display = ('user', 'active_status', 'banned_at', 'banned_until')
    search_fields = ('user__username',)
    list_filter = ('banned_at', 'banned_until')
    readonly_fields = ('banned_at',)
    autocomplete_fields = ('user',)

    def active_status(self, obj):
        return obj.is_active()
    active_status.boolean = True
    active_status.short_description = 'มีผลบังคับอยู่'



@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = (
        'id', 
        'reporter', 
        'reported_target_type', 
        'target_summary', 
        'report_type_display', 
        'colored_status', 
        'created_at', 
        'view_target_button'
    )
    search_fields = ('reporter__username', 'reported_user__username', 'description', 'thread__title', 'guide__title', 'comment__content')
    list_filter = ('report_type', 'status', 'created_at')
    readonly_fields = ('created_at', 'resolved_at')
    autocomplete_fields = ('reporter', 'reported_user', 'thread', 'guide', 'comment')
    actions = ['approve_and_delete_content', 'approve_and_ban', 'reject_report']

    def reported_target_type(self, obj):
        if obj.thread:
            return format_html('<span>กระทู้</span>')
        elif obj.guide:
            return format_html('<span>ไกด์เกม</span>')
        elif obj.comment:
            return format_html('<span>ความคิดเห็น</span>')
        elif obj.reported_user:
            return format_html('<span>ผู้ใช้งาน</span>')
        return format_html('<span>ทั่วไป</span>')
    reported_target_type.short_description = 'ประเภทสิ่งที่ถูกรายงาน'

    def target_summary(self, obj):
        if obj.thread:
            return f"กระทู้: {obj.thread.title[:35]}..." if len(obj.thread.title) > 35 else f"กระทู้: {obj.thread.title}"
        elif obj.guide:
            return f"ไกด์: {obj.guide.title[:35]}..." if len(obj.guide.title) > 35 else f"ไกด์: {obj.guide.title}"
        elif obj.comment:
            return f"ความเห็น: {obj.comment.content[:35]}..." if len(obj.comment.content) > 35 else f"ความเห็น: {obj.comment.content}"
        elif obj.reported_user:
            return f"ผู้ใช้: {obj.reported_user.username}"
        return "-"
    target_summary.short_description = 'รายละเอียดเนื้อหาที่ถูกรายงาน'

    def report_type_display(self, obj):
        return obj.get_report_type_display()
    report_type_display.short_description = 'สาเหตุที่รายงาน'

    def colored_status(self, obj):
        if obj.status == 'pending':
            return format_html('<span style="background: #FEF5E8; color: #854F0B; padding: 3px 10px; border-radius: 12px; font-weight: bold; border: 1px solid #EF9F27;">รอการตรวจสอบ</span>')
        elif obj.status == 'approved':
            return format_html('<span style="background: #FCEBEB; color: #791F1F; padding: 3px 10px; border-radius: 12px; font-weight: bold; border: 1px solid #E24B4A;">อนุมัติแล้ว</span>')
        elif obj.status == 'rejected':
            return format_html('<span style="background: #F1EFE8; color: #5F5E5A; padding: 3px 10px; border-radius: 12px; font-weight: bold; border: 1px solid #D3D1C7;">ปฏิเสธรายงาน</span>')
        return obj.get_status_display()
    colored_status.short_description = 'สถานะ'

    def view_target_button(self, obj):
        if obj.thread:
            url = reverse('community:thread_detail', args=[obj.thread.id])
            return format_html('<a href="{}" target="_blank" style="padding: 5px 12px; background: #7F77DD; color: white; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block;">ดูโพสต์</a>', url)
        elif obj.comment and obj.comment.thread:
            url = reverse('community:thread_detail', args=[obj.comment.thread.id])
            return format_html('<a href="{}" target="_blank" style="padding: 5px 12px; background: #1D9E75; color: white; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block;">ดูความเห็น</a>', url)
        elif obj.guide:
            url = reverse('community:guide_detail', args=[obj.guide.id])
            return format_html('<a href="{}" target="_blank" style="padding: 5px 12px; background: #1D9E75; color: white; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block;">ดูไกด์</a>', url)
        elif obj.reported_user:
            url = reverse('community:user_profile', args=[obj.reported_user.username])
            return format_html('<a href="{}" target="_blank" style="padding: 5px 12px; background: #D4537E; color: white; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block;">ดูโปรไฟล์</a>', url)
        return "-"
    view_target_button.short_description = 'ตรวจสอบหน้าเว็บ'

    def approve_and_ban(self, request, queryset):
        approved_count = 0
        banned_count = 0
        for report in queryset:
            if report.status == 'pending':
                report.status = 'approved'
                report.resolved_at = timezone.now()
                report.admin_notes = "อนุมัติรายงานและแบนผู้ใช้สำเร็จ"
                report.save()
                approved_count += 1
                
                if report.reported_user:
                    if not hasattr(report.reported_user, 'ban'):
                        UserBan.objects.create(
                            user=report.reported_user,
                            reason=f"ถูกระงับการใช้งานเนื่องจากถูกรายงานข้อหา: {report.get_report_type_display()} - {report.description}"
                        )
                        banned_count += 1
                    else:
                        ban = report.reported_user.ban
                        if not ban.is_active():
                            ban.banned_until = None
                            ban.reason = f"ถูกระงับการใช้งานเนื่องจากถูกรายงานข้อหา: {report.get_report_type_display()} - {report.description}"
                            ban.save()
                            banned_count += 1
        self.message_user(request, f'อนุมัติรายงาน {approved_count} รายการ และแบนผู้ใช้ {banned_count} คนสำเร็จ')
    approve_and_ban.short_description = 'อนุมัติรายงานและระงับการใช้งานผู้ใช้ที่ถูกรายงาน'

    def reject_report(self, request, queryset):
        updated_count = queryset.update(status='rejected', resolved_at=timezone.now(), admin_notes="ปฏิเสธการรายงาน")
        self.message_user(request, f'ปฏิเสธการรายงาน {updated_count} รายการเรียบร้อยแล้ว')
    reject_report.short_description = 'ปฏิเสธรายงานที่เลือก (ไม่พบความผิด)'

    def approve_and_delete_content(self, request, queryset):
        count = 0
        for report in queryset:
            if report.comment:
                target_comment = report.comment
                report.comment = None
                target_comment.delete()
            elif report.thread:
                target_thread = report.thread
                report.thread = None
                target_thread.delete()
            elif report.guide:
                target_guide = report.guide
                report.guide = None
                target_guide.delete()
            report.status = 'approved'
            report.resolved_at = timezone.now()
            report.admin_notes = "อนุมัติรายงานและลบเนื้อหาที่มีปัญหาเรียบร้อย"
            report.save()
            count += 1
        self.message_user(request, f'อนุมัติรายงานและลบเนื้อหา {count} รายการสำเร็จ')
    approve_and_delete_content.short_description = 'อนุมัติรายงานและลบเนื้อหาที่ถูกรายงานทันที'

    fieldsets = (
        ('รายละเอียดการรายงาน', {
            'fields': ('reporter', 'report_type', 'description', 'thread', 'comment', 'guide', 'reported_user')
        }),
        ('สถานะและการดำเนินการ', {
            'fields': ('status', 'created_at', 'resolved_at', 'admin_notes')
        }),
    )


@admin.register(Thread)
class ThreadAdmin(ModelAdmin):
    list_display = ('title', 'author', 'visibility', 'created_at', 'open_on_site')
    search_fields = ('title', 'content', 'author__username')
    list_filter = ('visibility', 'created_at')
    autocomplete_fields = ('author', 'game')

    def open_on_site(self, obj):
        url = reverse('community:thread_detail', args=[obj.id])
        return format_html(
            '<a href="{}" target="_blank" style="padding: 5px 12px; background: #7F77DD; color: white; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block;">ดูหน้ากระทู้</a>',
            url
        )
    open_on_site.short_description = 'ดูหน้าเว็บจริง'


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ('id', 'comment_preview', 'thread', 'author', 'created_at', 'open_on_site')
    search_fields = ('content', 'author__username')
    list_filter = ('created_at',)
    autocomplete_fields = ('author', 'thread')

    def comment_preview(self, obj):
        return obj.content[:40] + ('...' if len(obj.content) > 40 else '')
    comment_preview.short_description = 'เนื้อหาความคิดเห็น'

    def open_on_site(self, obj):

        if obj.thread:
            url = reverse('community:thread_detail', args=[obj.thread.id])
            return format_html(
                '<a href="{}" target="_blank" style="padding: 5px 12px; background: #7F77DD; color: white; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block;">ดูในกระทู้</a>',
                url
            )
        return "-"
    open_on_site.short_description = 'ดูหน้าเว็บจริง'


@admin.register(GameGuide)
class GameGuideAdmin(ModelAdmin):
    list_display = ('title', 'author', 'game', 'visibility', 'created_at', 'open_on_site')
    search_fields = ('title', 'content', 'author__username')
    list_filter = ('visibility', 'created_at', 'game')
    autocomplete_fields = ('author', 'game')

    def open_on_site(self, obj):
        url = reverse('community:guide_detail', args=[obj.id])
        return format_html(
            '<a href="{}" target="_blank" style="padding: 5px 12px; background: #1D9E75; color: white; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block;">ดูไกด์บนเว็บ</a>',
            url
        )
    open_on_site.short_description = 'ดูหน้าเว็บจริง'


@admin.register(GroupChat)
class GroupChatAdmin(ModelAdmin):
    list_display = ('name', 'game', 'creator', 'created_at')
    search_fields = ('name', 'description', 'creator__username')
    list_filter = ('created_at', 'game')
    autocomplete_fields = ('creator', 'game')




