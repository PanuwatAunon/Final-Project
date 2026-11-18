from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from community.models import (
    UserProfile, Thread, Comment, GameGuide, GuideComment, 
    Report, GroupChat, Game
)

# Tailwind input style
TW_INPUT = "w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition"
TW_SELECT = "w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition bg-white"
TW_TEXTAREA = "w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition"
TW_FILE = "w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"

class UserRegistrationForm(UserCreationForm):
    """ฟอร์มสำหรับการลงทะเบียนผู้ใช้"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('อีเมลนี้ถูกใช้แล้ว')
        return email


class UserProfileForm(forms.ModelForm):
    """ฟอร์มสำหรับแก้ไขโปรไฟล์ผู้ใช้"""
    class Meta:
        model = UserProfile
        fields = ('bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': TW_TEXTAREA,
                'rows': 4,
                'placeholder': 'บอกเล่าเกี่ยวกับตัวคุณ'
            }),
            'avatar': forms.FileInput(attrs={'class': TW_FILE}),
        }


class UserUpdateForm(forms.ModelForm):
    """ฟอร์มสำหรับแก้ไขข้อมูลผู้ใช้"""
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        widgets = {
            'email': forms.EmailInput(attrs={'class': TW_INPUT}),
            'first_name': forms.TextInput(attrs={'class': TW_INPUT}),
            'last_name': forms.TextInput(attrs={'class': TW_INPUT}),
        }


class ThreadForm(forms.ModelForm):
    """ฟอร์มสำหรับสร้าง/แก้ไขกระทู้"""
    class Meta:
        model = Thread
        fields = ('content', 'visibility', 'image', 'video')
        widgets = {
            'content': forms.Textarea(attrs={
                'class': TW_TEXTAREA,
                'rows': 6,
                'placeholder': 'ป้อนเนื้อหาของคุณ'
            }),
            'visibility': forms.Select(attrs={'class': TW_SELECT}),
            'image': forms.FileInput(attrs={'class': TW_FILE}),
            'video': forms.FileInput(attrs={'class': TW_FILE}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.content:
            instance.title = instance.content[:250]
        elif not instance.title:
            instance.title = "กระทู้พูดคุย"
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class BaseCommentForm(forms.ModelForm):
    """ฟอร์มพื้นฐานสำหรับความเห็น"""
    class Meta:
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'class': TW_TEXTAREA,
                'rows': 3,
                'placeholder': 'แสดงความคิดเห็นของคุณ'
            }),
        }

class CommentForm(BaseCommentForm):
    """ฟอร์มสำหรับเพิ่มความเห็นในกระทู้"""
    class Meta(BaseCommentForm.Meta):
        model = Comment


class GameGuideForm(forms.ModelForm):
    """ฟอร์มสำหรับสร้างไกด์เกม"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['game'].empty_label = "กรุณาเลือกเกมของคุณ"

    class Meta:
        model = GameGuide
        fields = ('game', 'title', 'content', 'visibility')
        widgets = {
            'game': forms.Select(attrs={'class': TW_SELECT}),
            'title': forms.TextInput(attrs={
                'class': TW_INPUT,
                'placeholder': 'ป้อนชื่อไกด์'
            }),
            'content': forms.Textarea(attrs={
                'class': TW_TEXTAREA,
                'rows': 8,
                'placeholder': 'ป้อนเนื้อหาไกด์'
            }),
            'visibility': forms.Select(attrs={'class': TW_SELECT}),
        }


class GuideCommentForm(BaseCommentForm):
    """ฟอร์มสำหรับเพิ่มความเห็นในไกด์"""
    class Meta(BaseCommentForm.Meta):
        model = GuideComment


class ReportForm(forms.ModelForm):
    """ฟอร์มสำหรับการรายงานเนื้อหา"""
    class Meta:
        model = Report
        fields = ('report_type', 'description')
        widgets = {
            'report_type': forms.Select(attrs={'class': TW_SELECT}),
            'description': forms.Textarea(attrs={
                'class': TW_TEXTAREA,
                'rows': 4,
                'placeholder': 'อธิบายรายละเอียดของปัญหา'
            }),
        }


class GroupChatForm(forms.ModelForm):
    """ฟอร์มสำหรับสร้างกลุ่มคุย"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['game'].empty_label = "-- กรุณาเลือกเกมประจำกลุ่ม --"

    class Meta:
        model = GroupChat
        fields = ('game', 'name', 'description')
        labels = {
            'game': 'เกมประจำกลุ่ม',
            'name': 'ชื่อกลุ่มพูดคุย',
            'description': 'คำอธิบาย / วัตถุประสงค์ของกลุ่ม',
        }
        widgets = {
            'game': forms.Select(attrs={
                'class': TW_SELECT,
                'id': 'groupGameSelect'
            }),
            'name': forms.TextInput(attrs={
                'class': TW_INPUT,
                'placeholder': 'ตั้งชื่อกลุ่ม',
                'maxlength': '200',
                'id': 'groupNameInput'
            }),
            'description': forms.Textarea(attrs={
                'class': TW_TEXTAREA,
                'rows': 4,
                'placeholder': 'แนะนำเกี่ยวกับกลุ่ม',
                'id': 'groupDescInput'
            }),
        }



class GameForm(forms.ModelForm):
    """ฟอร์มสำหรับจัดการเกม (เพิ่ม / แก้ไขเกมโดยแอดมิน)"""
    class Meta:
        model = Game
        fields = ('name', 'recommended_age', 'description', 'cover_image')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': TW_INPUT,
                'placeholder': 'ระบุชื่อเกม เช่น Valorant, Genshin Impact'
            }),
            'recommended_age': forms.Select(attrs={
                'class': TW_SELECT,
            }),
            'description': forms.Textarea(attrs={
                'class': TW_TEXTAREA,
                'rows': 4,
                'placeholder': 'คำอธิบายรายละเอียดเกี่ยวกับเกม'
            }),
            'cover_image': forms.FileInput(attrs={'class': TW_FILE}),
        }

