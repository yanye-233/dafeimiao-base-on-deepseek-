# 大肥鱼桌宠 · 小芷芷增强版 🐋

DeepSeek 社区二创形象「鲸鱼娘 · 大肥鱼」的 Windows 桌面宠物。
在 [RYANFFY/deepseek-dafeiyu-pet](https://github.com/RYANFFY/deepseek-dafeiyu-pet) 的基础上，
**并入了 [1190fasheqi/dafeiyu-pet](https://github.com/1190fasheqi/dafeiyu-pet) 的三项功能**，
新增「跟着 DSH 干活」的立绘联动，并加入自定义角色**「小芷芷」**：
**像素级触摸分区、母女热线、跨会话记忆、AI 对话兜底**。

![大肥鱼](sprites/dsh/working/1_306.png)
![小芷芷](sprites/正面_306.png)
<img width="1792" height="2400" alt="Imag" src="https://github.com/user-attachments/assets/d467fa11-8e3f-4bd1-adbf-28f1a4f14e8a" />
---

## 这个版本做了什么

| 部分 | 说明 |
|---|---|
| **底子** | RYANFFY/deepseek-dafeiyu-pet —— 含 DSH 小鲸鱼余额挂件的能力 |
| **并入** | 1190fasheqi/dafeiyu-pet 的三项：**AI 对话 / 喂食 / 系统监控** |
| **新增** | **DSH 联动**：11 个动作跟着 DeepSeek Harness 干活实时换立绘 |
| **新增** | 天气按时段播报、放歌换立绘、思考中姿势、13 页设置窗口 |
| **换装** | **自定义角色「小芷芷」**：全套三视图立绘 + 皮肤库机制（`skin_library`） |
| **新增** | **触摸分区**：labelme 手工标注 → 像素掩膜，摸到哪里都有对应台词 |
| **新增** | **母女热线**：小芷芷可以打电话给 OpenClaw 里的「妈妈」，GPT-SoVITS 语音 |
| **新增** | **记忆系统**：跨会话对话记忆（`_beta_mem/`） |
| **新增** | **AI 对话兜底**：DeepSeek 不可用时自动切换 Kimi |

抛砖引玉，感觉桌宠联合DSH还能干很多，但是自己第一次搞都是ds带着弄。

---

## 功能

### 🐟 桌宠本体

- 三视图形象（正面 / 侧面 / 背面），**自由散步 / 跟随鼠标 / 原地待着**
- 拖拽、屏幕边缘吸附、左吸附翻面、Q 弹按压、点击音效
- 置顶 / 置底 / 透明度 / **尺寸五档**（迷你 / 特小 / 小 / 中 / 大）
- 全局快捷键、实时天气、闲置语录、离开返回提醒、**免打扰**
- 可换形象、可上传自己的图（皮肤库 `skin_library`，内置小芷芷皮肤）

### 💰 DeepSeek 联动

- 余额 / 今日已用 / **峰谷时段**（高峰价是空闲价的两倍）/ 每轮消耗统计
- **AI 对话**：跟桌宠聊天（走 DeepSeek API，每句 ≤25 字）
- **喂食**：小鱼干 / 蛋糕 / 棒棒糖 / 团子 / 钻石
- **系统监控**：CPU ≥90%、内存 ≥95%、NVIDIA 显卡 ≥80℃ 时提醒

### ★ DSH 联动

跟着 **DeepSeek Harness** 干活，实时换立绘 + 冒台词：

| 动作 | 触发时机 | 台词示例 |
|---|---|---|
| `start` 开工 | 一轮开始 | 「开工！看我的」 |
| `working` 思考中 | **正在深度思考（常驻）** | —— |
| `tool_pwsh` 敲命令 | 执行命令 | 「又在敲命令」 |
| `tool_edit` 改代码 | 改 / 写文件 | 「改代码啦，别眨眼」 |
| `tool_read` 翻文件 | 读文件、搜索 | 「翻文件呢」 |
| `tool_web` 上网查 | 搜索、抓网页 | 「上网查点东西」 |
| `approval` 等批准 | 有工具等你批准 | 「主人快点一下嘛…」 |
| `error` 报错 | 工具执行出错 | 「哎哟，出错了…」 |
| `done` 收工 | 一轮结束 | 「干完啦，收工！」 |
| `idle` 发呆 | 静默超过 120 秒 | 「没事干，我先睡会儿…」 |
| `sing` 放歌 | 音乐播放中 | —— |

**优先级**：`approval` > `error` > `start` > `done` > `tool_*` > 常态
（常态 = `working` 思考中 > `sing` 放歌 > 默认三视图）

**性能**：直接读本地 zstd 会话日志，做了**增量读取**（只解压新增的帧），
单次读取从 **452 ms 降到 0.3 ms**；轮询 0.7 秒，工具反应约 1 秒。

#### ⚠️ 隐私说明（重要）

`DSH 联动` 会读取你本机的：

```
%USERPROFILE%\.dsh\sessions\**\session.v4.jsonl.zstd
```

这是 **DeepSeek Harness 的本地会话日志**（含完整对话内容与工具调用记录）。

- **全程本地读取，不会上传任何数据**
- 但它是**你自己的对话记录**，介意的话：
  - 右键菜单或**设置 → DSH 联动**里一键关闭
  - 默认值在 `桌宠.py` 的 `DEFAULTS` 里改 `"dsh_link": False`

### 🫧 小芷芷 · 触摸分区（本版重点）

摸不同部位有不同的台词，识别是**像素级**的，不是矩形框：

- 用 [labelme](https://github.com/wkentaro/labelme) 在正面立绘上手工标注 **15 个身体分区**
  （嘴巴 / 脸颊 / 下巴 / 小手手 / 脚脚 / 小腿 / 手臂 / 猫耳 / 胸口 / 脸 / 头顶 …），
  保存为 `custom_zhizhi/zhizhi_front.json`
- 跑转换工具生成掩膜与分区表：

  ```bat
  python 工具\labelme2mask.py
  ```

  产出 `custom_zhizhi/zone_map.png`（分区掩膜）+ `zone_id_names.json`（分区对照表）
- **优先级**：`custom_zhizhi/zone_priority.json` 手动排序（小部位在前，避免被大分区盖住），
  没列出的标签按多边形面积升序自动排
- 点击时反查掩膜像素 → 精确知道摸的是哪里；透明像素不算命中
- 每个分区一个**台词池** `zone_lines.json`：最少被说的台词优先出场；
  AI 聊天里现编的合适应答会自动入池，越养越多
- 改了标注只需重跑转换脚本 + 重启桌宠，**不用改代码**

### 📞 小芷芷 · 母女热线（family_call/）

小芷芷可以主动「打电话」给住在 [OpenClaw](https://github.com/openclaw/openclaw) 里的
AI 妈妈（当然也可以是任何跑在别的进程里的角色）：

- **文件信箱机制**：`daughter_outbox/` ↔ `mom_inbox/` 两个目录互发 JSON 小纸条，
  OpenClaw 侧用定时任务值守转发（`family_call/hotline_api.py` 是值守脚本）
- 妈妈的回复经 **GPT-SoVITS** 合成语音播放（`family_call/tts_ref.json` 配音色与参考音频）
- 需要本机（或局域网）跑着 OpenClaw 网关与 GPT-SoVITS API
- 配置：复制 `family_call/api_ref.example.json` 为 `api_ref.json`，填上网关地址 / token /
  各家 API key（`api_ref.json` 已被 .gitignore 排除，不会入库）

### 🧠 小芷芷 · 记忆系统（_beta_mem/）

- 跨会话对话记忆：`dialog.jsonl`（对话流水）+ `sessions.json`（会话索引）
- 实现与测试详见 [`_beta_mem/README.md`](_beta_mem/README.md)
- 真实对话数据已通过 .gitignore 排除（`_beta_mem/data/`），入库的只有代码和合成测试数据

### 🔁 AI 对话兜底

- AI 对话优先走 DeepSeek（`config.json` 的 `ds_api_key`）
- DeepSeek 不可用时自动 fallback 到 **Kimi**（右键菜单也有手动入口）
- Kimi key 读取顺序：OpenClaw 配置文件（共享，不落盘到本项目）→
  环境变量 `KIMICODE_API_KEY` → `config.json`

---

## 环境要求

- **Windows 10 / 11**（用了系统媒体控制、窗口标题等 Windows 接口）
- **Python 3.10+**，推荐 **3.14**（DSH 联动的 zstd 读取用它自带的标准库）

> 低版本 Python 想要 DSH 联动的话：`pip install zstandard`

---

## 快速开始

```bat
:: 1. 建虚拟环境
python -m venv .venv

:: 2. 装依赖
.venv\Scripts\pip install -r requirements.txt

:: 3. 启动（也可以直接双击 启动桌宠.bat）
.venv\Scripts\pythonw 桌宠.py
```

首次运行会在程序目录自动生成 `config.json`。

---

## 配置 API Key

余额、天气、AI 对话都需要 DeepSeek 的 API Key：

**右键桌宠 →「设置…」→「余额和用量」→ 设置 Key**

Key 存在本地 `config.json` 里，**不会上传到任何地方**（除了调用 DeepSeek 官方接口）。
`config.json`、`family_call/api_ref.json` 等含 Key 的文件都已被 `.gitignore` 排除，
本项目仓库不含任何密钥；提交前脚本会再检查一遍。

> 官方计价：**空闲时段是高峰时段的一半**。
> 高峰 = 北京时间周一至周五 09:00–12:00 与 14:00–18:00（法定节假日除外）。

---

## 自定义立绘 / 动作

11 个动作各有自己的立绘，放在 `sprites\dsh\<动作名>\<帧>_<档位>.png`。
**没画的动作用三视图兜底，不会报错。**

### 加一张新动作图

1. 画图：**纯白底**、立绘完整不裁边
2. 命名（任选一种）：
   ```
   approval.png      approval-1.png      approval_1.png
   start-work1.png   ← start 的第 1 帧
   动作名-2.png       ← 该动作的第 2 帧
   ```
3. 丢进 `工具\源图\`
4. 跑生成工具：
   ```bat
   python 工具\make_frames.py
   ```
5. 重启桌宠

**尺寸、长宽比、抠图、缩放全自动**，不用管。

### 换成自己的角色（皮肤库）

在设置里把 `skin` 换成皮肤库里的角色即可（`config.json` 的 `skin_library`），
正/侧/背三张 PNG 指到自己的立绘就能换装；
小芷芷皮肤（`zhizhi-001`）自带触摸分区支持。

### 生成工具做了什么

1. **泛洪抠白底** —— 只抠「连到画布边缘」的浅色区域，
   所以**人物内部的白色（脸、头饰）不会被误删**（这是和"按颜色阈值抠图"的本质区别）
2. 裁到角色
3. **统一缩放**：角色高度 = 画布高 × 0.95，所有动作一致 → **切换不跳大小**
4. 生成三档：特小 122 / 中 245 / 大 306

详见 [`工具/说明.md`](工具/说明.md)。

---

## 设置窗口

右键桌宠 →「打开设置…」（或双击托盘图标），一共 **13 页**：

```
余额和用量 · 桌宠形象 · 控制台外观 · 动作和互动 · 天气和城市
音乐和歌词 · 文案和语录 · 音效 · 应用联动 · DSH 联动
性能和工具 · 通用 · 关于
```

**「DSH 联动」页**里有开关、调试日志开关，以及**「动作一览」**——
一眼看出哪张立绘画了、哪张还在用三视图兜底。

---

## 目录结构

```
├── 桌宠.py               主程序
├── ui_console.py         设置窗口
├── 启动桌宠.bat           双击启动
├── config.json           ← 首次运行自动生成（含 Key，别外传，已 gitignore）
├── config.example.json   配置模板
├── requirements.txt
├── assets/               图标、音效
├── sprites/              形象（大肥鱼 / 小芷芷 + dsh 动作立绘）
├── custom_zhizhi/        小芷芷立绘源 + 触摸分区
│   ├── zhizhi_front.json   labelme 标注（分区多边形）
│   ├── zone_map.png        分区掩膜（labelme2mask.py 生成）
│   ├── zone_priority.json  分区优先级（手动排序）
│   └── zone_id_names.json  分区号 ↔ 名称对照表
├── family_call/          母女热线（信箱 + 语音合成；api_ref.json 不入库）
├── _beta_mem/            记忆系统（beta，真实数据不入库）
├── zone_lines.json       触摸分区台词池（运行时自动扩充）
└── 工具/                 素材工具
    ├── make_frames.py    立绘 → 动作帧（自动抠图 + 统一尺寸）
    ├── labelme2mask.py   labelme 标注 → 触摸分区掩膜
    ├── 说明.md
    └── 源图/             原始立绘
```

---

## 署名与许可

### 代码

**MIT License** —— 见 [LICENSE](LICENSE)。

### 本项目基于

| 项目 | 作者 | 许可 |
|---|---|---|
| [deepseek-dafeiyu-pet](https://github.com/RYANFFY/deepseek-dafeiyu-pet) | RYANFFY | MIT |
| [dafeiyu-pet](https://github.com/1190fasheqi/dafeiyu-pet) | 1190fasheqi | MIT |
| [DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget) | MeteorNOX | MIT |
| 界面图标 | [Lucide](https://lucide.dev) | ISC |

原版说明文档见 [`原版说明.md`](原版说明.md)。

### ⚠️ 立绘形象

「鲸鱼娘 · 大肥鱼」是 **DeepSeek V4 Pro 的社区二创形象**（饭制作品），
**版权归 DeepSeek 及原作者所有**。
小芷芷立绘为 AI 生成 + 手工修整的自定义形象，仅供个人使用。

- 本项目中的立绘**仅供个人学习、交流使用，请勿用于商业用途**
- 若要商用，请先自行取得官方授权

---

## 常见问题

**Q：DSH 联动没反应？**
→ 设置 →「DSH 联动」→ 打开「记调试日志」，然后看程序目录下的 `dsh-debug.log`。
它会记录每次读到了什么。

**Q：它能读到我的哪些对话？**
→ 只读**最新修改的那一条** DSH 会话日志（本地文件），不会外传。

**Q：为什么 `error` 有时不触发？**
→ 目前只认 DSH 标记的 `isError`。**命令返回非零退出码不算**（已知限制）。

**Q：想让它别读日志？**
→ 设置 →「DSH 联动」→ 关掉；或右键菜单里关闭。

**Q：触摸分区不灵 / 点了没反应？**
→ ① 确认当前皮肤是带分区标注的角色（如小芷芷）；
② `zone_map.png` 要和当前正面立绘对应（改过立绘就重跑 `工具\labelme2mask.py`）；
③ 分区掩膜只对**正面**立绘生效。
**Q：母女热线怎么打不通？**
→ 检查 `family_call/api_ref.json` 是否填好、OpenClaw 网关与 GPT-SoVITS 是否在线、
值守任务是否在跑。

---

## 已知限制

- 仅支持 Windows
- `error` 动作只认 DSH 的 `isError` 标记，非零退出码不触发
- 放歌换立绘依赖系统媒体控制（SMTC），部分播放器可能读不到进度
- 触摸分区目前只支持正面立绘（侧面/背面用兜底逻辑）
- 立绘为社区二创，**请勿商用**
