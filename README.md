# Traffic AI — YOLOv8 Vehicle Detection & Business Intelligence

Real-time vehicle detection, counting, and analytics platform built with YOLOv8 + Django.

## Features

| Feature | Status |
|---|---|
| YOLOv8 detection (car, bus, truck, motorcycle) | ✅ |
| ByteTrack multi-object tracking | ✅ |
| Counting line with up/down direction | ✅ |
| object_id, confidence logging to DB | ✅ |
| SQLite (default) / MySQL support | ✅ |
| Dashboard with hourly, daily, type charts | ✅ |
| AI Chatbot (Uzbek NLP) | ✅ |
| Dataset generator from video | ✅ |
| Fine-tuning script | ✅ |
| Async DB logging (non-blocking) | ✅ |

## Project Structure

```
traffic_project/
├── detector/           # YOLO detection loop + DB model
│   └── main.py         # Run this to start detection
├── core/
│   ├── services/       # AsyncLogger (DB writer)
│   └── utils/          # Geometry helpers
├── dashboard/          # Django app — charts & stats
├── chatbot/            # Django app — NLP query engine
├── dataset/
│   ├── generate_dataset.py  # Extract frames → YOLO labels
│   ├── data.yaml            # Dataset config
│   ├── images/train|val/
│   └── labels/train|val/
├── training/
│   ├── train.py        # Fine-tuning script
│   └── config.yaml     # Hyperparameters
├── fake_data/
│   └── generate_data.py
├── templates/
├── .env                # All secrets and config here
└── requirements.txt
```

## Quick Start

```bash
# 1. Clone and enter project
cd traffic_project

# 2. One-command setup
bash setup.sh

# 3. Start web server
python manage.py runserver

# 4. Start vehicle detector (separate terminal)
python detector/main.py
```

Open http://127.0.0.1:8000 for the dashboard.

## Configuration (.env)

```env
SECRET_KEY=your-50-char-secret-key     # REQUIRED in production
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,yourdomain.com
TIME_ZONE=Asia/Tashkent

DB_ENGINE=django.db.backends.sqlite3   # or mysql
VIDEO_SOURCE=traffic.mp4               # or 0 for webcam
MODEL_PATH=yolov8n.pt                  # or training/traffic_best.pt
LINE_Y=400                             # Counting line Y position
```

## Dataset & Fine-tuning

```bash
# Step 1: Generate dataset from traffic video
python dataset/generate_dataset.py --video traffic.mp4 --frames 200

# Step 2: Fine-tune YOLOv8 on the generated dataset
python training/train.py

# Step 3: Use the fine-tuned model
# Set MODEL_PATH=training/traffic_best.pt in .env
```

## AI Chatbot Queries (Uzbek)

| Query | Example |
|---|---|
| Bugungi hisobot | "Bugun nechta mashina o'tdi?" |
| Kechagi | "Kecha nechta truck o'tdi?" |
| Vaqt oralig'i | "Soat 10 dan 12 gacha nechta o'tdi?" |
| Peak hour | "Eng band vaqt qaysi?" |
| Jami | "Jami statistika" |

## Database Schema

| Field | Type | Description |
|---|---|---|
| id | BigInt PK | Auto-increment |
| object_id | Int | YOLO tracker ID |
| vehicle_type | Char(50) | car / bus / truck / motorcycle |
| direction | Char(10) | up / down |
| confidence | Float | Detection confidence 0–1 |
| detected_time | DateTime | Auto timestamp |

## YOLO Classes (COCO → Local)

| COCO ID | Local ID | Name |
|---|---|---|
| 2 | 0 | car |
| 3 | 1 | motorcycle |
| 5 | 2 | bus |
| 7 | 3 | truck |

## Security Notes

- Never commit `.env` to git (it is in `.gitignore`)
- Set `DEBUG=False` in production
- Change `SECRET_KEY` to a random 50-char string
- Set `ALLOWED_HOSTS` to your actual domain
