# Stroid

Stroidは、株式・為替・暗号資産の価格をシンプルな画面で確認するWebアプリケーションです。銘柄コードを入力すると、Yahoo Financeのデータを基に現在値、前日比、出来高、取引時刻を表示します。株式では、取得できる場合にプレマーケットまたはアフターマーケットの価格も表示します。

フロントエンドはHTML、CSS、JavaScriptで構成され、価格取得APIはPythonと[`yfinance`](https://pypi.org/project/yfinance/)で実装されています。ローカル開発ではBottle、本番環境ではAWS LambdaとS3を利用する構成です。

## 主な機能

- 株式、為替、暗号資産の価格検索
- 現在値、前日比、騰落率、出来高、取引時刻の表示
- 株式のプレマーケット／アフターマーケット情報の表示
- BTC/USD、ETH/USD、USD/JPYを入力するショートカット
- 銘柄コードのブラウザへの保存と読み込み
- PCとモバイルの両方で利用できるコンパクトな画面

## 公開先

[http://aws-s3-serverless.s3-website-ap-northeast-1.amazonaws.com/stroid/](http://aws-s3-serverless.s3-website-ap-northeast-1.amazonaws.com/stroid/)

## 構成

```text
.
├── public/                         # 静的フロントエンド
│   ├── index.html
│   └── static/
│       ├── script.js
│       ├── style.css
│       └── favicon.png
├── lambda/
│   └── lambda_function.py          # AWS Lambda用API
├── local_test.py                   # Bottleによるローカルサーバー
├── requirements.txt                # Python依存パッケージ
├── run_Windows.bat                 # Windows用起動スクリプト
└── .github/workflows/
    └── stroid-deploy-s3.yml         # public/をS3へ同期するWorkflow
```

## 必要な環境

- Python 3（`zoneinfo`を使用）
- インターネット接続

価格データの取得にはYahoo Financeへ接続できる必要があります。

## ローカルでの起動

```bash
python local_test.py
```

起動後、ブラウザで <http://127.0.0.1:5400> を開きます。

サーバーは`0.0.0.0:5400`で待ち受けます。同じネットワーク内の別端末からアクセスする場合は、起動時に表示されるNetwork URLを使用してください。

## 使い方

1. 入力欄にYahoo Finance形式の銘柄コードを入力します。
2. `update`を押すか、Enterキーを押します。
3. 必要に応じて`save`で銘柄コードをブラウザのLocalStorageへ保存し、`load`で復元します。

入力例：

| 対象 | 銘柄コード |
| --- | --- |
| Apple | `AAPL` |
| トヨタ自動車 | `7203.T` |
| Bitcoin / USD | `BTC-USD` |
| Ethereum / USD | `ETH-USD` |
| USD / JPY | `JPY=X` |

`BTC`、`ETH`、`$/¥`の各ボタンは対応するコードを入力欄へ設定します。価格を取得するには、その後`update`を押してください。

## API

ローカルサーバーは次のGETエンドポイントを提供します。

```http
GET /api/quote?t=AAPL
GET /quote?t=AAPL
```

実行例：

```bash
curl "http://127.0.0.1:5400/api/quote?t=AAPL"
```

レスポンス例：

```json
{
  "ticker": "AAPL",
  "title": "Apple Inc. (AAPL)",
  "price": "210.50",
  "priceChange": "+1.25",
  "priceChangePercent": "(+0.60%)",
  "marketTime": "July 28 at 04:00:00 PM EDT",
  "volume": "Vol: 45,000,000",
  "postPrice": "210.80",
  "postPriceChange": "+0.30",
  "postPriceChangePercent": "(+0.14%)",
  "postMarketTime": "July 28 at 07:59:00 PM EDT"
}
```

値は表示用に整形された文字列です。時間外データや出来高を取得できない場合、対応するフィールドは`null`になります。

| ステータス | 条件 |
| --- | --- |
| `200` | 価格を取得できた |
| `400` | クエリパラメーター`t`がない |
| `500` | 銘柄が見つからない、または外部データの取得に失敗した |

## AWSへの配置

本番構成では、`public/`をS3の静的Webサイトとして配信し、`lambda/lambda_function.py`をLambda Function URLから呼び出します。

### Lambda

- ハンドラー: `lambda_function.lambda_handler`
- ランタイム: Python 3.13
- 依存パッケージ: `yfinance`
- 入力: Function URLのクエリパラメーター`t`

Lambdaへ配置する際は、`lambda_function.py`と依存パッケージをデプロイパッケージへ含めるか、依存パッケージをLambda Layerとして追加してください。Function URLからブラウザのリクエストを受け付けるためのCORS設定も必要です。

フロントエンドの接続先は`public/static/script.js`の`getApiUrl()`で決まります。S3のホスト名やLambda Function URLを変更する場合は、この関数の設定も更新してください。

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

## 開発時の注意

- `local_test.py`と`lambda/lambda_function.py`には同じ価格取得処理があります。取得項目や整形方法を変更する場合は、両方を更新してください。
- 表示される価格や時刻はYahoo Financeから取得できた値に依存し、リアルタイム性や完全性は保証されません。
- 暗号資産および為替では時間外取引の判定を行いません。

## ライセンス

[MIT License](LICENSE)
