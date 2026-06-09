import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from detector.models import VehicleLog
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta


VEHICLE_ALIASES = {
    'mashina': 'car',
    'car': 'car',
    'avtomobil': 'car',
    'bus': 'bus',
    'avtobus': 'bus',
    'truck': 'truck',
    'yuk mashinasi': 'truck',
    'yukxona': 'truck',
    'motorcycle': 'motorcycle',
    'mototsikl': 'motorcycle',
    'moto': 'motorcycle',
}

HOUR_PATTERN = re.compile(r'soat\s+(\d{1,2})(?:[:\.](\d{2}))?\s+dan\s+(\d{1,2})(?:[:\.](\d{2}))?\s+gacha')
TYPE_PATTERN = re.compile(
    r'(mashina|car|avtomobil|bus|avtobus|truck|yuk mashinasi|motorcycle|mototsikl|moto)'
)


def _detect_vehicle_type(message: str):
    m = TYPE_PATTERN.search(message)
    if m:
        return VEHICLE_ALIASES.get(m.group(1))
    return None


class ChatbotEngine:
    @staticmethod
    def process(message: str) -> str:
        msg = message.lower().strip()
        now = timezone.now()

        # "Soat X dan Y gacha nechta o'tdi?"
        m = HOUR_PATTERN.search(msg)
        if m:
            h1, m1, h2, m2 = m.group(1), m.group(2) or '0', m.group(3), m.group(4) or '0'
            start = now.replace(hour=int(h1), minute=int(m1), second=0, microsecond=0)
            end = now.replace(hour=int(h2), minute=int(m2), second=59, microsecond=999999)
            qs = VehicleLog.objects.filter(detected_time__range=(start, end))
            vtype = _detect_vehicle_type(msg)
            if vtype:
                qs = qs.filter(vehicle_type=vtype)
            count = qs.count()
            label = vtype or "transport"
            return f"Soat {h1}:{m1.zfill(2)} dan {h2}:{m2.zfill(2)} gacha {count} ta {label} o'tdi."

        # "Eng band vaqt qaysi?"
        if any(k in msg for k in ['eng band', 'eng gavjum', 'peak', 'busiest']):
            from django.db.models.functions import ExtractHour
            result = (
                VehicleLog.objects.annotate(hour=ExtractHour('detected_time'))
                .values('hour')
                .annotate(total=Count('id'))
                .order_by('-total')
                .first()
            )
            if result:
                return f"Eng band vaqt: soat {result['hour']}:00 da ({result['total']} ta transport)."
            return "Hozircha ma'lumot yo'q."

        # "Kecha nechta X o'tdi?"
        if 'kecha' in msg:
            yesterday = now.date() - timedelta(days=1)
            qs = VehicleLog.objects.filter(detected_time__date=yesterday)
            vtype = _detect_vehicle_type(msg)
            if vtype:
                qs = qs.filter(vehicle_type=vtype)
            count = qs.count()
            label = vtype or "transport"
            return f"Kecha {count} ta {label} o'tdi."

        # "Bugun nechta X o'tdi?"
        if 'bugun' in msg:
            qs = VehicleLog.objects.filter(detected_time__date=now.date())
            vtype = _detect_vehicle_type(msg)
            if vtype:
                qs = qs.filter(vehicle_type=vtype)
            count = qs.count()
            label = vtype or "transport"
            return f"Bugun {count} ta {label} aniqlandi."

        # "Nechta truck o'tdi?" — all-time by type
        vtype = _detect_vehicle_type(msg)
        if vtype and any(k in msg for k in ['nechta', 'jami', 'total', 'hammasi']):
            count = VehicleLog.objects.filter(vehicle_type=vtype).count()
            return f"Jami {count} ta {vtype} aniqlangan."

        # "Statistika / umumiy"
        if any(k in msg for k in ['statistika', 'umumiy', 'jami', 'total']):
            stats = (
                VehicleLog.objects.values('vehicle_type')
                .annotate(total=Count('id'))
                .order_by('-total')
            )
            if not stats:
                return "Hozircha ma'lumot yo'q."
            lines = [f"  • {s['vehicle_type']}: {s['total']} ta" for s in stats]
            return "Jami statistika:\n" + "\n".join(lines)

        # "Eng ko'p o'tgan transport"
        if any(k in msg for k in ["eng ko'p", 'eng kop', 'most']):
            result = (
                VehicleLog.objects.values('vehicle_type')
                .annotate(total=Count('id'))
                .order_by('-total')
                .first()
            )
            if result:
                return f"Eng ko'p: {result['vehicle_type']} ({result['total']} ta)."

        return (
            "Quyidagi savollarni berishingiz mumkin:\n"
            "• Bugun nechta mashina o'tdi?\n"
            "• Kecha nechta truck o'tdi?\n"
            "• Soat 10 dan 12 gacha nechta o'tdi?\n"
            "• Eng band vaqt qaysi?\n"
            "• Jami statistika"
        )


def chatbot_view(request):
    return render(request, 'chatbot/chat.html')


@csrf_exempt
def chat_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
    else:
        message = request.GET.get('message', '').strip()

    if not message:
        return JsonResponse({'response': 'Xabar yozing...'})

    if len(message) > 500:
        return JsonResponse({'response': 'Xabar juda uzun.'})

    return JsonResponse({'response': ChatbotEngine.process(message)})
