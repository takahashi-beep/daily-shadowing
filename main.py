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
prompt = f"""
あなたは科学技術スタートアップの創業コンサルタント兼、英語教育の専門家です。
以下の条件に従って、シャドーイング練習用の英語スクリプト、単語解説、段階的シャドーイング用テキスト、および内容理解確認クイズを作成してください。

### 条件：
1. **テーマ**: 科学技術分野のスタートアップによる1分間の投資家向けピッチ。
2. **ビジネス要素の強化**: 解決する課題、ビジネスモデル、市場規模、参入障壁、現在の実績、資金使途を含める。
3. **語数・難易度**: 150〜180語程度。CEFR B2〜C1レベル。
4. **アクセント指定**: 今回のアジア・多国籍パートは「{selected_country}」を指定して作成してください。
5. **注釈（単語リスト）**: 高校レベルを超える英単語やビジネス・専門用語（5〜8個）を抽出。
6. **Key Sentences**: ピッチの中で最も重要かつシャドーイング練習に最適な1〜2文を抽出。
7. **スラッシュリーディング・強音表示テキスト**:
   - 意味の区切り（チャンク）ごとに ` / ` を挟む。
   - 強く発音する単語（重要名詞、動詞、強調箇所など）を `<b>単語</b>` タグで囲む。
8. **4択クイズ（3問）**:
   - ピッチ内容の把握度を確認する英語の4択問題を正確に3問作成。
   - 各問題には選択肢4つ（A, B, C, D）、正解の記号（A/B/C/D）、日本語の簡潔な解説を含める。

### 出力フォーマット（JSON形式）：
```json
{{
  "pitch_script": "150-180 words pitch script in English",
  "key_sentences": "Most important 1-2 sentences for shadowing practice",
  "slash_script": "<b>Good day</b>, / esteemed <b>investors</b>. / ...",
  "vocabulary": "1. Word (pronunciation): Meaning\\n   - Note: Explanation",
  "japanese_translation": "Japanese translation of the pitch",
  "quiz": [
    {{
      "question": "1. What is the main problem...?",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "answer": "A",
      "explanation": "日本語解説"
    }},
    {{
      "question": "2. ...",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "answer": "B",
      "explanation": "日本語解説"
    }},
    {{
      "question": "3. ...",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "answer": "C",
      "explanation": "日本語解説"
    }}
  ]
}}
