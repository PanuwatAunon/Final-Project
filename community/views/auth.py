from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from ..forms import UserRegistrationForm


def register(request):
    """ฟังก์ชันสำหรับการลงทะเบียน"""
    if request.user.is_authenticated:
        return redirect('community:home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ')
            return redirect('community:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'community/register.html', {'form': form})


def login_view(request):
    """ฟังก์ชันสำหรับการเข้าสู่ระบบ"""
    if request.user.is_authenticated:
        return redirect('community:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        # ตรวจสอบว่าผู้ใช้ถูกแบน
        if user and hasattr(user, 'ban') and user.ban.is_active():
            reason_text = f" (เหตุผล: {user.ban.reason})" if user.ban.reason else ""
            if user.ban.banned_until:
                diff = user.ban.banned_until - timezone.now()
                total_seconds = int(diff.total_seconds())
                if total_seconds > 0:
                    days = total_seconds // 86400
                    hours = (total_seconds % 86400) // 3600
                    mins = (total_seconds % 3600) // 60
                    if days > 0:
                        time_left_str = f"เหลือเวลาอีก {days} วัน {hours} ชั่วโมง"
                    elif hours > 0:
                        time_left_str = f"เหลือเวลาอีก {hours} ชั่วโมง {mins} นาที"
                    else:
                        time_left_str = f"เหลือเวลาอีก {max(1, mins)} นาที"
                    
                    banned_date_str = timezone.localtime(user.ban.banned_until).strftime('%d/%m/%Y %H:%M')
                    messages.error(request, f'บัญชีนี้ถูกระงับการใช้งานชั่วคราว ({time_left_str} - ปลดแบนวันที่ {banned_date_str}){reason_text}')
                    return redirect('community:login')
                else:
                    # หมดเวลาแบนแล้ว ปลดแบนอัตโนมัติ
                    user.ban.delete()
            else:
                messages.error(request, f'บัญชีนี้ถูกระงับการใช้งานถาวร{reason_text}')
                return redirect('community:login')
        
        if user is not None:
            login(request, user)
            messages.success(request, f'ยินดีต้อนรับ {username}!')
            return redirect('community:home')
        else:
            messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    
    return render(request, 'community/login.html')


def logout_view(request):
    """ฟังก์ชันสำหรับการออกจากระบบ"""
    logout(request)
    messages.success(request, 'ออกจากระบบสำเร็จ')
    return redirect('community:home')
