from django.utils import timezone
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from .models import UserProfile

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if user is banned
            if hasattr(request.user, 'ban') and request.user.ban.is_active():
                ban = request.user.ban
                logout(request)
                reason_text = f" (เหตุผล: {ban.reason})" if ban.reason else ""
                if ban.banned_until:
                    diff = ban.banned_until - timezone.now()
                    total_seconds = int(diff.total_seconds())
                    if total_seconds > 0:
                        days = total_seconds // 86400
                        hours = (total_seconds % 86400) // 3600
                        mins = (total_seconds % 3600) // 60
                        if days > 0:
                            time_str = f"เหลือเวลาอีก {days} วัน {hours} ชั่วโมง"
                        elif hours > 0:
                            time_str = f"เหลือเวลาอีก {hours} ชั่วโมง {mins} นาที"
                        else:
                            time_str = f"เหลือเวลาอีก {max(1, mins)} นาที"
                        banned_date_str = timezone.localtime(ban.banned_until).strftime('%d/%m/%Y %H:%M')
                        messages.error(request, f'บัญชีของคุณถูกระงับการใช้งานชั่วคราว ({time_str} - ปลดแบนวันที่ {banned_date_str}){reason_text}')
                    else:
                        ban.delete()
                else:
                    messages.error(request, f'บัญชีของคุณถูกระงับการใช้งานถาวร{reason_text}')
                return redirect('community:login')
                
            # Update last activity time
            UserProfile.objects.filter(user=request.user).update(last_activity=timezone.now())
            
        response = self.get_response(request)
        return response
