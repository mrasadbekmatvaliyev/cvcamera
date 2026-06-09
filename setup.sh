#!/bin/bash
set -e

echo "=== Traffic AI — Project Setup ==="

# 1. Virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created virtual environment."
fi
source venv/bin/activate

# 2. Dependencies
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "Dependencies installed."

# 3. Logs directory
mkdir -p logs

# 4. Migrations
python manage.py makemigrations --no-input
python manage.py migrate --no-input
echo "Database migrated."

# 5. Superuser (skip if exists)
echo "from django.contrib.auth import get_user_model; U=get_user_model(); \
U.objects.filter(username='admin').exists() or U.objects.create_superuser('admin','admin@local.com','admin123')" \
| python manage.py shell -q 2>/dev/null && echo "Admin user ready (admin / admin123)."

# 6. Fake data
python fake_data/generate_data.py --days 7 --count 150
echo "Fake data generated."

echo ""
echo "=== Setup complete ==="
echo "  Run server:    python manage.py runserver"
echo "  Run detector:  python detector/main.py"
echo "  Generate dataset: python dataset/generate_dataset.py --video traffic.mp4"
echo "  Train model:   python training/train.py"
