import base64
from datetime import datetime, timedelta, timezone
import html
import json
import os
import random
import re
from gtts import gTTS
from openai import OpenAI
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    ClickTracking,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
    TrackingSettings,
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
prompt = f"あなたは科学技術スタートアップの創業コンサルタント兼、英語教育の専門家です。以下の条件に従って、シャドーイング練習用の英語スクリプト、単語解説、段階的シャドーイング用テキスト、理解度クイズ、および内容理解確認用のリンキング穴埋めディクテーション問題を作成し、JSON形式で出力してください。\n\n条件：\n1. テーマ: 科学技術分野のスタートアップによる1分間の投資家向けピッチ。\n2. ビジネス要素の強化: 解決する課題、ビジネスモデル、市場規模、参入障壁、現在の実績、資金使途を含める。\n3. 語数・難易度: 150〜180語程度。CEFR B2〜C1レベル。\n4. アクセント指定: 今回のアジア・多国籍パートは「{selected_country}」を指定して作成してください。\n5. 注釈（単語リスト）: 高校レベルを超える英単語やビジネス・専門用語（5〜8個）を抽出。\n6. Key Sentences: ピッチの中で最も重要かつシャドーイング練習に最適な1〜2文を抽出。必ず意味の区切りごとに / を挟み、強く発音する単語を <b>単語</b> タグで囲んだ「スラッシュ＆リズム表示形式」で出力すること。\n7. スラッシュリーディング・強音表示テキスト: 全文について意味の区切りごとに / を挟み、強く発音する単語を <b>単語</b> タグで囲む。\n8. 4択クイズ（3問）: ピッチ内容の把握度を確認する英語の4択問題を正確に3問作成。各問題には選択肢4つ（A, B, C, D）、正解の記号（A/B/C/D）、日本語の簡潔な解説を含める。\n9. リンキング穴埋め問題（3問）: ピッチ本文の中から、音が繋がる「リンキング現象（連結・脱落）」が起きて聞き取りづらいフレーズ（2〜3語）を3箇所抽出。前後の文脈を含む英文（穴埋め部分は [ _____ ] と表記）、正解フレーズ、カタカナ発音イメージヒント、日本語の発音変化解説を含めること。\n\nJSONキー: pitch_script, key_sentences, slash_script, vocabulary, japanese_translation, quiz (配列: question, options, answer, explanation), linking_dictation (配列: sentence_with_blank, answer, target_text, hint, explanation)"

response = client.chat.completions.create(
    model='gpt-4o',
    messages=[{'role': 'user', 'content': prompt}],
    response_format={'type': 'json_object'},
)

raw_content = response.choices[0].message.content

try:
  data = json.loads(raw_content)
except Exception:
  clean_json = re.sub(
      r'^```json\s*|\s*```$', '', raw_content.strip(), flags=re.MULTILINE
  )
  try:
    data = json.loads(clean_json)
  except Exception:
    data = {}

pitch_script = (
    data.get('pitch_script', '').strip()
    if isinstance(data.get('pitch_script'), str)
    else 'Failed to generate pitch script.'
)

raw_key = data.get('key_sentences', '')
if isinstance(raw_key, list):
  key_sentences = ' '.join(raw_key).strip()
elif isinstance(raw_key, str):
  key_sentences = raw_key.strip()
else:
  key_sentences = pitch_script[:100]

slash_script = (
    data.get('slash_script', '').strip()
    if isinstance(data.get('slash_script'), str)
    else pitch_script
)
vocabulary = (
    data.get('vocabulary', '').strip()
    if isinstance(data.get('vocabulary'), str)
    else 'No vocabulary generated.'
)
japanese_translation = (
    data.get('japanese_translation', '').strip()
    if isinstance(data.get('japanese_translation'), str)
    else 'No translation generated.'
)
quiz_data = data.get('quiz', []) if isinstance(data.get('quiz'), list) else []
linking_data = (
    data.get('linking_dictation', [])
    if isinstance(data.get('linking_dictation'), list)
    else []
)

clean_key_sentences = re.sub(r'<[^>]+>', '', key_sentences).replace('/', '')

sentence_list = [
    s.strip()
    for s in re.split(r'(?<=[.!?])\s+', pitch_script)
    if s.strip()
]

generated_text = f"""【今日のアクセント指定】
{selected_country}

【Pitch Script】
{pitch_script}

【Vocabulary & Key Phrases】
{vocabulary}

【日本語訳】
{japanese_translation}
"""

