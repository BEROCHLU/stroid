# Stroid

Stroid は、Yahoo Finance のデータを利用して株価・為替・暗号資産の現在値を表示するシンプルな Web アプリです。  
フロントエンドは静的ファイルとして配信でき、ローカル開発時は Bottle サーバー、公開時は S3 静的サイト + AWS Lambda Function URL を使う構成です。

## 主な機能

- ティッカーを入力して価格情報を取得
- 前日比・前日比率・出来高・市場時刻を表示
- 米国株などで取得できる場合はプレマーケット / アフターマーケット価格を表示
- BTC、ETH、USD/JPY のショートカットボタン
- 入力したティッカーをブラウザの LocalStorage に保存 / 読み込み
- ローカル開発用 Bottle サーバー
- GitHub Actions による S3 への静的ファイルデプロイ

## 公開先

[http://aws-s3-serverless.s3-website-ap-northeast-1.amazonaws.com/stroid/](http://aws-s3-serverless.s3-website-ap-northeast-1.amazonaws.com/stroid/)

## 構成

```text
.
├── lambda/
│   └── lambda_function.py      # AWS Lambda 用の株価取得 API
├── public/
│   ├── index.html              # フロントエンド HTML
│   └── static/
│       ├── script.js           # フロントエンドロジック
│       ├── style.css           # スタイル
│       └── favicon.png
├── local_test.py               # ローカル開発用 Bottle サーバー
├── requirements.txt            # Python 依存関係
├── run_Windows.bat             # Windows 用ローカル起動スクリプト
└── .github/workflows/
    └── stroid-deploy-s3.yml    # S3 デプロイ用 GitHub Actions
```

## 技術スタック

- Python
- Bottle
- yfinance
- HTML / CSS / JavaScript
- AWS S3 Static Website Hosting
- AWS Lambda Function URL
- GitHub Actions

## セットアップ

Python 3 が必要です。

```bash
pip install -r requirements.txt
```

## ローカル起動

```bash
python3 local_test.py
```

起動後、ブラウザで以下を開きます。

```text
http://127.0.0.1:5400
```

`run_Windows.bat` でも起動できます。

## 使い方

1. テキストボックスに Yahoo Finance 形式のティッカーを入力します。
2. `update` ボタン、または Enter キーで価格を取得します。
3. 必要に応じて `save` で現在のティッカーを保存し、`load` で読み込みます。

入力例:

```text
AAPL
MSFT
7203.T
BTC-USD
ETH-USD
JPY=X
```

## API

ローカル開発時は Bottle サーバーが API を提供します。

```text
GET /api/quote?t=<ticker>
GET /quote?t=<ticker>
```

例:

```text
http://127.0.0.1:5400/api/quote?t=AAPL
```

レスポンス例:

```json
{
  "ticker": "AAPL",
  "title": "Apple Inc. (AAPL)",
  "price": "123.45",
  "priceChange": "+1.23",
  "priceChangePercent": "(+1.01%)",
  "marketTime": "July 27 at 04:00:00 PM EDT",
  "volume": "Vol: 12,345,678",
  "postPrice": "124.00",
  "postPriceChange": "+0.55",
  "postPriceChangePercent": "(+0.45%)",
  "postMarketTime": "July 27 at 07:59:00 PM EDT"
}
```

`t` パラメータがない場合は `400`、データ取得に失敗した場合は `500` を返します。

## フロントエンドの API 接続先

`public/static/script.js` の `getApiUrl()` で接続先を切り替えています。

- `localhost` / `127.0.0.1`: `/api/quote`
- `aws-s3-serverless.s3-website-ap-northeast-1.amazonaws.com`: AWS Lambda Function URL
- その他のホスト: `/quote`

S3 バケット名、静的サイト URL、Lambda Function URL を変更した場合は、この分岐も更新してください。

## AWS デプロイ

`.github/workflows/stroid-deploy-s3.yml` は、`main` ブランチへの push 時に `public/` 配下を S3 バケットへ同期します。

必要な GitHub Secrets:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

現在の workflow は以下を実行します。

```bash
aws s3 sync ./public/ s3://aws-s3-serverless/stroid/ --delete
```

注意: この workflow は静的ファイルのみをデプロイします。`lambda/lambda_function.py` の Lambda 反映は別途行う必要があります。

## 開発メモ

- 価格データの取得は `yfinance` に依存します。Yahoo Finance 側の仕様変更やレート制限により、取得に失敗する可能性があります。
- ローカルサーバーは `0.0.0.0:5400` で起動するため、同一 LAN 内の端末からもアクセスできます。
- `local_test.py` と `lambda/lambda_function.py` には同等の `fetch_data()` 実装があります。API ロジックを変更する場合は両方の整合性に注意してください。
