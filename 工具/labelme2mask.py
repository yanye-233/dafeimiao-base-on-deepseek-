# -*- coding: utf-8 -*-
"""labelme JSON -> zone_map.png + zone_id_names.json

触摸分区掩膜生成工具:
1. 用 labelme 在正面立绘上标注分区多边形, 存为 custom_zhizhi/zhizhi_front.json
2. 运行本脚本: python 工具/labelme2mask.py
3. 重启桌宠生效

优先级: custom_zhizhi/zone_priority.json 手动序号(越前越优先, 小部位放前面避免被大分区盖住),
未列出的标签按多边形最小面积升序自动排。
覆盖不了的透明区域最后兜底为 身上(body)。
"""
import json
import os
import numpy as np
from PIL import Image, ImageDraw

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "custom_zhizhi"))
SRC = os.path.join(BASE, "zhizhi_front.png")
JSON = os.path.join(BASE, "zhizhi_front.json")

KEY_MAP = {"猫耳": "ear", "脸脸": "face", "脸颊": "cheek", "嘴巴": "mouth",
           "下巴": "chin", "头顶": "head", "头": "head", "胸口": "chest",
           "手臂": "arm", "小手手": "hand", "大腿": "thigh", "裙底": "skirt_bottom",
           "涩涩的地方": "lewd", "小腿": "calf", "脚脚": "foot", "身上": "body"}

img = Image.open(SRC).convert("RGBA")
W, H = img.size
alpha = np.array(img.split()[3]) > 32

data = json.load(open(JSON, encoding="utf-8"))
label_masks = {}   # label -> uint8 mask
label_area = {}    # label -> min polygon area
for sh in data["shapes"]:
    lab = sh["label"]
    pts = [(float(p[0]), float(p[1])) for p in sh["points"]]
    if len(pts) < 3:
        continue
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(pts, fill=1)
    arr = np.array(m, dtype=bool)
    area = int(arr.sum())
    if area == 0:
        continue
    label_masks[lab] = (label_masks.get(lab, np.zeros((H, W), bool)) | arr)
    label_area[lab] = min(label_area.get(lab, 1 << 30), area)

# priority: zone_priority.json(手动序号, 越前越优先) > 未列出的按多边形最小面积升序
pri_path = os.path.join(BASE, "zone_priority.json")
try:
    manual = json.load(open(pri_path, encoding="utf-8"))
    if not isinstance(manual, list):
        manual = []
except Exception:
    manual = []
manual = [str(x) for x in manual if str(x) in label_area]
rest_labels = sorted((k for k in label_area if k not in manual),
                     key=lambda k: label_area[k])
order = manual + rest_labels
print("priority order (manual first, then area-asc):")
for lab in order:
    tag = "manual" if lab in manual else "area"
    print(f"  [{tag}] {lab}: min_poly {label_area[lab]}px total {int(label_masks[lab].sum())}px")

ids = np.zeros((H, W), dtype=np.uint8)
names = {}
next_id = 1
for lab in order:
    m = label_masks[lab] & alpha & (ids == 0)
    if not m.any():
        print(f"  !! {lab} fully covered by higher-priority labels, skipped")
        continue
    ids[m] = next_id
    names[next_id] = [KEY_MAP.get(lab, lab), lab]
    next_id += 1
rest = alpha & (ids == 0)
if rest.any():
    ids[rest] = next_id
    names[next_id] = ["body", "身上"]

Image.fromarray(ids, mode="L").save(os.path.join(BASE, "zone_map.png"))
json.dump({str(k): v for k, v in names.items()},
          open(os.path.join(BASE, "zone_id_names.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nzone ids:", {k: v for k, v in names.items()})
print("coverage: %d/%d opaque px labeled" % (int((ids > 0).sum()), int(alpha.sum())))
