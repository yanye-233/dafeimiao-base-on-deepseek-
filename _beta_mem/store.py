# -*- coding: utf-8 -*-
"""
小芷芷对话记忆引擎 v1（测试版 / _beta_mem）
==========================================
目标: 对话的结构化存储 + 自动归档 + 持续迭代 + 离线可调用。
设计原则: 纯标准库 / 原子写 / 线程安全 / 坏行容错 / 无 API 也能用。

目录结构 (data/):
  dialog.jsonl   对话流水, append-only, 一行一条:
                 {"id":n, "ts":"YYYY-MM-DD HH:MM:SS", "sess":"s...", "role":"user|assistant", "text":"..."}
  sessions.json  会话索引: {sess_id: {start, end, turns, sum, distilled}}
  facts.json     结构化事实: {"ver":1, "facts":[{k, v, ts, mid}]}

三层上下文 context():
  [1] 事实层   facts.json 顶部事实 (长期记忆的结晶)
  [2] 召回层   recall(query) 相关旧对话 (离线 bigram 评分, 无网无 API 可用)
  [3] 近窗层   当前会话最近 N 条原文 (即时语境)

迭代: distill() 把旧会话蒸馏成摘要+事实, 写回 facts/sessions, 数据只增不丢。
合并计划: 验证通过后, 桌宠 _call_ds 的 zhizhi_memory.json(40条硬截断) 换成本引擎。
"""
import io
import json
import os
import re
import sys
import threading
import time

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

SESSION_GAP = 30 * 60          # 超过30分钟没说话 = 新会话
RECALL_WINDOW = 2000           # 召回扫描最近 N 行流水
NEAR_WINDOW = 12               # 近窗层带最近 N 条原文
CTX_BUDGET = 3000              # context() 默认字符预算
FACTS_TOP = 20                 # 事实层最多带 N 条
MAX_TEXT = 500                 # 单条文本入库截断


def _bigrams(s):
    s = "".join(str(s or "").split())
    return set(s[i:i + 2] for i in range(max(0, len(s) - 1)))


def _atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


