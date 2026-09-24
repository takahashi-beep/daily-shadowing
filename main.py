import base64
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

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# アジア・多国籍アクセントのマップ
ACCENTS = {
    'インド': {'tld': 'co.in', 'lang': 'en'},
    'シンガポール': {'tld': 'com.sg', 'lang': 'en'},
    'フィリピン': {'tld': 'com.ph', 'lang': 'en'},
    '英国': {'tld': 'co.uk', 'lang': 'en'},
    'オーストラリア': {'tld': 'com.au', 'lang': 'en'},
}

selected_country = random.choice(list(ACCENTS.keys()))
accent_info = ACCENTS[selected_country]

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

# 【Pitch Script】の英文テキストのみを抽出
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

# --- 2パターンの音声を生成して1つに連結 ---

# 1. パート1：標準的な米国英語 (Standard American English)
gTTS(text='First, Standard American accent.', lang='en', tld='com').save(
    'part1_intro.mp3'
)
gTTS(text=pitch_script, lang='en', tld='com').save('part1_script.mp3')

# 2. パート2：本日ターゲットのアクセント (例: シンガポール、インド等)
gTTS(
    text=f'Next, {selected_country} accent.', lang='en', tld='com'
).save('part2_intro.mp3')
gTTS(text=pitch_script, lang='en', tld=accent_info['tld']).save(
    'part2_script.mp3'
)

# 3. 4つの音声トラックを順番に1つのMP3ファイルへ結合
audio_file = 'shadowing_pitch.mp3'
parts = [
    'part1_intro.mp3',
    'part1_script.mp3',
    'part2_intro.mp3',
    'part2_script.mp3',
]

with open(audio_file, 'wb') as outfile:
  for p in parts:
    with open(p, 'rb') as infile:
      outfile.write(infile.read())

# メール送信処理
message = Mail(
    from_email=os.environ.get('FROM_EMAIL'),
    to_emails=os.environ.get('TO_EMAIL'),
    subject=(
        f'【Daily Shadowing】標準アメリカ英語 ＆ {selected_country}アクセント'
    ),
    plain_text_content=generated_text,
)

with open(audio_file, 'rb') as f:
  data = f.read()

encoded_file = base64.b64encode(data).decode()

attached_file = Attachment(
    FileContent(encoded_file),
    FileName('shadowing_pitch.mp3'),
    FileType('audio/mpeg'),
    Disposition('attachment'),
)
message.attachment = attached_file

sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
sg.send(message)

print('メール送信が完了しました！')
