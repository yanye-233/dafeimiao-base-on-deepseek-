# -*- coding: utf-8 -*-
"""_beta_mem 结构体测试: 写入/会话切分/召回/预算/蒸馏/容错/并发/迁移, 全绿=结构可合成。"""
import json
import os
import shutil
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from store import ChatStore

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_data")
LEGACY = r"D:\软件\大肥鱼桌宠\zhizhi_memory.json"
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))


def fresh(tag):
    d = os.path.join(TEST_DIR, tag)
    if os.path.exists(d):
        shutil.rmtree(d)
    return ChatStore(d)


def ts_shift(base, secs):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(
        time.mktime(time.strptime(base, "%Y-%m-%d %H:%M:%S")) + secs))


# T1 写入 + 自动会话切分 (30min 间隙)
st = fresh("t1")
t0 = "2026-10-28 00:00:00"
st.append("user", "爸爸想点外卖了", ts=t0)
st.append("assistant", "小芷芷帮爸爸看评论哒", ts=ts_shift(t0, 60))
st.append("user", "再看一个会话", ts=ts_shift(t0, 3600))   # 1小时后 -> 新会话
st.flush_sessions()
ss = st._sess_data()
check("T1_写入与会话切分", len(ss) == 2 and list(ss.values())[0]["turns"] == 1,
      "sessions=%d" % len(ss))

# T2 离线召回: 命中 + 未命中
st = fresh("t2")
st.append("user", "小芷芷会不会点外卖呀", ts=t0)
st.append("assistant", "会哒会哒，小芷芷学会看评论啦，黄焖鸡不点哟", ts=ts_shift(t0, 5))
st.append("user", "今天天气怎么样", ts=ts_shift(t0, 10))
st.append("assistant", "外面冷冷的，爸爸穿厚点哟", ts=ts_shift(t0, 15))
hit = st.recall("小芷芷会点外卖吗")
miss = st.recall("量子力学方程组怎么解")
check("T2_离线召回", len(hit) >= 1 and "黄焖鸡" in hit[0][1]["text"] and len(miss) == 0,
      "hit=%d miss=%d" % (len(hit), len(miss)))

# T3 三层上下文预算
st = fresh("t3")
for i in range(30):
    st.append("user", "第%d个问题：爸爸喜欢在深夜写代码" % i, ts=ts_shift(t0, i * 10))
    st.append("assistant", "小芷芷陪着爸爸哒", ts=ts_shift(t0, i * 10 + 5))
st.append("user", "爸爸喜欢什么饮料呀", ts=ts_shift(t0, 400))
st.append("assistant", "爸爸喜欢冰美式，但是深夜要少喝哟", ts=ts_shift(t0, 405))
st.distill()
ctx = st.context("爸爸喜欢什么", budget=1200)
check("T3_上下文组装", "小芷芷记得的事" in ctx and "旧对话" in ctx and "最近对话" in ctx and len(ctx) <= 1300,
      "len=%d" % len(ctx))

# T4 蒸馏: 抽事实 + 摘要 + 幂等
st = fresh("t4")
st.append("user", "爸爸喜欢在周末睡懒觉", ts=t0)
st.append("assistant", "小芷芷也喜欢赖在爸爸旁边哒", ts=ts_shift(t0, 5))
r1 = st.distill()
r2 = st.distill()
facts = st.facts()
check("T4_蒸馏迭代", r1["sessions"] == 1 and r2["sessions"] == 0 and len(facts) >= 1
      and "睡懒觉" in facts[0]["v"],
      "r1=%s r2_sessions=%d facts=%d" % (json.dumps(r1, ensure_ascii=False), r2["sessions"], len(facts)))

# T5 坏行容错 (模拟写一半崩溃)
st = fresh("t5")
st.append("user", "问题一", ts=t0)
with open(st.f_dialog, "a", encoding="utf-8") as f:
    f.write('{"id":99,"ts":"2026-10-28 00:0')       # 截断行
st.append("assistant", "回答一", ts=ts_shift(t0, 5))
rows = st._rows()
check("T5_崩溃容错", len(rows) == 2 and all(r["id"] != 99 for r in rows),
      "rows=%d" % len(rows))

# T6 并发写入 (2线程 x 200条, 无丢行)
st = fresh("t6")
def w(tag):
    for i in range(200):
        st.append("user", "%s_%d" % (tag, i), sess="s_fixed", ts=ts_shift(t0, i))
ths = [threading.Thread(target=w, args=("A",)), threading.Thread(target=w, args=("B",))]
[x.start() for x in ths]
[x.join() for x in ths]
n = len(st._rows())
ids = set(r["id"] for r in st._rows())
check("T6_并发安全", n == 400 and len(ids) == 400, "rows=%d uniq=%d" % (n, len(ids)))

# T7 迁移: 导入现有 zhizhi_memory.json
st = fresh("t7")
if os.path.exists(LEGACY):
    n = st.import_legacy(LEGACY)
    s = st.stats()
    check("T7_旧记忆迁移", n == 40 and s["messages"] == 40,
          "imported=%d msgs=%d" % (n, s["messages"]))
else:
    check("T7_旧记忆迁移", False, "legacy not found")

# T8 规模压测: 1000条写入+召回耗时
st = fresh("t8")
t_start = time.time()
for i in range(500):
    st.append("user", "压力测试问题编号%d：今天吃什么" % i, ts=ts_shift(t0, i * 30))
    st.append("assistant", "压力测试回答编号%d" % i, ts=ts_shift(t0, i * 30 + 2))
w_ms = (time.time() - t_start) * 1000
t_start = time.time()
hits = st.recall("问题编号233：今天吃什么")
r_ms = (time.time() - t_start) * 1000
check("T8_千条压测", len(st._rows()) == 1000 and len(hits) >= 1 and w_ms < 3000 and r_ms < 500,
      "write=%.0fms recall=%.0fms" % (w_ms, r_ms))

print("\n==== %d/%d PASS ====" % (sum(1 for _, ok, _ in results if ok), len(results)))
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