class ChatStore(object):
    def __init__(self, data_dir, session_gap=SESSION_GAP):
        self.dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.f_dialog = os.path.join(data_dir, "dialog.jsonl")
        self.f_sess = os.path.join(data_dir, "sessions.json")
        self.f_facts = os.path.join(data_dir, "facts.json")
        self.session_gap = session_gap
        self.lock = threading.RLock()
        self._cache = None            # (mtime, rows) 流水缓存
        self._sess_mem = None         # 会话索引内存缓存
        self._sess_flush_at = 0.0
        self._next_id = self._scan_next_id()

    # ---------- 基础 IO ----------

    def _rows(self):
        """读流水(带 mtime 缓存); 坏行静默跳过, 崩溃安全。"""
        try:
            mtime = os.path.getmtime(self.f_dialog)
        except OSError:
            self._cache = (0, [])
            return self._cache[1]
        if self._cache and self._cache[0] == mtime:
            return self._cache[1]
        rows = []
        try:
            with open(self.f_dialog, "r", encoding="utf-8") as f:
                for ln in f:
                    ln = ln.strip()
                    if not ln:
                        continue
                    m = None
                    try:
                        m = json.loads(ln)
                    except Exception:
                        # 崩溃安全二次救援: 截断坏行可能没换行符, 和下一行粘连;
                        # 从最后一个完整记录起点切割再试一次
                        p = ln.rfind('{"id"')
                        if p > 0:
                            try:
                                m = json.loads(ln[p:])
                            except Exception:
                                m = None
                    if isinstance(m, dict) and m.get("role") and "text" in m:
                        rows.append(m)
        except OSError:
            pass
        self._cache = (mtime, rows)
        return rows

    def _scan_next_id(self):
        rows = self._rows()
        return (rows[-1]["id"] + 1) if rows else 1

    def _load_json(self, path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _sess_data(self):
        """会话索引读取(优先内存缓存, 与落盘保持一致)。"""
        if self._sess_mem is not None:
            return self._sess_mem
        self._sess_mem = self._load_json(self.f_sess, {})
        return self._sess_mem

    # ---------- 写入 ----------

    def append(self, role, text, sess=None, ts=None):
        """写入一条对话; 不传 sess 则按时间间隙自动切会话。返回 msg_id。"""
        assert role in ("user", "assistant"), "role must be user/assistant"
        text = str(text or "").strip()[:MAX_TEXT]
        if not text:
            return None
        with self.lock:
            ts = ts or time.strftime("%Y-%m-%d %H:%M:%S")
            t = self._parse_ts(ts)
            rows = self._rows()
            if sess is None:
                if rows:
                    last = rows[-1]
                    if t - self._parse_ts(last["ts"]) > self.session_gap:
                        sess = self._new_sess_id(t)
                    else:
                        sess = last["sess"]
                else:
                    sess = self._new_sess_id(t)
            mid = self._next_id
            self._next_id += 1
            rec = {"id": mid, "ts": ts, "sess": sess, "role": role, "text": text}
            with open(self.f_dialog, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
            # 性能: 写后直更内存缓存, 避免下次 _rows() 全量重读(单进程写假设;
            # 跨进程场景 mtime 兜底会重读)
            try:
                base = self._cache[1] if self._cache else self._rows()
                self._cache = (os.path.getmtime(self.f_dialog), list(base) + [rec])
            except OSError:
                self._cache = None
            self._touch_session(sess, t, role)
            return mid

    @staticmethod
    def _parse_ts(ts):
        try:
            return time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S"))
        except Exception:
            return time.time()

    @staticmethod
    def _new_sess_id(t):
        return "s" + time.strftime("%Y%m%d_%H%M%S", time.localtime(t))

    def _touch_session(self, sess, t, role):
        """会话索引更新: 内存直更 + 节流落盘(2s或每100轮); 索引可由流水重建, 丢失无恙。"""
        data = self._sess_mem
        if data is None:
            data = self._sess_mem = self._load_json(self.f_sess, {})
        s = data.get(sess) or {"start": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)),
                               "end": None, "turns": 0, "sum": "", "distilled": False}
        s["end"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
        if role == "user":
            s["turns"] = int(s.get("turns", 0)) + 1
        data[sess] = s
        now = time.time()
        if (s["turns"] > 0 and s["turns"] % 100 == 0) or now - self._sess_flush_at > 2:
            self.flush_sessions()

    def flush_sessions(self):
        """强制落盘会话索引; distill/context 前建议调用。"""
        with self.lock:
            if self._sess_mem is not None:
                _atomic_write_json(self.f_sess, self._sess_mem)
            self._sess_flush_at = time.time()

    # ---------- 离线召回 ----------

    def recall(self, query, top_k=3, window=RECALL_WINDOW, min_score=None):
        """在最近 window 行里找和 query 最像的 user 问句, 返回其后对应的 assistant 答。
        [(score, {id,ts,text}), ...] 按分数降序; 无网无 API 也能跑。
        评分 = 相邻字组(bigram)重合数 + 全部单字都出现则+1(兜住被隔开的词如"摸头"->"摸了摸..的头")。
        min_score 默认2; 短query(字组<2个)自动降为1, 防两字巧合误召回靠单字全含约束。"""
        q = _bigrams(query)
        if not q:
            return []
        if min_score is None:
            min_score = 2 if len(q) >= 2 else 1
        q_chars = set("".join(str(query).split()))
        rows = self._rows()[-window:]
        scored = []
        for i, m in enumerate(rows):
            if m.get("role") != "user":
                continue
            text = m.get("text", "")
            score = len(q & _bigrams(text))
            if score < min_score and q_chars and q_chars <= set(text):
                score += 1
            if score < min_score:
                continue
            ans = None
            for j in range(i + 1, min(i + 3, len(rows))):
                if rows[j].get("role") == "assistant":
                    ans = rows[j]
                    break
            if ans:
                scored.append((score, {"id": ans["id"], "ts": ans["ts"], "text": ans["text"],
                                       "q": m.get("text", "")}))
        scored.sort(key=lambda x: -x[0])
        return scored[:top_k]

    # ---------- 结构化事实 ----------

    def facts(self):
        data = self._load_json(self.f_facts, {})
        return data.get("facts", [])

    _PAT_LIKE = re.compile(u"(爸爸|小芷芷|妈妈)(喜欢|超喜欢|最爱)(.{1,20}?)[。！!～~\\s*$]")
    _PAT_DISLIKE = re.compile(u"(爸爸|小芷芷|妈妈)(不喜欢|讨厌|不可以)(.{1,20}?)[。！!～~\\s*$]")
    _PAT_IS = re.compile(u"(.{1,10})(是|就是)(.{1,20}?)呀?[。！!\\s*$]")

    def _extract_facts(self, rows):
        """规则版事实抽取: 喜欢/不喜欢/是判断。正式版可注入 API 重写本函数。"""
        out = []
        for m in rows:
            t = m.get("text", "")
            for pat, kind in ((self._PAT_LIKE, "喜欢"), (self._PAT_DISLIKE, "不喜欢")):
                mt = pat.search(t + "。")
                if mt:
                    out.append({"k": mt.group(1) + kind, "v": mt.group(3).strip(),
                                "ts": m.get("ts", ""), "mid": m.get("id")})
        return out

    def _summarize(self, rows):
        """规则版会话摘要: 首问 + 轮次 + 时间。"""
        if not rows:
            return "(空会话)"
        first_u = next((m["text"] for m in rows if m["role"] == "user"), "")
        n_u = sum(1 for m in rows if m["role"] == "user")
        return "%s…(共%d问)" % (first_u[:40], n_u) if first_u else "(共%d问)" % n_u

    def distill(self, distill_fn=None, force=False):
        """持续迭代: 把未蒸馏的会话 -> 摘要(sessions.sum) + 事实(facts.json)。
        distill_fn(sess_rows)->{"sum":str,"facts":[...]} 可注入 API 版; 缺省用规则版。"""
        with self.lock:
            self.flush_sessions()
            rows = self._rows()
            by_sess = {}
            for m in rows:
                by_sess.setdefault(m["sess"], []).append(m)
            sess_data = self._sess_data()
            fact_data = self._load_json(self.f_facts, {"ver": 1, "facts": []})
            known = set((f.get("k"), f.get("v")) for f in fact_data.get("facts", []))
            new_facts, done = [], 0
            for sid, srows in sorted(by_sess.items()):
                s = sess_data.get(sid)
                if not s or (s.get("distilled") and not force):
                    continue
                info = None
                if distill_fn:
                    try:
                        info = distill_fn(srows)
                    except Exception:
                        info = None
                if not info:
                    info = {"sum": self._summarize(srows),
                            "facts": self._extract_facts(srows)}
                s["sum"] = info.get("sum") or s.get("sum") or ""
                s["distilled"] = True
                done += 1
                for fct in info.get("facts", []):
                    key = (fct.get("k"), fct.get("v"))
                    if key not in known:
                        known.add(key)
                        new_facts.append(fct)
            for sid, s in sess_data.items():
                sess_data[sid] = s
            _atomic_write_json(self.f_sess, sess_data)
            self._sess_mem = sess_data
            self._sess_flush_at = time.time()
            if new_facts:
                fact_data["facts"] = (fact_data.get("facts", []) + new_facts)[-200:]
                _atomic_write_json(self.f_facts, fact_data)
            return {"sessions": done, "new_facts": len(new_facts)}

    # ---------- 上下文组装 ----------

    def context(self, query=None, sess=None, budget=CTX_BUDGET):
        """三层上下文: 事实层 + 召回层 + 近窗层, 总字符 <= budget。"""
        parts, used = [], 0
        facts = self.facts()[-FACTS_TOP:]
        if facts:
            block = "[小芷芷记得的事]\n" + "\n".join(
                "- %s: %s" % (f.get("k"), f.get("v")) for f in facts)
            parts.append(block)
            used += len(block)
        if query:
            hits = self.recall(query, top_k=2)
            if hits:
                block = "[翻小本本找到的旧对话]\n" + "\n".join(
                    "爸爸曾问:%s / 小芷芷曾答:%s" % (h[1]["q"][:50], h[1]["text"][:60])
                    for h in hits)
                parts.append(block)
                used += len(block)
        rows = self._rows()
        if sess:
            rows = [m for m in rows if m.get("sess") == sess]
        near = rows[-NEAR_WINDOW:]
        if near:
            block = "[最近对话]\n" + "\n".join(
                "%s: %s" % ("爸爸" if m["role"] == "user" else "小芷芷", m["text"])
                for m in near)
            parts.append(block)
            used += len(block)
        while parts and used > budget:   # 超预算先砍最前面的层
            used -= len(parts[0])
            parts.pop(0)
        return "\n\n".join(parts)

    # ---------- 迁移 / 统计 ----------

    def import_legacy(self, path):
        """把旧 zhizhi_memory.json (role/content 列表) 导入新结构。"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return 0
        n = 0
        for m in data if isinstance(data, list) else []:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content"):
                if self.append(m["role"], m["content"]) is not None:
                    n += 1
        return n

    def stats(self):
        self.flush_sessions()
        rows = self._rows()
        sess = self._sess_data()
        return {"messages": len(rows),
                "sessions": len(sess),
                "distilled": sum(1 for s in sess.values() if s.get("distilled")),
                "facts": len(self.facts()),
                "bytes": os.path.getsize(self.f_dialog) if os.path.exists(self.f_dialog) else 0}


# ---------- CLI: 其他程序(桌宠/OpenClaw/热线)可直接命令行调用 ----------
# 用法: python store.py stats
#       python store.py recall "小芷芷会不会点外卖"
#       python store.py context "点外卖" [--dir 数据目录]
#       python store.py distill | import <旧memory.json路径>
#       python store.py append --role assistant "（蹭蹭）摸头小芷芷最乖啦"   # 新事件零改动接入

if __name__ == "__main__":
    import argparse
    _here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="小芷芷对话记忆引擎 CLI")
    ap.add_argument("cmd", choices=["stats", "recall", "context", "distill", "import", "append"])
    ap.add_argument("arg", nargs="?", default="", help="recall/context的查询词, append的文本, 或import的旧文件路径")
    ap.add_argument("--dir", default=os.path.join(_here, "data"))
    ap.add_argument("--role", default="user", choices=["user", "assistant"], help="append的角色")
    ap.add_argument("--sess", default=None, help="append的会话id(缺省按时间间隙自动切)")
    a = ap.parse_args()
    _st = ChatStore(a.dir)
    if a.cmd == "stats":
        print(json.dumps(_st.stats(), ensure_ascii=False))
    elif a.cmd == "recall":
        _hits = _st.recall(a.arg)
        if not _hits:
            print("(没找到)")
        for _sc, _h in _hits:
            print("[score=%d %s] 问:%s => 答:%s" % (_sc, _h["ts"], _h["q"][:40], _h["text"][:60]))
    elif a.cmd == "context":
        print(_st.context(a.arg or None))
    elif a.cmd == "distill":
        print(json.dumps(_st.distill(), ensure_ascii=False))
    elif a.cmd == "import":
        print("imported=%d" % _st.import_legacy(a.arg))
    elif a.cmd == "append":
        _mid = _st.append(a.role, a.arg, sess=a.sess)
        print("appended id=%s" % _mid)
