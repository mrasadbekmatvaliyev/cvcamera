"""
Fine-tuning script for YOLOv8 on the traffic vehicle dataset.

Usage:
    python training/train.py
    python training/train.py --config training/config.yaml --epochs 100

Prerequisites:
    1. Run `python dataset/generate_dataset.py` first to create the dataset.
    2. Ensure dataset/data.yaml exists and paths are correct.
"""

import argparse
import sys
import types
import yaml
from pathlib import Path

# Python 3.14 + torchvision compatibility workaround
import importlib.metadata as _ilm
import torch as _torch

def _pure_nms(boxes, scores, iou_threshold):
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


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def train(config_path: str):
    cfg = load_config(config_path)

    model = YOLO(cfg['base_model'])
    print(f"Base model: {cfg['base_model']}")
    print(f"Dataset: {cfg['data']}")
    print(f"Epochs: {cfg['epochs']} | Image size: {cfg['imgsz']}")

    results = model.train(
        data=cfg['data'],
        epochs=cfg['epochs'],
        imgsz=cfg['imgsz'],
        batch=cfg['batch'],
        lr0=cfg['lr0'],
        patience=cfg['patience'],
        save=True,
        save_period=cfg.get('save_period', 10),
        project=cfg.get('project', 'training/runs'),
        name=cfg.get('name', 'traffic_v1'),
        pretrained=True,
        device=cfg.get('device', 'cpu'),
        workers=cfg.get('workers', 4),
        verbose=True,
    )

    best_model_path = Path(results.save_dir) / 'weights' / 'best.pt'
    output_path = Path(cfg.get('output_model', 'training/traffic_best.pt'))
    if best_model_path.exists():
        import shutil
        shutil.copy(str(best_model_path), str(output_path))
        print(f"\nBest model saved to: {output_path}")
    else:
        print("\nWarning: best.pt not found — check training output.")

    print("\nTraining complete.")
    print(f"  mAP50:    {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
    print(f"  mAP50-95: {results.results_dict.get('metrics/mAP50-95(B)', 'N/A')}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='training/config.yaml')
    args = parser.parse_args()
    train(args.config)
