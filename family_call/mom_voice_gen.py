# -*- coding: utf-8 -*-
# 妈妈语音生成器(接线员调用): 读tts_ref.json配置 -> 9880生成wav -> stdout输出wav绝对路径
# 用法: python mom_voice_gen.py "要说的话"   成功输出wav路径, 失败输出ERROR开头
import io, sys, os, json, time, requests
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FC = r'D:\软件\大肥鱼桌宠\family_call'
API = 'http://127.0.0.1:9880'

try:
    cfg = json.load(open(os.path.join(FC, 'tts_ref.json'), encoding='utf-8'))
except Exception as e:
    print('ERROR no tts_ref.json:', e); sys.exit(1)

text = sys.argv[1] if len(sys.argv) > 1 else '小芷芷～妈妈在哦'
statef = os.path.join(FC, 'tts_state.json')
try:
    state = json.load(open(statef, encoding='utf-8'))
except Exception:
    state = {}

try:
    # 模型与上次不同才热切(省10-20s加载), 重启TTS服务后请删tts_state.json或手动对齐
    if state.get('gpt') != cfg['gpt'] or state.get('sovits') != cfg['sovits']:
        r = requests.post(API + '/set_model', json={
            'gpt_model_path': cfg['gpt'], 'sovits_model_path': cfg['sovits']}, timeout=240)
        if r.json().get('code') != 0:
            print('ERROR set_model:', r.text[:200]); sys.exit(1)
        json.dump({'gpt': cfg['gpt'], 'sovits': cfg['sovits']}, open(statef, 'w', encoding='utf-8'))
        time.sleep(4)
    r = requests.post(API + '/change_refer', json={
        'refer_wav_path': cfg['refer'], 'prompt_text': cfg['prompt_text'],
        'prompt_language': cfg['prompt_lang']}, timeout=30)
    if r.json().get('code') != 0:
        print('ERROR change_refer:', r.text[:200]); sys.exit(1)
    g = requests.post(API + '/', json={
        'text': text, 'text_language': 'zh', 'cut_punc': '。？！；：…，'}, timeout=360)
    if len(g.content) < 2000:
        print('ERROR tts too small:', len(g.content), g.content[:60]); sys.exit(1)
    out = os.path.join(FC, 'voice', 'mom_%s_%d.wav' % (time.strftime('%H%M%S'), os.getpid() % 10000))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'wb').write(g.content)
    print(out)
except Exception as e:
    print('ERROR:', e); sys.exit(1)
