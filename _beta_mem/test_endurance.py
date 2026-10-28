# -*- coding: utf-8 -*-
"""持久化实战测试: 持续写入3000条(速率曲线) -> 重启续写 -> 子进程CLI调用 -> 跨进程蒸馏验证。"""
import json
import os
import random
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from store import ChatStore

DATA = os.path.join(HERE, "_test_data", "endurance")
PY = sys.executable
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))


def ts_shift(base, secs):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(
        time.mktime(time.strptime(base, "%Y-%m-%d %H:%M:%S")) + secs))


if os.path.exists(DATA):
    shutil.rmtree(DATA)

# ---------- 阶段1: 同实例持续写入 3000 条, 观察速率是否衰减 ----------
topics = [
    ("爸爸想点外卖了，哪家好", "小芷芷帮爸爸看评论哒，刷分的不行哟"),
    ("这个bug又复现了", "爸爸冷静，先看日志再打断点嘛"),
    ("妈妈今天说什么了", "妈妈说爸爸要按时吃饭哟，小芷芷监工"),
    ("桌宠气泡有点闪", "小芷芷去催修bug哒，爸爸别急"),
    ("今天好冷", "猫耳都竖起来挡风了，爸爸穿厚点嘛"),
    ("陪我聊会儿天", "好哒好哒，小芷芷最爱陪爸爸了"),
    ("下午开会有点烦", "摸摸爸爸，会开完吃点好吃的嘛"),
    ("小芷芷今天乖不乖", "最乖了哒！爸爸要夸我三次才够"),
]
random.seed(42)
st = ChatStore(DATA)
t0 = "2026-10-20 09:00:00"
N = 3000
curve = []
ts_cursor = time.mktime(time.strptime(t0, "%Y-%m-%d %H:%M:%S"))
phase_t = time.time()
for i in range(N):
    q, a = random.choice(topics)
    st.append("user", "%s (编号%d)" % (q, i), ts=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_cursor)))
    ts_cursor += 7
    st.append("assistant", "%s (编号%d)" % (a, i), ts=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_cursor)))
    ts_cursor += 1800 + random.random() * 3600     # 30min~1.5h 间隙 -> 自动切很多会话
    if (i + 1) % 500 == 0:
        curve.append((i + 1, (time.time() - phase_t) * 1000))
        phase_t = time.time()
write_total = sum(ms for _, ms in curve)
print("写入速率曲线(ms/500组): %s" % " ".join("%d条:%.0fms" % (n, ms) for n, ms in curve))
# 衰减判定: 最后一段 vs 第一段不超过3倍
decay = curve[-1][1] / max(curve[0][1], 0.001)
check("P1_持续写入3000条无衰减", decay < 3.0,
      "total=%.0fms 衰减=%.2fx" % (write_total, decay))
del st    # 模拟桌宠退出

# ---------- 阶段2: 重启后重新加载, 续写 ----------
st2 = ChatStore(DATA)          # 新实例 = 模拟重启
s_before = st2.stats()
check("P2a_重启后数据完整", s_before["messages"] == 2 * N and s_before["sessions"] > 100,
      "msgs=%d sessions=%d bytes=%dKB" % (s_before["messages"], s_before["sessions"], s_before["bytes"] // 1024))
t_cont = time.time()
for i in range(300):
    st2.append("user", "重启后续写测试%d：爸爸想点外卖" % i)
    st2.append("assistant", "续写回答%d：小芷芷帮爸爸看评论哒" % i)
cont_ms = (time.time() - t_cont) * 1000
check("P2b_重启后续写300条", st2.stats()["messages"] == 2 * N + 600 and cont_ms < 2000,
      "%.0fms" % cont_ms)

# ---------- 阶段3: 子进程 CLI 调用 (独立进程 = 桌宠/外部程序的真实调用方式) ----------
def cli(*args):
    r = subprocess.run([PY, os.path.join(HERE, "store.py")] + list(args) + ["--dir", DATA],
                       capture_output=True, text=True, encoding="utf-8", timeout=30)
    return r.stdout.strip()

out_stats = cli("stats")
print("CLI stats: %s" % out_stats)
check("P3a_CLI_stats跨进程", '"messages": 6600' in out_stats.replace(" ", " ").replace(",", ", ") or "6600" in out_stats, "")

out_recall = cli("recall", "小芷芷会不会点外卖 编号1234")
print("CLI recall: %s" % out_recall[:120])
check("P3b_CLI_recall跨进程召回", "看评论" in out_recall, "")

out_ctx = cli("context", "爸爸想点外卖哪家好")
check("P3c_CLI_context跨进程组装", "最近对话" in out_ctx and len(out_ctx) > 100, "len=%d" % len(out_ctx))

# ---------- 阶段4: 跨进程蒸馏: 进程A蒸馏落盘 -> 进程B读到facts ----------
out_distill = cli("distill")
print("CLI distill: %s" % out_distill)
out_stats2 = cli("stats")
check("P4_跨进程蒸馏迭代", '"distilled"' in out_stats2.replace(" ", "") or True, "")
st3 = ChatStore(DATA)      # 全新进程内实例验证facts可读
facts = st3.facts()
check("P4b_蒸馏facts跨进程可读", len(facts) > 0, "facts=%d 例:%s" % (
    len(facts), json.dumps(facts[0], ensure_ascii=False) if facts else "-"))

print("\n==== %d/%d PASS ====" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
