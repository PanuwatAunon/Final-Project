from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


AGE_CHOICES = [
    ('3+', '3+ : สำหรับทุกวัย'),
    ('7+', '7+ : อายุ 7 ปีขึ้นไป'),
    ('12+', '12+ : อายุ 12 ปีขึ้นไป'),
    ('13+', '13+ : วัยรุ่น 13 ปีขึ้นไป'),
    ('16+', '16+ : อายุ 16 ปีขึ้นไป'),
    ('18+', '18+ : ผู้ใหญ่ 18 ปีขึ้นไป'),
]


class Game(models.Model):
    """โมเดลสำหรับเก็บข้อมูลเกม"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    genre = models.CharField(max_length=100, blank=True)
    target_gender = models.CharField(max_length=50, default='ทุกเพศ', blank=True, verbose_name='เพศ')
    recommended_age = models.CharField(max_length=50, choices=AGE_CHOICES, default='3+', verbose_name='อายุที่แนะนำ')
    cover_image = models.ImageField(upload_to='games/', null=True, blank=True)
    likes = models.ManyToManyField(User, related_name='liked_games', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.recommended_age:
            self.recommended_age = '3+'
        # Keep genre synced with recommended_age for backward compatibility with existing templates/badges
        self.genre = self.recommended_age
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """โมเดลสำหรับโปรไฟล์ผู้ใช้"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    points = models.IntegerField(default=0)  # คะแนนจากการรับไลค์
    last_activity = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def is_online(self):
        """เช็คสถานะออนไลน์ (ภายใน 5 นาที)"""
        if self.last_activity:
            now = timezone.now()
            diff = now - self.last_activity
            return diff.total_seconds() < 300  # 5 minutes
        return False

    def get_rank(self):
        """คำนวณ Rank ตามคะแนนแบบสมดุล (ภาษาไทย)"""
        if self.points <= 20:
            return "ผู้เริ่มต้น"
        elif self.points <= 50:
            return "นักผจญภัย"
        elif self.points <= 100:   
            return "ผู้บุกเบิก"
        elif self.points <= 200:   
            return "ผู้ชี้แนะ"
        elif self.points <= 400:
            return "ยอดฝีมือ"
        elif self.points <= 700:
            return "ผู้เชี่ยวชาญ"
        elif self.points <= 1200:
            return "ปรมาจารย์"
        elif self.points <= 2000:
            return "จอมราชัน"
        else:
            return "ตำนาน"
        
        


REACTION_CHOICES = [
    ('like', '❤️ ถูกใจ'),
    ('laugh', '😆 ขำ'),
    ('sad', '😢 เศร้า'),
    ('angry', '😡 โกรธ'),
]

REACTION_EMOJIS = {code: label.split()[0] for code, label in REACTION_CHOICES}


class Thread(models.Model):
    """โมเดลสำหรับกระทู้/หัวข้อการคุย"""
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True, related_name='threads')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='threads')
    title = models.CharField(max_length=300)
    content = models.TextField()
    image = models.ImageField(upload_to='thread_images/', null=True, blank=True)
    video = models.FileField(upload_to='thread_videos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)
    
    VISIBILITY_CHOICES = [
        ('public', 'สาธารณะ'),
        ('friends', 'เฉพาะเพื่อน'),
        ('private', 'ส่วนตัว'),
    ]
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_like_count(self):
        return self.reactions.count()

    def get_reaction_counts(self):
        counts = {'like': 0, 'laugh': 0, 'sad': 0, 'angry': 0, 'total': 0}
        for r in self.reactions.all():
            counts[r.reaction_type] = counts.get(r.reaction_type, 0) + 1
            counts['total'] += 1
        return counts

    def get_user_reaction(self, user):
        if not user or not user.is_authenticated:
            return None
        r = self.reactions.filter(user=user).first()
        return r.reaction_type if r else None

    @property
    def views(self):
        return self.views_count


class ThreadReaction(models.Model):
    """โมเดลแสดงความรู้สึกในกระทู้"""
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='thread_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('thread', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.reaction_type} on {self.thread.title}"


class Comment(models.Model):
    """โมเดลสำหรับความเห็นในกระทู้"""
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username}"
    
    def get_like_count(self):
        return self.reactions.count()

    def get_reaction_counts(self):
        counts = {'like': 0, 'laugh': 0, 'sad': 0, 'angry': 0, 'total': 0}
        for r in self.reactions.all():
            counts[r.reaction_type] = counts.get(r.reaction_type, 0) + 1
            counts['total'] += 1
        return counts

    def get_user_reaction(self, user):
        if not user or not user.is_authenticated:
            return None
        r = self.reactions.filter(user=user).first()
        return r.reaction_type if r else None


class CommentReaction(models.Model):
    """โมเดลแสดงความรู้สึกในความคิดเห็นกระทู้"""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comment', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.reaction_type} on comment {self.comment.id}"


