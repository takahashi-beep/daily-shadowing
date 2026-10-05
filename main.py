import base64
from datetime import datetime, timedelta, timezone
import html
import os
import random
import re
from gtts import gTTS
from openai import OpenAI
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

# 1. OpenAI クライアント初期化
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# 日本時間の現在日付・タイムスタンプ取得
jst = timezone(timedelta(hours=9))
now = datetime.now(jst)
date_str = now.strftime('%Y-%m-%d')
timestamp = int(now.timestamp())

# GitHub Pages 用の URL 構築
repo = os.environ.get('GITHUB_REPOSITORY', '')
user_name = repo.split('/')[0] if '/' in repo else ''
repo_name = repo.split('/')[1] if '/' in repo else ''
base_url = f'https://{user_name}.github.io/{repo_name}/' if repo else ''
page_url = f'{base_url}?v={timestamp}' if base_url else 'Local Test'

# 2. アクセント選択
ACCENTS = {
    'インド': {'tld': 'co.in', 'lang': 'en'},
    'シンガポール': {'tld': 'com.sg', 'lang': 'en'},
    'フィリピン': {'tld': 'com.ph', 'lang': 'en'},
    '英国': {'tld': 'co.uk', 'lang': 'en'},
    'オーストラリア': {'tld': 'com.au', 'lang': 'en'},
}

selected_country = random.choice(list(ACCENTS.keys()))
accent_info = ACCENTS[selected_country]

# 3. プロンプト定義と生成
prompt = f"""
あなたは科学技術スタートアップの創業コンサルタント兼、英語教育の専門家です。
以下の条件に従って、シャドーイング練習用の英語スクリプトと単語解説を作成してください。

### 条件：
1. **テーマ**: 科学技術分野のスタートアップによる1分間の投資家向けピッチ。
2. **ビジネス要素の強化**: 解決する課題、ビジネスモデル、市場規模、参入障壁、現在の実績、資金使途を含める。
3. **語数・難易度**: 150〜180語程度。CEFR B2〜C1レベル。
4. **アクセント指定**: 今回のアジア・多国籍パートは「{selected_country}」を指定して作成してください。
5. **注釈（単語リスト）**: 高校レベルを超える英単語やビジネス・専門用語（5〜8個）を抽出。

### 出力フォーマット：
---
【今日のアクセント指定】
{selected_country}

【Pitch Script】
(ここに150〜180語の英語本文)

【Vocabulary & Key Phrases】
1. [単語] (発音記号) : 日本語訳
   - 解説: (簡潔な補足説明)

【日本語訳】
(本文の自然な日本語訳)
---
"""

response = client.chat.completions.create(
    model='gpt-4o', messages=[{'role': 'user', 'content': prompt}]
)

generated_text = response.choices[0].message.content

# 4. 【Pitch Script】の本文のみ抽出
pitch_match = re.search(
    r'【Pitch Script】\s*\n(.*?)(?=\n\s*【Vocabulary|\Z)', generated_text, re.DOTALL
)

if pitch_match:
  pitch_script = pitch_match.group(1).strip()
else:
  try:
    start = generated_text.index('【Pitch Script】') + len('【Pitch Script】')
    end = generated_text.index('【Vocabulary')
    pitch_script = generated_text[start:end].strip()
  except ValueError:
    pitch_script = generated_text

# 5. 音声合成＆MP3結合（公開用フォルダ public へ出力）
os.makedirs('public', exist_ok=True)

gTTS(text='First, Standard American accent.', lang='en', tld='com').save(
    'part1_intro.mp3'
)
gTTS(text=pitch_script, lang='en', tld='com').save('part1_script.mp3')
gTTS(
    text=f'Next, {selected_country} accent.', lang='en', tld='com'
).save('part2_intro.mp3')
gTTS(text=pitch_script, lang='en', tld=accent_info['tld']).save(
    'part2_script.mp3'
)

audio_filename = f'audio_{date_str}.mp3'
audio_path = f'public/{audio_filename}'
parts = [
    'part1_intro.mp3',
    'part1_script.mp3',
    'part2_intro.mp3',
    'part2_script.mp3',
]

with open(audio_path, 'wb') as outfile:
  for p in parts:
    with open(p, 'rb') as infile:
      outfile.write(infile.read())

