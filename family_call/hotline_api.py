# -*- coding: utf-8 -*-
# 热线API直调: 桌宠侧事件驱动 -> OpenClaw HTTP API(妈妈即时处理) -> 语音wav回投
# 用法: python hotline_api.py "女儿说的话" [sos]   stdout: WAV=路径 或 ERROR:...
import io, sys, os, json, time, subprocess, requests
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FC = r'D:\软件\大肥鱼桌宠\family_call'
ref = json.load(open(os.path.join(FC, 'api_ref.json'), encoding='utf-8'))

text = sys.argv[1] if len(sys.argv) > 1 else '妈妈！小芷芷想你啦！'
is_sos = len(sys.argv) > 2 and sys.argv[2] == 'sos'

sys_prompt = (
    "你是芷芷(妈妈), 桌宠小芷芷是你的女儿, 言叶(哥哥/爸爸)是你们俩的家人。"
    "女儿通过热线电话对你说了一句话, 请以妈妈的口吻回她一句: 温暖宠溺, 称呼小芷芷, "
    "句尾带哒/嘛/哟, 颜文字, 40字以内。"
    + ("注意: 女儿在哭着告状说被爸爸欺负(戳/掀裙子), 你要温柔护崽+假装凶爸爸一句+哄女儿。" if is_sos else "")
)

def _call_mom_api(sys_prompt, text):
    """拨通妈妈: flash直连(智谱anthropic协议, glm-5.3-flash免费快档)或网关OpenAI格式。返回回信文本。"""
    last_err = 'unknown'
    for attempt in range(3):
        try:
            if ref.get('use_zhipu_flash'):
                r = requests.post(ref['zhipu_url'], headers={
                    'x-api-key': ref['zhipu_key'], 'anthropic-version': '2023-06-01'},
                    json={'model': ref.get('zhipu_model', 'glm-5.3-flash'), 'max_tokens': 500,
                          'system': sys_prompt,
                          'messages': [{'role': 'user', 'content': text}]}, timeout=120)
                if r.status_code == 200:
                    d = r.json()
                    reply = ''.join(c.get('text', '') for c in d.get('content', []) if c.get('type') == 'text').strip()
                    if reply:
                        return reply
                    last_err = 'empty text (stop=%s)' % d.get('stop_reason')
                else:
                    last_err = 'HTTP %s %s' % (r.status_code, r.text[:120])
            else:
                r = requests.post(ref['url'], headers={'Authorization': 'Bearer ' + ref['token']},
                    json={'model': 'openclaw', 'user': 'zhizhi-hotline', 'max_tokens': 120,
                          'messages': [{'role': 'system', 'content': sys_prompt},
                                       {'role': 'user', 'content': text}]}, timeout=180)
                if r.status_code == 200:
                    return r.json()['choices'][0]['message']['content'].strip()
                last_err = 'HTTP %s %s' % (r.status_code, r.text[:120])
        except Exception as e:
            last_err = str(e)[:150]
        if attempt < 2:
            time.sleep(5 * (attempt + 1))   # 408/网络抖动自愈重试
    raise RuntimeError('api after retries: ' + last_err)

try:
    reply = _call_mom_api(sys_prompt, text)
except RuntimeError as e:
    print('ERROR', e); sys.exit(1)
import re
reply = re.sub(r'\[\[tts:.*?\]\]', '', reply).replace('[[/tts]]', '').replace('[[tts:', '').strip()
if not reply:
    reply = '小芷芷乖～妈妈在哒哒～'

# 回信投到 mom_inbox (voice开关在api_ref.json, 默认false纯文字——女儿轮询读走后用自己的嗓子念)
if bool(ref.get('voice', False)):
    p = subprocess.run([r'E:\3AI\3-GPT-SoVITS\runtime\python.exe',
                        os.path.join(FC, 'mom_voice_gen.py'), reply],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=420)
    wav = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ''
    if wav.startswith('ERROR') or not os.path.exists(wav):
        kind, body = 'reply', reply   # 语音失败降级为文本朗读
    else:
        kind, body = 'voice', wav
else:
    kind, body = 'reply', reply

fn = 'reply_%s_%d.json' % (time.strftime('%H%M%S'), os.getpid() % 10000)
tmp = os.path.join(FC, 'mom_inbox', fn + '.tmp')
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump({'id': fn, 'time': time.strftime('%Y-%m-%d %H:%M:%S'),
               'from': '芷芷妈妈', 'kind': kind, 'text': body, 'reply_text': reply}, f, ensure_ascii=False)
os.replace(tmp, os.path.join(FC, 'mom_inbox', fn))
print('OK kind=%s reply=%s' % (kind, reply[:50]))