class GameGuide(models.Model):
    """โมเดลสำหรับเก็บไกด์เกม"""
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True, related_name='guides')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guides')
    title = models.CharField(max_length=300)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)
    
    VISIBILITY_CHOICES = [
        ('public', 'สาธารณะ'),
        ('friends', 'เฉพาะเพื่อน'),
        ('private', 'ส่วนตัว'),
    ]
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_like_count(self):
        return self.reactions.count()

    def get_reaction_counts(self):
        counts = {'like': 0, 'laugh': 0, 'sad': 0, 'angry': 0, 'total': 0}
        for r in self.reactions.all():
            counts[r.reaction_type] = counts.get(r.reaction_type, 0) + 1
            counts['total'] += 1
        return counts

    def get_user_reaction(self, user):
        if not user or not user.is_authenticated:
            return None
        r = self.reactions.filter(user=user).first()
        return r.reaction_type if r else None

    @property
    def views(self):
        return self.views_count


class GuideReaction(models.Model):
    """โมเดลแสดงความรู้สึกในไกด์"""
    guide = models.ForeignKey(GameGuide, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guide_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('guide', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.reaction_type} on {self.guide.title}"


class GuideComment(models.Model):
    """โมเดลสำหรับความเห็นในไกด์"""
    guide = models.ForeignKey(GameGuide, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guide_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username}"
    
    def get_like_count(self):
        return self.reactions.count()

    def get_reaction_counts(self):
        counts = {'like': 0, 'laugh': 0, 'sad': 0, 'angry': 0, 'total': 0}
        for r in self.reactions.all():
            counts[r.reaction_type] = counts.get(r.reaction_type, 0) + 1
            counts['total'] += 1
        return counts

    def get_user_reaction(self, user):
        if not user or not user.is_authenticated:
            return None
        r = self.reactions.filter(user=user).first()
        return r.reaction_type if r else None


class GuideCommentReaction(models.Model):
    """โมเดลแสดงความรู้สึกในความคิดเห็นไกด์"""
    comment = models.ForeignKey(GuideComment, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guide_comment_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comment', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.reaction_type} on guide comment {self.comment.id}"


class GroupChat(models.Model):
    """โมเดลสำหรับกลุ่มคุยกัน"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_groups')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_chat_groups')
    members = models.ManyToManyField(User, related_name='chat_group_members')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    """โมเดลสำหรับข้อความในกลุ่ม"""
    group = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='group_chat_images/', null=True, blank=True)
    video = models.FileField(upload_to='group_chat_videos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username}"


class Friendship(models.Model):
    """โมเดลสำหรับความสัมพันธ์เพื่อน"""
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_received')
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
    
    def __str__(self):
        status = "friends" if self.is_accepted else "pending"
        return f"{self.from_user.username} -> {self.to_user.username} ({status})"


class DirectMessage(models.Model):
    """โมเดลสำหรับข้อความส่วนตัว"""
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(blank=True) # Allow blank content if sending media
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    video = models.FileField(upload_to='chat_videos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"From {self.from_user.username} to {self.to_user.username}"


class Notification(models.Model):
    """โมเดลสำหรับการแจ้งเตือน"""
    NOTIFICATION_TYPES = [
        ('reply', 'ตอบกลับ'),
        ('like', 'กดถูกใจ'),
        ('friend_request', 'คำขอเพิ่มเพื่อน'),
        ('friend_accept', 'ยอมรับเพื่อน'),
        ('message', 'ข้อความใหม่'),
        ('warning', 'คำเตือนจากระบบ'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    guide = models.ForeignKey(GameGuide, on_delete=models.CASCADE, null=True, blank=True)
    warning = models.ForeignKey('UserWarning', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}"


class Report(models.Model):
    """โมเดลสำหรับการรายงาน"""
    REPORT_TYPES = [
        ('spam', 'สแปม'),
        ('offensive', 'เนื้อหาไม่สุภาพ'),
        ('hate_speech', 'เนื้อหาเกลียดชัง'),
        ('adult', 'เนื้อหาสำหรับผู้ใหญ่'),
        ('violence', 'ความรุนแรง'),
        ('misleading', 'ข้อมูลเท็จ'),
        ('copyright', 'ละเมิดลิขสิทธิ์'),
        ('other', 'อื่นๆ'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'รอการตรวจสอบ'),
        ('approved', 'อนุมัติ'),
        ('rejected', 'ปฏิเสธ'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField()
    thread = models.ForeignKey(Thread, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.SET_NULL, null=True, blank=True)
    guide = models.ForeignKey('GameGuide', on_delete=models.SET_NULL, null=True, blank=True)
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='reports_against')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report #{self.id} - {self.get_report_type_display()}"


class UserBan(models.Model):
    """โมเดลสำหรับจำกัดสิทธิผู้ใช้"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ban')
    reason = models.TextField()
    banned_at = models.DateTimeField(auto_now_add=True)
    banned_until = models.DateTimeField(null=True, blank=True)  # None = permanent
    
    def is_active(self):
        if self.banned_until is None:
            return True
        return timezone.now() < self.banned_until
    
    def __str__(self):
        return f"{self.user.username} - Banned"


class UserWarning(models.Model):
    """โมเดลสำหรับคำเตือนผู้ใช้"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warnings')
    reason = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_warnings')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Create Notification
            Notification.objects.create(
                user=self.user,
                notification_type='warning',
                from_user=self.created_by,
                warning=self
            )

    def __str__(self):
        return f"Warning for {self.user.username}"