# 4. 音声合成＆MP3結合（公開用フォルダ public へ出力）
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

with open('public/audio.mp3', 'wb') as outfile:
  with open(audio_path, 'rb') as infile:
    outfile.write(infile.read())

# 5. HTML作成
quiz_json_str = json.dumps(quiz_data, ensure_ascii=False)
linking_json_str = json.dumps(linking_data, ensure_ascii=False)
sentences_json_str = json.dumps(sentence_list, ensure_ascii=False)

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
  .player-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px; }}
  .player-title {{ font-weight: bold; font-size: 0.9em; color: #adb5bd; }}
  
  .speed-controls {{ display: flex; gap: 4px; flex-wrap: wrap; }}
  .speed-btn {{ background: #343a40; color: #fff; border: 1px solid #495057; padding: 4px 8px; border-radius: 6px; cursor: pointer; font-size: 0.8em; transition: all 0.2s; }}
  .speed-btn:hover {{ background: #495057; }}
  .speed-btn.active {{ background: #0d6efd; border-color: #0d6efd; font-weight: bold; }}
  
  audio {{ width: 100%; }}
  h2 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 6px; font-size: 1.25em; margin-top: 0; }}
  
  .key-card {{ background: #fff3cd; border-left: 6px solid #ffc107; padding: 16px; border-radius: 8px; margin-bottom: 20px; }}
  .key-card h3 {{ margin: 0 0 10px 0; color: #856404; font-size: 1.1em; }}
  .key-sentence-box {{ display: flex; align-items: flex-start; gap: 12px; }}
  .key-text-content {{ font-size: 1.1em; line-height: 1.8; color: #212529; font-weight: bold; }}
  .key-text-content b {{ color: #0d6efd; font-weight: 700; }}
  
  .slash-text {{ font-size: 1.15em; line-height: 2.0; color: #212529; background: #fdfbf7; padding: 16px; border-radius: 8px; border: 1px dashed #d3d3d3; }}
  .slash-text b {{ color: #0d6efd; font-weight: 700; }}
  
  .sentence-item {{ display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px; padding: 10px; background: #f8f9fa; border-radius: 8px; }}
  .play-sentence-btn {{ background: #198754; color: #fff; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.85em; white-space: nowrap; flex-shrink: 0; }}
  .play-sentence-btn:hover {{ background: #157347; }}
  
  .script-text {{ font-size: 1.15em; line-height: 1.8; color: #212529; white-space: pre-wrap; }}
  .vocab-list {{ white-space: pre-wrap; font-size: 0.95em; background: #f1f3f5; padding: 16px; border-radius: 8px; }}

  .quiz-item {{ margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eee; }}
  .quiz-item:last-child {{ border-bottom: none; }}
  .quiz-q {{ font-weight: bold; font-size: 1.05em; margin-bottom: 10px; }}
  .quiz-opt {{ display: block; width: 100%; text-align: left; background: #f8f9fa; border: 1px solid #ced4da; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px; cursor: pointer; font-size: 0.95em; transition: background 0.2s; }}
  .quiz-opt:hover {{ background: #e9ecef; }}
  .quiz-opt.correct {{ background: #d1e7dd; border-color: #0f5132; color: #0f5132; font-weight: bold; }}
  .quiz-opt.incorrect {{ background: #f8d7da; border-color: #842029; color: #842029; }}
  .quiz-exp {{ margin-top: 8px; padding: 10px; background: #e2e3e5; border-radius: 6px; font-size: 0.9em; display: none; }}

  .linking-item {{ background: #f8f9fa; border: 1px solid #e9ecef; padding: 16px; border-radius: 8px; margin-bottom: 16px; }}
  .linking-q {{ font-size: 1.05em; margin-bottom: 8px; line-height: 1.6; }}
  .linking-input-group {{ display: flex; gap: 8px; margin: 10px 0; }}
  .linking-input {{ flex: 1; padding: 8px 12px; border: 1px solid #ced4da; border-radius: 6px; font-size: 1em; }}
  .linking-hint {{ font-size: 0.85em; color: #6c757d; margin-bottom: 6px; }}

  details {{ background: #fff; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden; }}
  summary {{ padding: 18px 24px; font-weight: bold; font-size: 1.1em; color: #1a237e; cursor: pointer; background: #fff; user-select: none; list-style: none; display: flex; justify-content: space-between; align-items: center; }}
  summary::-webkit-details-marker {{ display: none; }}
  summary::after {{ content: "▼"; font-size: 0.8em; color: #6c757d; transition: transform 0.2s; }}
  details[open] summary::after {{ transform: rotate(180deg); }}
  .details-content {{ padding: 0 24px 24px 24px; border-top: 1px solid #f1f3f5; }}
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
      <button class="speed-btn" onclick="setSpeed(0.6, this)">0.6x</button>
      <button class="speed-btn" onclick="setSpeed(0.7, this)">0.7x</button>
      <button class="speed-btn" onclick="setSpeed(0.8, this)">0.8x</button>
      <button class="speed-btn active" onclick="setSpeed(1.0, this)">1.0x</button>
      <button class="speed-btn" onclick="setSpeed(1.2, this)">1.2x</button>
      <button class="speed-btn" onclick="setSpeed(1.5, this)">1.5x</button>
    </div>
  </div>
  <audio id="audio-player" controls src="{audio_filename}?v={timestamp}" autoplay></audio>
</div>

<div class="card">
  <h2>📖 Pitch Script (全文原稿)</h2>
  <div class="script-text">{html.escape(pitch_script)}</div>
</div>

<div class="card">
  <h2>🎵 スラッシュ＆リズム表示テキスト</h2>
  <p style="font-size: 0.85em; color: #6c757d; margin-top: -6px;">/ : 息継ぎ・意識の区切り | <b style="color: #0d6efd;">青太字</b> : 強く発音する単語</p>
  <div class="slash-text">{slash_script}</div>
</div>

<div class="key-card">
  <h3>🎯 今日の重点シャドーイング練習センテンス (Key Sentence)</h3>
  <div class="key-sentence-box">
    <button class="play-sentence-btn" onclick="playText(`{html.escape(clean_key_sentences)}`)">▶ 再生</button>
    <div class="key-text-content">{key_sentences}</div>
  </div>
</div>

<div class="card">
  <h2>📝 Comprehension Check (3 Questions)</h2>
  <div id="quiz-container"></div>
</div>

<details open>
  <summary>✍️ Linking Dictation (3 Questions)</summary>
  <div class="details-content">
    <p style="font-size: 0.9em; color: #6c757d; margin-top: 14px;">音がつながって聞こえるリンキング（連結・脱落）部分の穴埋め問題です。再生ボタンで音声を聞いて入力してみましょう。</p>
    <div id="linking-container"></div>
  </div>
</details>

<details>
  <summary>🗣️ Sentence-by-Sentence Shadowing (Option)</summary>
  <div class="details-content">
    <p style="font-size: 0.9em; color: #6c757d; margin-top: 14px;">1文ずつじっくり聞いてシャドーイングの練習をしたい時にご活用ください。</p>
    <div id="sentence-container" style="margin-top: 10px;"></div>
  </div>
</details>

<div class="card">
  <h2>📚 全文テキスト＆注釈・解説</h2>
  <div class="vocab-list">{html.escape(generated_text)}</div>
</div>

<script>
  let currentSpeed = 1.0;

  function setSpeed(rate, btn) {{
    currentSpeed = rate;
    const audio = document.getElementById('audio-player');
    audio.playbackRate = rate;
    document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }}

  // 確実に英語ネイティブの声を選択する厳格な再生関数
  function playText(text) {{
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'en-US';
    utter.rate = currentSpeed;
    
    const voices = window.speechSynthesis.getVoices();
    // 言語がenで始まるボイスの中で、最も品質の高い米国/英国英語ボイスを検索
    let selectedVoice = voices.find(v => v.lang === 'en-US' || v.lang === 'en_US');
    if (!selectedVoice) {{
      selectedVoice = voices.find(v => v.lang.startsWith('en'));
    }}
    
    if (selectedVoice) {{
      utter.voice = selectedVoice;
    }}
    
    window.speechSynthesis.speak(utter);
  }}

  // ページの読み込み直後に音声エンジンを初期化させる
  window.addEventListener('DOMContentLoaded', () => {{
    if (typeof speechSynthesis !== 'undefined') {{
      speechSynthesis.getVoices();
    }}
  }});

  const linkingData = {linking_json_str};
  const linkingContainer = document.getElementById('linking-container');

  if (linkingData && linkingData.length > 0) {{
    linkingData.forEach((item, idx) => {{
      const div = document.createElement('div');
      div.className = 'linking-item';

      const fullSentence = item.sentence_with_blank.replace('[ _____ ]', item.answer);

      const playBtn = document.createElement('button');
      playBtn.className = 'play-sentence-btn';
      playBtn.innerHTML = '▶ 音声を聴く';
      playBtn.onclick = () => playText(fullSentence);

      const qText = document.createElement('div');
      qText.className = 'linking-q';
      qText.style.marginTop = '8px';
      qText.innerHTML = '<strong>Q' + (idx+1) + ':</strong> ' + item.sentence_with_blank;

      const hintText = document.createElement('div');
      hintText.className = 'linking-hint';
      hintText.textContent = '💡 ヒント (聞こえ方のイメージ): ' + (item.hint || '音声を聞いて穴埋めしてください');

      const inputGroup = document.createElement('div');
      inputGroup.className = 'linking-input-group';

      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'linking-input';
      input.placeholder = 'Type the missing words...';

      const checkBtn = document.createElement('button');
      checkBtn.className = 'play-sentence-btn';
      checkBtn.style.background = '#0d6efd';
      checkBtn.textContent = '答え合わせ';

      const expDiv = document.createElement('div');
      expDiv.className = 'quiz-exp';
      expDiv.innerHTML = '<strong>正解:</strong> <span style="color:#0d6efd; font-weight:bold;">' + item.answer + '</span><br><strong>解説:</strong> ' + item.explanation;

      checkBtn.onclick = () => {{
        expDiv.style.display = 'block';
      }};

      inputGroup.appendChild(input);
      inputGroup.appendChild(checkBtn);

      div.appendChild(playBtn);
      div.appendChild(qText);
      div.appendChild(hintText);
      div.appendChild(inputGroup);
      div.appendChild(expDiv);

      linkingContainer.appendChild(div);
    }});
  }}

  const sentenceList = {sentences_json_str};
  const sentenceContainer = document.getElementById('sentence-container');

  if (sentenceList && sentenceList.length > 0) {{
    sentenceList.forEach((st, idx) => {{
      const div = document.createElement('div');
      div.className = 'sentence-item';
      
      const btn = document.createElement('button');
      btn.className = 'play-sentence-btn';
      btn.innerHTML = '▶ 再生';
      btn.onclick = () => playText(st);

      const textSpan = document.createElement('span');
      textSpan.style.fontSize = '1em';
      textSpan.textContent = st;

      div.appendChild(btn);
      div.appendChild(textSpan);
      sentenceContainer.appendChild(div);
    }});
  }}

  const quizData = {quiz_json_str};
  const quizContainer = document.getElementById('quiz-container');

  if (quizData && quizData.length > 0) {{
    quizData.forEach((q, qIndex) => {{
      const itemDiv = document.createElement('div');
      itemDiv.className = 'quiz-item';
      
      const qTitle = document.createElement('div');
      qTitle.className = 'quiz-q';
      qTitle.textContent = q.question;
      itemDiv.appendChild(qTitle);

      const expDiv = document.createElement('div');
      expDiv.className = 'quiz-exp';
      expDiv.innerHTML = '<strong>解説:</strong> ' + q.explanation;

      q.options.forEach(opt => {{
        const btn = document.createElement('button');
        btn.className = 'quiz-opt';
        btn.textContent = opt;
        btn.onclick = () => {{
          const siblings = itemDiv.querySelectorAll('.quiz-opt');
          siblings.forEach(s => s.disabled = true);

          const selectedSymbol = opt.trim().charAt(0);
          if (selectedSymbol === q.answer) {{
            btn.classList.add('correct');
          }} else {{
            btn.classList.add('incorrect');
            siblings.forEach(s => {{
              if (s.textContent.trim().charAt(0) === q.answer) {{
                s.classList.add('correct');
              }}
            }});
          }}
          expDiv.style.display = 'block';
        }};
        itemDiv.appendChild(btn);
      }});

      itemDiv.appendChild(expDiv);
      quizContainer.appendChild(itemDiv);
    }});
  }}
</script>

</body>
</html>
"""

with open('public/index.html', 'w', encoding='utf-8') as f:
  f.write(html_content)

email_body = f"""本日のシャドーイング教材が更新されました！

リンキング特化型ディクテーション（3問）や段階的シャドーイング機能を搭載した専用Webページが開きます。

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

tracking_settings = TrackingSettings()
tracking_settings.click_tracking = ClickTracking(
    enable=False, enable_text=False
)
message.tracking_settings = tracking_settings

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
