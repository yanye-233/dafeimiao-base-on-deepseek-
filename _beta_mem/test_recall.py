# -*- coding: utf-8 -*-
"""回归: 召回改进(单字兜底+短query自适应) 不破坏原8项, 新增短词/隔词召回用例。"""
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from store import ChatStore

D = os.path.join(HERE, "_test_data", "regression")
if os.path.exists(D):
    shutil.rmtree(D)
st = ChatStore(D)
t0 = "2026-10-28 00:00:00"


def ts(sec):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(
        time.mktime(time.strptime(t0, "%Y-%m-%d %H:%M:%S")) + sec))


# 原T2用例
st.append("user", "小芷芷会不会点外卖呀", ts=ts(0))
st.append("assistant", "会哒会哒，小芷芷学会看评论啦，黄焖鸡不点哟", ts=ts(5))
st.append("user", "今天天气怎么样", ts=ts(10))
st.append("assistant", "外面冷冷的，爸爸穿厚点哟", ts=ts(15))
hit = st.recall("小芷芷会点外卖吗")
miss = st.recall("量子力学方程组怎么解")
r = [("R1_正常召回", len(hit) >= 1 and "黄焖鸡" in hit[0][1]["text"]), ("R2_不误召回", len(miss) == 0)]

# 新: 短词 + 被隔开的词
st.append("user", "爸爸摸了摸小芷芷的头", ts=ts(20))
st.append("assistant", "[触摸:头]（蹭蹭）嘿嘿，摸头小芷芷最乖啦", ts=ts(25))
h2 = st.recall("摸头")
r.append(("R3_短词隔词召回(摸头)", len(h2) >= 1 and "最乖" in h2[0][1]["text"]))
h3 = st.recall("外卖")
r.append(("R4_两字词召回(外卖)", len(h3) >= 1))
h4 = st.recall("的")   # 单字query无字组 -> 应空
r.append(("R5_单字query不炸", isinstance(h4, list)))
h5 = st.recall("今天天气怎么样")
r.append(("R6_原文query召回", len(h5) >= 1))

ok = True
for name, passed in r:
    print("%s %s" % ("PASS" if passed else "FAIL", name))
    ok = ok and passed
print("==== %d/%d PASS ====" % (sum(1 for _, p in r if p), len(r)))
sys.exit(0 if ok else 1)
