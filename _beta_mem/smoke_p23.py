# -*- coding: utf-8 -*-
"""PATCH23 冒烟: 模拟桌宠 _call_ds 记忆链路(临时目录, 不碰真实数据)。"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from store import ChatStore

D = os.path.join(HERE, "_test_data", "smoke")
if os.path.exists(D):
    shutil.rmtree(D)

mem = ChatStore(D)
mem.append("user", "爸爸喜欢在深夜写代码")
mem.append("assistant", "小芷芷陪着爸爸哒")
mem.distill()

# 1. 模拟 _call_ds 上下文组装
ctx = mem.context("爸爸喜欢什么", budget=1600)
messages = [{"role": "system", "content": "persona"}]
if ctx:
    messages.append({"role": "system", "content": "[记忆检索]\n" + ctx})
messages.append({"role": "user", "content": "爸爸喜欢什么"})
assert len(messages) == 3 and "记忆检索" in messages[1]["content"] and "喜欢" in messages[1]["content"]
print("SMOKE1_上下文组装 OK (含事实层:%s)" % ("记得的事" in ctx))

# 2. 模拟回复成功入史
mem.append("user", "爸爸喜欢什么")
mem.append("assistant", "爸爸喜欢写代码哒，小芷芷知道哟")
assert mem.stats()["messages"] == 4
print("SMOKE2_对话入史 OK msgs=%d" % mem.stats()["messages"])

# 3. 模拟断网离线回声
echo = mem.recall("爸爸喜欢什么", top_k=1)
assert echo and "写代码" in echo[0][1]["text"]
print("SMOKE3_离线回声 OK => %s" % ("（翻小本本）" + echo[0][1]["text"][:40]))

# 4. 模拟事件冒话成对入史(触发记录+台词, 同 PATCH23 桌宠侧逻辑)
mem.append("user", "[触摸:头]（爸爸触发）")
mem.append("assistant", "[触摸:头] （蹭蹭）嘿嘿，摸头小芷芷最乖啦")
h = mem.recall("摸头", top_k=1)
assert h and "最乖" in h[0][1]["text"], "事件召回失败: %r" % (h,)
print("SMOKE4_事件成对入史召回 OK")

shutil.rmtree(D)
print("==== SMOKE 4/4 PASS ====")
