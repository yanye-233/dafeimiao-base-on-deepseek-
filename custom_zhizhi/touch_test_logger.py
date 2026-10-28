# -*- coding: utf-8 -*-
"""触摸分区测试日志 - 记录每次触摸的区域和回复"""
import json, os, time
from datetime import datetime

LOG_FILE = r"D:\软件\大肥鱼桌宠\custom_zhizhi\touch_test_log.jsonl"

def log_touch(zone_key, zone_name, reply_text, reply_voice=None):
    """记录一次触摸测试"""
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "zone_key": zone_key,
        "zone_name": zone_name,
        "reply_text": reply_text,
        "reply_voice": reply_voice,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[{entry['ts']}] {zone_name} -> {reply_text[:30]}...")

def read_log(limit=20):
    """读取最近的测试记录"""
    if not os.path.exists(LOG_FILE):
        print("暂无测试记录")
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    entries = [json.loads(line) for line in lines[-limit:]]
    print(f"最近 {len(entries)} 条记录:")
    for e in entries:
        print(f"  [{e['ts']}] {e['zone_name']:12s} -> {e['reply_text'][:40]}")
    return entries

def clear_log():
    """清空测试记录"""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
        print("已清空测试记录")
    else:
        print("暂无记录")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_log()
    else:
        read_log()