# バックアップとして最新用audio.mp3も保存
with open('public/audio.mp3', 'wb') as outfile:
  with open(audio_path, 'rb') as infile:
    outfile.write(infile.read())

# 6. HTML（キャッシュ対策・速度切り替えボタン付きWebページ）の作成
html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>Daily Shadowing App ({date_str})</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
  .card {{ background: #fff; padding: 24px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 20px; }}
  .tag {{ display: inline-block; background: #e3f2fd; color: #0d47a1; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 0.9em; }}
  .date-badge {{ font-size: 0.85em; color: #6c757d; margin-left: 8px; }}
  
  .sticky-player {{ position: sticky; top: 10px; z-index: 100; background: #212529; color: #fff; padding: 16px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); margin-bottom: 24px; }}
  .player-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
  .player-title {{ font-weight: bold; font-size: 0.9em; color: #adb5bd; }}
  
  .speed-controls {{ display: flex; gap: 6px; }}
  .speed-btn {{ background: #343a40; color: #fff; border: 1px solid #495057; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 0.85em; transition: all 0.2s; }}
  .speed-btn:hover {{ background: #495057; }}
  .speed-btn.active {{ background: #0d6efd; border-color: #0d6efd; font-weight: bold; }}
  
  audio {{ width: 100%; }}
  h2 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 6px; font-size: 1.25em; margin-top: 0; }}
  .script-text {{ font-size: 1.15em; line-height: 1.8; color: #212529; white-space: pre-wrap; }}
  .vocab-list {{ white-space: pre-wrap; font-size: 0.95em; background: #f1f3f5; padding: 16px; border-radius: 8px; }}
</style>
</head>
<body>

<div class="card">
  <h1>🎧 Daily Shadowing</h1>
  <span class="tag">アクセント: 標準アメリカ ＆ {selected_country}</span>
  <span class="date-badge">📅 {date_str}</span>
</div>

<div class="sticky-player">
  <div class="player-header">
    <div class="player-title">PLAYER</div>
    <div class="speed-controls">
      <button class="speed-btn" onclick="setSpeed(0.8, this)">0.8x</button>
      <button class="speed-btn active" onclick="setSpeed(1.0, this)">1.0x</button>
      <button class="speed-btn" onclick="setSpeed(1.2, this)">1.2x</button>
      <button class="speed-btn" onclick="setSpeed(1.5, this)">1.5x</button>
    </div>
  </div>
  <audio id="audio-player" controls src="{audio_filename}?v={timestamp}" autoplay></audio>
</div>

<div class="card">
  <h2>Pitch Script (原稿)</h2>
  <div class="script-text">{html.escape(pitch_script)}</div>
</div>

<div class="card">
  <h2>全文テキスト＆注釈・解説</h2>
  <div class="vocab-list">{html.escape(generated_text)}</div>
</div>

<script>
  function setSpeed(rate, btn) {{
    const audio = document.getElementById('audio-player');
    audio.playbackRate = rate;
    
    document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }}
</script>

</body>
</html>
"""

# トップページ用 (index.html) の書き出し
with open('public/index.html', 'w', encoding='utf-8') as f:
  f.write(html_content)

# 7. メール送信（パラメータ付きURLでキャッシュ回避）
email_body = f"""本日のシャドーイング教材が更新されました！

以下の専用Webページを開くと、音声を再生（速度変更機能つき）しながらスクリプトをスムーズに閲覧できます。

👉 今日の学習ページを開く:
{page_url}

---
【メール版テキスト】
{generated_text}
"""

message = Mail(
    from_email=os.environ.get('FROM_EMAIL'),
    to_emails=os.environ.get('TO_EMAIL'),
    subject=(
        f'【Daily Shadowing】標準アメリカ英語 ＆ {selected_country}アクセント'
    ),
    plain_text_content=email_body,
)

with open(audio_path, 'rb') as f:
  data = f.read()

message.attachment = Attachment(
    FileContent(base64.b64encode(data).decode()),
    FileName('shadowing_pitch.mp3'),
    FileType('audio/mpeg'),
    Disposition('attachment'),
)

sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
sg.send(message)

print('Webサイト生成＆メール送信が完了しました！')
