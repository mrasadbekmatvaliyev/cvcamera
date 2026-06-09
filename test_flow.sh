#!/bin/bash
cd traffic_project
# Serverni fonda ishga tushiramiz
./venv/bin/python manage.py runserver 127.0.0.1:8001 > server.log 2>&1 &
SERVER_PID=$!

# Server tayyor bo'lishini kutamiz
sleep 5

echo "--- Dashboard testi ---"
curl -s http://127.0.0.1:8001/ | grep -E "Jami transportlar|Bugungi sana"

echo -e "\n--- Chatbot testi (Bugun nechta mashina o'tdi?) ---"
curl -s "http://127.0.0.1:8001/chatbot/api/response/?message=bugun"

echo -e "\n--- Chatbot testi (Chap tomonga nechta?) ---"
curl -s "http://127.0.0.1:8001/chatbot/api/response/?message=chap"

echo -e "\n--- Deteksiya simulyatsiyasi ---"
# Yangi mashina qo'shamiz
PYTHONPATH=. ./venv/bin/python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'traffic_app.settings'); django.setup(); from detector.models import VehicleLog; VehicleLog.objects.create(vehicle_type='Tesla', direction='up')"
echo "Yangi transport (Tesla) qo'shildi."

echo -e "\n--- Dashboard yangilanishini tekshirish ---"
curl -s http://127.0.0.1:8001/ | grep "Tesla"

# Serverni to'xtatamiz
kill $SERVER_PID
echo -e "\nServer to'xtatildi."
