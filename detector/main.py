import cv2
import os
import sys
import types
import django
import torch

# Python 3.14 + torchvision compatibility workaround
import importlib.metadata as _ilm

def _pure_nms(boxes, scores, iou_threshold):
    order = scores.argsort(descending=True)
    keep = []
    while order.numel() > 0:
        i = order[0]
        keep.append(i.item())
        if order.numel() == 1:
            break
        rest = order[1:]
        xx1 = torch.maximum(boxes[i, 0], boxes[rest, 0])
        yy1 = torch.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = torch.minimum(boxes[i, 2], boxes[rest, 2])
        yy2 = torch.minimum(boxes[i, 3], boxes[rest, 3])
        inter = torch.clamp(xx2 - xx1, 0) * torch.clamp(yy2 - yy1, 0)
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_r = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / (area_i + area_r - inter + 1e-6)
        order = rest[iou <= iou_threshold]
    return torch.tensor(keep, dtype=torch.long)

_tv = types.ModuleType('torchvision')
_tv_ops = types.ModuleType('torchvision.ops')
_tv_ops.nms = _pure_nms
_tv.ops = _tv_ops
sys.modules['torchvision'] = _tv
sys.modules['torchvision.ops'] = _tv_ops
_orig_ver = _ilm.version
_ilm.version = lambda n: '0.27.0' if n == 'torchvision' else _orig_ver(n)

from ultralytics import YOLO
from collections import OrderedDict
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'traffic_app.settings')
django.setup()

from core.utils.geometry import is_crossing_line
from core.services.db_logger import db_logger

# COCO class IDs for target vehicles
VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}


class VehicleDetector:
    def __init__(self, model_path='yolov8n.pt', video_source=0):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = YOLO(model_path).to(self.device)

        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {video_source}")

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

        # Counting line Y position — configurable via env
        self.line_y = int(os.getenv('LINE_Y', 400))
        self.count = 0

        self.max_cache_size = 1000
        self.track_history = OrderedDict()
        self.crossed_ids = OrderedDict()

    def _cleanup_cache(self, cache: OrderedDict):
        while len(cache) > self.max_cache_size:
            cache.popitem(last=False)

    def run(self):
        print(f"AI Detector online. Device: {self.device} | Line Y: {self.line_y}")

        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                break

            results = self.model.track(
                frame,
                persist=True,
                classes=list(VEHICLE_CLASSES.keys()),
                verbose=False,
                tracker="bytetrack.yaml",
                imgsz=640,
            )

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                clss = results[0].boxes.cls.cpu().numpy().astype(int)
                confs = results[0].boxes.conf.cpu().numpy()

                for box, track_id, cls, conf in zip(boxes, ids, clss, confs):
                    x1, y1, x2, y2 = box
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    label = VEHICLE_CLASSES.get(cls, 'vehicle')

                    if track_id in self.track_history:
                        prev_y = self.track_history[track_id]
                        if track_id not in self.crossed_ids:
                            if is_crossing_line(prev_y, cy, self.line_y):
                                self.count += 1
                                self.crossed_ids[track_id] = True
                                direction = "down" if cy > prev_y else "up"
                                db_logger.log_detection(
                                    object_id=int(track_id),
                                    vehicle_type=label,
                                    direction=direction,
                                    confidence=round(float(conf), 4),
                                )
                                self._cleanup_cache(self.crossed_ids)

                    self.track_history[track_id] = cy
                    self._cleanup_cache(self.track_history)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        f"{label} ID:{track_id} {conf:.2f}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2,
                    )

            frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            cv2.line(frame, (0, self.line_y), (frame_w, self.line_y), (0, 0, 255), 2)
            cv2.putText(
                frame,
                f"Count: {self.count}",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

            cv2.imshow("Traffic AI", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()
        db_logger.stop()


if __name__ == "__main__":
    video_source = os.getenv('VIDEO_SOURCE', 'traffic.mp4')
    model_path = os.getenv('MODEL_PATH', 'yolov8n.pt')

    if isinstance(video_source, str) and video_source.isdigit():
        video_source = int(video_source)
    elif isinstance(video_source, str) and not os.path.exists(video_source):
        alt = os.path.join(os.path.dirname(__file__), '..', video_source)
        if os.path.exists(alt):
            video_source = alt

    detector = VehicleDetector(model_path=model_path, video_source=video_source)
    detector.run()
