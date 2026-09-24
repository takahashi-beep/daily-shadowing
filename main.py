import base64
import os
import random
import re
from gtts import gTTS
from openai import OpenAI
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
    Mail,
)

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

ACCENTS = {
    '米国': {'tld': 'com', 'lang': 'en'},
    '英国': {'tld': 'co.uk', 'lang': 'en'},
    'インド': {'tld': 'co.in', 'lang': 'en'},
    'シンガポール': {'tld': 'com.sg', 'lang': 'en'},
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
4. **アクセント指定**: 今回は「{selected_country}」を指定して作成してください。
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

pitch_match = re.search(
    r'【Pitch Script】\n(.*?)\n\n【Vocabulary', generated_text, re.DOTALL
)
pitch_script = pitch_match.group(1) if pitch_match else generated_text

tts = gTTS(text=pitch_script, lang=accent_info['lang'], tld=accent_info['tld'])
audio_file = 'shadowing_pitch.mp3'
tts.save(audio_file)

message = Mail(
    from_email=os.environ.get('FROM_EMAIL'),
    to_emails=os.environ.get('TO_EMAIL'),
    subject=f'【Daily Shadowing】{selected_country}アクセント - 科学技術ピッチ',
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
