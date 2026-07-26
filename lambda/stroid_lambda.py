import json
import time
import requests
from bs4 import BeautifulSoup

# CORS（オリジン間リソース共有）を許可するオリジン一覧
ALLOWED_ORIGINS = {
    "http://aws-s3-serverless.s3-website-ap-northeast-1.amazonaws.com",
    "http://127.0.0.1:5400",
    "http://localhost:5400",
}

# Yahoo Finance アクセス時の User-Agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

# 銘柄ごとの最新タイムスタンプ保持用辞書 (ロードバランサー遅延による巻き戻り防止)
LATEST_MARKET_TIMES = {}


def fetch_data(ticker):
    """
    1. 通常株価・リアルタイム価格は API (query2.finance.yahoo.com) から取得 (CDNキャッシュ回避)
    2. 時間外株価および時間外日時 (postMarketTime) は HTML の secondary セクションから確実に抽出
    3. タイムスタンプ逆転（遅延ノードヒット）時は None を返して HTTP 204 スキップ
    """
    headers = {"User-Agent": USER_AGENT}

    # 1. リアルタイム API リクエスト (通常価格)
    url_api = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    res = requests.get(url_api, headers=headers, timeout=5)

    if res.status_code != 200:
        raise Exception(f"Yahoo Finance API returned status {res.status_code}")

    data = res.json()
    result = data.get("chart", {}).get("result", [])
    if not result:
        raise Exception(f"Ticker not found: {ticker}")

    meta = result[0]["meta"]
    price = meta.get("regularMarketPrice")
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")

    if price is None:
        raise Exception(f"Price data not available for ticker: {ticker}")

    if prev_close is not None and prev_close > 0:
        change = price - prev_close
        change_pct = (change / prev_close) * 100
        fmt_change = f"+{change:,.2f}" if change >= 0 else f"{change:,.2f}"
        fmt_pct = f"(+{change_pct:.2f}%)" if change_pct >= 0 else f"({change_pct:.2f}%)"
    else:
        fmt_change = ""
        fmt_pct = ""

    name = meta.get("longName") or meta.get("shortName") or ticker
    symbol = meta.get("symbol", ticker)
    title = f"{name} ({symbol})"

    reg_time = meta.get("regularMarketTime")
    if reg_time:
        # 複数ノードの非同期遅延によるタイムスタンプ逆転（巻き戻り）時は None を返して HTTP 204 スキップ
        prev_time = LATEST_MARKET_TIMES.get(ticker, 0)
        if reg_time < prev_time:
            print(f"Stale timestamp for {ticker} ({reg_time} < {prev_time}). Returning HTTP 204.")
            return None
        else:
            LATEST_MARKET_TIMES[ticker] = reg_time  # 新しいタイムスタンプが来たら更新

        tz_str = meta.get("timezone", "UTC")
        m_time = time.strftime(f"%I:%M:%S %p {tz_str}", time.gmtime(reg_time))
        market_time = f"As of {m_time}."
    else:
        market_time = ""

    # API の時間外データ確認
    post_price = meta.get("postMarketPrice")
    post_change = meta.get("postMarketChange")
    post_pct = meta.get("postMarketChangePercent")

    fmt_post_price = f"{post_price:,.2f}" if isinstance(post_price, (int, float)) else None
    fmt_post_change = f"+{post_change:,.2f}" if post_change and post_change >= 0 else (f"{post_change:,.2f}" if post_change else None)
    fmt_post_pct = f"(+{post_pct:.2f}%)" if post_pct and post_pct >= 0 else (f"({post_pct:.2f}%)" if post_pct else None)
    fmt_post_time = None

    # 2. HTML の secondary セクションから時間外株価・変化率・通知日時 (After hours: ...) を抽出
    try:
        url_html = f"https://finance.yahoo.com/quote/{ticker}/"
        res_html = requests.get(url_html, headers=headers, timeout=5)

        if res_html.status_code == 200:
            soup = BeautifulSoup(res_html.text, "lxml")  # type: ignore
            sec_sec = soup.find("section", class_=lambda c: c and "secondary" in c)
            if sec_sec and hasattr(sec_sec, "find"):
                p_elem = sec_sec.find(attrs={"data-testid": ["qsp-pre-price", "qsp-post-price"]})  # type: ignore
                c_elem = sec_sec.find(attrs={"data-testid": ["qsp-pre-price-change", "qsp-post-price-change"]})  # type: ignore
                cp_elem = sec_sec.find(attrs={"data-testid": ["qsp-pre-price-change-percent", "qsp-post-price-change-percent"]})  # type: ignore
                t_elem = sec_sec.find("span", class_=lambda c: c and "marketTimeNotice" in c)  # type: ignore

                if p_elem and not fmt_post_price:
                    fmt_post_price = p_elem.text.strip()
                if c_elem and not fmt_post_change:
                    fmt_post_change = c_elem.text.strip()
                if cp_elem and not fmt_post_pct:
                    fmt_post_pct = cp_elem.text.strip()
                if t_elem:
                    fmt_post_time = t_elem.text.strip()
    except Exception as ex:
        print(f"Post market HTML check failed for {ticker}: {ex}")

    # 株式銘柄 (EQUITY) のみ出来高 (Volume) を抽出
    inst_type = meta.get("instrumentType")
    raw_vol = meta.get("regularMarketVolume")
    if inst_type == "EQUITY" and isinstance(raw_vol, (int, float)) and raw_vol > 0:
        volume = f"Vol: {raw_vol:,}"
    else:
        volume = None

    return {
        "ticker": ticker,
        "title": title,
        "price": f"{price:,.2f}" if isinstance(price, (int, float)) else str(price),
        "priceChange": fmt_change,
        "priceChangePercent": fmt_pct,
        "marketTime": market_time,
        "volume": volume,
        "postPrice": fmt_post_price,
        "postPriceChange": fmt_post_change,
        "postPriceChangePercent": fmt_post_pct,
        "postMarketTime": fmt_post_time,
    }


def lambda_handler(event, context):
    """
    AWS Lambda エントリーポイント関数
    """
    headers = event.get("headers", {}) or {}
    req_origin = headers.get("origin") or headers.get("Origin") or ""
    cors_origin = req_origin if req_origin in ALLOWED_ORIGINS else "*"

    cors_headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,GET",
    }

    params = event.get("queryStringParameters", {}) or {}
    ticker = params.get("t", "").strip().upper()

    if not ticker:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "Missing parameter: t"}),
        }

    try:
        result_data = fetch_data(ticker)
        if result_data is None:
            return {
                "statusCode": 204,
                "headers": cors_headers,
                "body": "",
            }
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps(result_data, ensure_ascii=False),
        }
    except Exception as e:
        print(f"Error getting data for {ticker}: {str(e)}")
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": str(e)}),
        }
