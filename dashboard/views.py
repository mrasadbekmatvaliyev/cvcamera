import json
from django.shortcuts import render
from detector.models import VehicleLog
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from django.db.models.functions import ExtractHour, TruncDate


def dashboard_view(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)

    total_count = VehicleLog.objects.count()
    today_count = VehicleLog.objects.filter(detected_time__gte=today_start).count()
    weekly_count = VehicleLog.objects.filter(detected_time__gte=week_start).count()

    recent_detections = VehicleLog.objects.order_by('-detected_time')[:20]

    # Hourly stats for today (Chart.js)
    hourly_qs = (
        VehicleLog.objects
        .filter(detected_time__gte=today_start)
        .annotate(hour=ExtractHour('detected_time'))
        .values('hour')
        .annotate(total=Count('id'))
        .order_by('hour')
    )
    hourly_labels = [f"{h['hour']:02d}:00" for h in hourly_qs]
    hourly_data = [h['total'] for h in hourly_qs]

    # Vehicle type breakdown (Chart.js)
    type_qs = (
        VehicleLog.objects
        .values('vehicle_type')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    type_labels = [t['vehicle_type'] for t in type_qs]
    type_data = [t['total'] for t in type_qs]

    # Daily stats — last 7 days (Chart.js)
    daily_qs = (
        VehicleLog.objects
        .filter(detected_time__gte=week_start)
        .annotate(day=TruncDate('detected_time'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )
    daily_labels = [str(d['day']) for d in daily_qs]
    daily_data = [d['total'] for d in daily_qs]

    context = {
        'total_count': total_count,
        'today_count': today_count,
        'weekly_count': weekly_count,
        'recent_detections': recent_detections,
        # JSON for charts
        'hourly_labels': json.dumps(hourly_labels),
        'hourly_data': json.dumps(hourly_data),
        'type_labels': json.dumps(type_labels),
        'type_data': json.dumps(type_data),
        'daily_labels': json.dumps(daily_labels),
        'daily_data': json.dumps(daily_data),
    }
    return render(request, 'dashboard/index.html', context)
