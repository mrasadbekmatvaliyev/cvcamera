"""
Dataset generator: extracts frames from a traffic video, runs YOLOv8 inference,
and saves images + YOLO-format labels for fine-tuning.

Usage:
    python dataset/generate_dataset.py --video traffic.mp4 --output dataset --frames 200

COCO class mapping used in this project:
    2 → car  →  class 0
    3 → motorcycle → class 1
    5 → bus  →  class 2
    7 → truck →  class 3
"""

import argparse
import os
import sys
import types
import random
import cv2
from pathlib import Path

# Python 3.14 + torchvision compatibility workaround
import importlib.metadata as _ilm
import torch as _torch

def _pure_nms(boxes, scores, iou_threshold):
    """Pure PyTorch NMS (no torchvision C extension needed)."""
    order = scores.argsort(descending=True)
    keep = []
    while order.numel() > 0:
        i = order[0]
        keep.append(i.item())
        if order.numel() == 1:
            break
        rest = order[1:]
        xx1 = _torch.maximum(boxes[i, 0], boxes[rest, 0])
        yy1 = _torch.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = _torch.minimum(boxes[i, 2], boxes[rest, 2])
        yy2 = _torch.minimum(boxes[i, 3], boxes[rest, 3])
        inter = _torch.clamp(xx2 - xx1, 0) * _torch.clamp(yy2 - yy1, 0)
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_r = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / (area_i + area_r - inter + 1e-6)
        order = rest[iou <= iou_threshold]
    return _torch.tensor(keep, dtype=_torch.long)

_tv = types.ModuleType('torchvision')
_tv_ops = types.ModuleType('torchvision.ops')
_tv_ops.nms = _pure_nms
_tv.ops = _tv_ops
sys.modules['torchvision'] = _tv
sys.modules['torchvision.ops'] = _tv_ops

_orig_ver = _ilm.version
_ilm.version = lambda n: '0.27.0' if n == 'torchvision' else _orig_ver(n)

from ultralytics import YOLO

COCO_TO_LOCAL = {2: 0, 3: 1, 5: 2, 7: 3}
TARGET_CLASSES = list(COCO_TO_LOCAL.keys())


def extract_and_annotate(video_path: str, output_dir: str, n_frames: int, val_ratio: float):
    output = Path(output_dir)
    for split in ('train', 'val'):
        (output / 'images' / split).mkdir(parents=True, exist_ok=True)
        (output / 'labels' / split).mkdir(parents=True, exist_ok=True)

    model = YOLO('yolov8n.pt')

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < n_frames:
        n_frames = total_frames
        print(f"Video has only {total_frames} frames — using all.")

    step = max(1, total_frames // n_frames)
    frame_indices = list(range(0, total_frames, step))[:n_frames]
    random.shuffle(frame_indices)

    val_count = max(1, int(len(frame_indices) * val_ratio))
    val_indices = set(frame_indices[:val_count])

    saved = 0
    for idx in sorted(frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        results = model(frame, classes=TARGET_CLASSES, verbose=False)
        boxes = results[0].boxes

        if boxes is None or len(boxes) == 0:
            continue

        split = 'val' if idx in val_indices else 'train'
        fname = f"frame_{idx:06d}"

        img_path = output / 'images' / split / f"{fname}.jpg"
        cv2.imwrite(str(img_path), frame)

        h, w = frame.shape[:2]
        label_path = output / 'labels' / split / f"{fname}.txt"
        with open(label_path, 'w') as f:
            for box in boxes:
                cls_coco = int(box.cls.item())
                cls_local = COCO_TO_LOCAL.get(cls_coco)
                if cls_local is None:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx = (x1 + x2) / 2 / w
                cy = (y1 + y2) / 2 / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                f.write(f"{cls_local} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

        saved += 1
        if saved % 20 == 0:
            print(f"  Saved {saved}/{len(frame_indices)} frames...")

    cap.release()

    train_imgs = len(list((output / 'images' / 'train').glob('*.jpg')))
    val_imgs = len(list((output / 'images' / 'val').glob('*.jpg')))
    print(f"\nDataset ready: {train_imgs} train / {val_imgs} val images")
    print(f"Output: {output.resolve()}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate YOLO dataset from traffic video')
    parser.add_argument('--video', default='traffic.mp4')
    parser.add_argument('--output', default='dataset')
    parser.add_argument('--frames', type=int, default=200)
    parser.add_argument('--val-ratio', type=float, default=0.2)
    args = parser.parse_args()

    extract_and_annotate(args.video, args.output, args.frames, args.val_ratio)
