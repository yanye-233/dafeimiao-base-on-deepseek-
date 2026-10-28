# _beta_mem 小芷芷对话记忆引擎（测试版）

> 目的: 替换主程序 `zhizhi_memory.json` 的 40 条硬截断方案（旧对话直接丢弃）。
> 结构验证通过后再合成进 桌宠.py。主程序暂未动（还在做其他变更）。

## 数据结构 (data/)

| 文件 | 角色 | 崩溃安全 |
|------|------|---------|
| `dialog.jsonl` | 对话流水, append-only, 一行一条 `{id,ts,sess,role,text}` | 坏行跳过 + 粘连行二次切割恢复 |
| `sessions.json` | 会话索引 `{sess_id: {start,end,turns,sum,distilled}}` | tmp+rename 原子写; 可从流水重建 |
| `facts.json` | 结构化事实 `{k,v,ts,mid}` | tmp+rename 原子写 |

会话切分: 距上一条 >30 分钟自动开新会话。

## 核心 API (store.ChatStore)

- `append(role, text)` — 写入, 自动切会话, O(1)（内存缓存直更）
- `recall(query)` — **离线召回**: bigram 重合度找相似旧问句及其回答, 无网无 API 可用
- `context(query, budget)` — **三层上下文**: 事实层 + 召回层 + 近窗层, 字符预算控制
- `distill()` — **持续迭代**: 未蒸馏会话 → 摘要 + 规则抽事实, 写回 facts/sessions;
  `distill_fn` 参数可注入 API 版蒸馏（正式版接 GLM）
- `import_legacy(path)` — 迁移旧 zhizhi_memory.json
- `stats()` / `flush_sessions()`

## 触发式接入（合成时）

桌宠 `_call_ds` 改造点:
1. system prompt ← `store.context(user_msg)`（替代 `chat_history[-40:]`）
2. 回复后 `store.append("user", ...)` + `store.append("assistant", ...)`
3. API 失败/超时/无 Key → `store.recall(user_msg)` 离线回声（"翻小本本"）
4. 空闲/定时 → `store.distill()`（或妈妈在 OpenClaw 侧远程蒸馏）
5. AI 冒话（react/music 等事件）也 `append`，对话可被事件触发并接续

## 结构体分离契约（重点）

**引擎与主程序三重分离, 桌宠随便迭代互不干扰：**
1. 目录分离: 独立 `_beta_mem/`, 不进主程序代码
2. 代码分离: store.py 零依赖(纯标准库), 不 import 桌宠任何东西
3. 数据分离: 独立 `data/`, 桌宠打补丁/备份/回滚碰不到它

**对接模式(合成时二选一):**
- A. import 常驻(推荐, 桌宠内高频调用): `sys.path.append(._beta_mem路径)` + `from store import ChatStore`, 单例常驻, 写读都是函数调用零开销
- B. CLI 子进程(外部程序/兜底): `python store.py stats|recall|context|distill|append --dir <data目录>`, 任何程序不 import 也能用

**接口稳定承诺: 桌宠侧只需要这5个 API(或对应CLI), 引擎内部怎么改都不影响主程序:**
`append` / `recall` / `context` / `distill` / `stats`

**新事件零改动接入(PATCH19部位触摸/未来任何新功能):**
```python
# 桌宠侧新增事件后, 只多这一行, 引擎不用改:
store.append("assistant", "[触摸:头]" + ai_reply)   # 建议带事件标签前缀
# 之后爸爸问"摸头", recall/context 自动能找回当时小芷芷说了什么;
# 蒸馏时还能沉淀成 facts(如"小芷芷喜欢被摸头")
```

## 测试 (test_store.py, 8/8 PASS 2026-10-28)

T1 写入+会话切分 / T2 离线召回(命中+不误召回) / T3 三层上下文预算
/ T4 蒸馏幂等 / T5 崩溃容错(截断行+粘连行) / T6 双线程并发400条无丢
/ T7 旧记忆迁移40条 / T8 千条压测 write=470ms recall=3ms

复跑: `D:\软件\大肥鱼桌宠\.venv\Scripts\python.exe _beta_mem\test_store.py`
持久化实战(test_endurance.py, 8/8): 持续写3000组无衰减(1.07x) / 重启后数据完整续写正常 / 子进程CLI跨进程stats+recall+context+distill全通
召回回归(test_recall.py, 6/6): 正常召回/不误召回/短词隔词(摸头)/两字词/单字query/原文query

## 整合状态: 已合成进主程序 (PATCH23_V1, 2026-10-28 01:07, 备份.bak_p23mem_0103)

5个接入点全部落地, 均带回退路径(引擎缺失时自动退回旧40条窗口逻辑):
1. `__init__`: 引擎加载 + 旧 zhizhi_memory.json 一次性自动迁移(迁完改名 .migrated) + 每小时蒸馏 QTimer
2. `_call_ds`: system 注入 `[记忆检索]` 三层上下文(budget=1600) 替代 `chat_history[-40:]`
3. 回复成功: user+assistant 成对 append 入库(永不丢)
4. 无Key/超时/断网: `_mem_recall_echo` 离线回声(翻小本本)
5. 事件冒话(戳/歌/摸/通话): 成对入史 user侧`[触摸:x]（爸爸触发）` + assistant侧`[标签] 台词`, recall可召回

验证: py_compile OK + SMOKE 4/4 + 回归 8/8 + 召回 6/6
生效条件: 重启桌宠(PATCH19~23一起加载); 首启自动迁移旧记忆

## 历史拍板记录

- [x] 结构 OK → 已合成进主程序(PATCH23_V1, 见上)
- [ ] 蒸馏用规则版够不够, 还是接 GLM flash(现为规则版, distill_fn 已留插口)
- [ ] facts 的规则抽取模式要不要再加(现在: 喜欢/不喜欢/是判断)
