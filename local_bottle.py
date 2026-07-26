#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stroid - ローカル開発用 Bottle サーバー
------------------------------------------
ローカル環境 (http://127.0.0.1:5400) で Stroid Web アプリを起動・テストするためのサーバーです。
Yahoo Finance リアルタイム API + 時間外情報（株価・日時）の補完取得機能を備えています。
"""

import json
import socket
import time
from bottle import TEMPLATE_PATH, Bottle, debug, request, response, static_file, template  # type: ignore
import yfinance as yf

# Bottle アプリの初期化
app = Bottle()

# HTML テンプレート (index.html) の参照先フォルダを指定
TEMPLATE_PATH.append("./public")

# Yahoo Finance アクセス時の User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"


# -----------------------------------------------------------------------------
# ルート 1: トップページ (HTML 配信)
# -----------------------------------------------------------------------------
@app.get("/")  # type: ignore
@app.get("/index.html")  # type: ignore
def index():
    """public/index.html をレンダーして表示"""
    return template("index")  # type: ignore


# 銘柄ごとの最新タイムスタンプ保持用辞書 (ロードバランサー遅延による巻き戻り防止)
LATEST_MARKET_TIMES = {}


# -----------------------------------------------------------------------------
# ルート 2: 株価データ取得 API エンドポイント
# -----------------------------------------------------------------------------
def fetch_data(ticker):
    """
    yfinance ライブラリを利用して株価・為替・時間外データを高精度に取得
    """
    t = yf.Ticker(ticker)
    
    # 銘柄基本情報・リアルタイム価格 (fast_info / info)
    fast = t.fast_info
    
    # 価格と前日終値の取得
    price = fast.get("last_price") or fast.get("regular_market_price")
    prev_close = fast.get("previous_close")
    
    if price is None:
        info = getattr(t, "info", {}) or {}
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        
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

    # タイトル
    info = getattr(t, "info", {}) or {}
    name = info.get("longName") or info.get("shortName") or ticker
    symbol = info.get("symbol", ticker)
    title = f"{name} ({symbol})"

    # タイムゾーンと時間
    tz_str = fast.get("timezone") or info.get("timezone", "UTC")
    m_time = time.strftime(f"%I:%M:%S %p {tz_str}", time.gmtime())
    market_time = f"As of {m_time}."

    # 出来高 (Volume)
    raw_vol = fast.get("last_volume") or info.get("regularMarketVolume")
    if isinstance(raw_vol, (int, float)) and raw_vol > 0:
        volume = f"Vol: {int(raw_vol):,}"
    else:
        volume = None

    # 仮想通貨 (Cryptocurrency) のみ時間外チェックをスキップ
    quote_type = str(info.get("quoteType") or fast.get("quote_type") or "").upper()
    is_crypto = (quote_type == "CRYPTOCURRENCY") or ticker.endswith("-USD") or ticker.endswith("-EUR") or ticker.endswith("-BTC")

    # 時間外データ (仮想通貨以外の場合にチェック)
    fmt_post_price = None
    fmt_post_change = None
    fmt_post_pct = None
    fmt_post_time = None

    if not is_crypto:
        try:
            hist = t.history(period="1d", interval="1m", prepost=True)
            if not hist.empty:
                last_price_val = float(hist["Close"].iloc[-1])
                if abs(last_price_val - price) >= 0.01:
                    fmt_post_price = f"{last_price_val:,.2f}"
                    p_diff = last_price_val - price
                    p_pct = (p_diff / price) * 100
                    fmt_post_change = f"+{p_diff:,.2f}" if p_diff >= 0 else f"{p_diff:,.2f}"
                    fmt_post_pct = f"(+{p_pct:.2f}%)" if p_pct >= 0 else f"({p_pct:.2f}%)"
                    fmt_post_time = "Post/Pre Market"
        except Exception as ex:
            print(f"yfinance history prepost check failed for {ticker}: {ex}")

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


@app.get("/api/quote")  # type: ignore
@app.get("/quote")  # type: ignore
def quote():
    """
    クエリパラメータ ?t=AAPL や ?t=QS や ?t=BTC-USD を受け取り、
    Yahoo Finance から最速・高精度なデータを返却する API
    """
    response.content_type = "application/json; charset=UTF-8"
    response.headers["Access-Control-Allow-Origin"] = "*"

    ticker = str(request.query.get("t", "")).strip().upper()  # type: ignore
    if not ticker:
        response.status = 400
        return json.dumps({"error": "Missing parameter: t"})

    try:
        result_data = fetch_data(ticker)
        if result_data is None:
            response.status = 204
            return ""
        return json.dumps(result_data, ensure_ascii=False)

    except Exception as e:
        print(f"Error getting data for {ticker}: {e}")
        response.status = 500
        return json.dumps({"error": str(e)})


# -----------------------------------------------------------------------------
# ルート 3: 静的ファイル (CSS / JS / 画像) の配信
# -----------------------------------------------------------------------------
@app.get("/static/<filepath:path>")  # type: ignore
def server_static(filepath):
    """public/static/ 以下のファイルを配信"""
    return static_file(filepath, root="./public/static")  # type: ignore


def get_local_ip():
    """VPN環境下でも物理LAN（192.168.x.x等）のローカルIPを優先取得"""
    try:
        # PC内の全IPアドレス一覧を取得
        hostname = socket.gethostname()
        _, _, ip_list = socket.gethostbyname_ex(hostname)

        # 192.168. 系の物理LAN IPを最優先
        for ip in ip_list:
            if ip.startswith("192.168."):
                return ip

        # 172.16.〜172.31. 系のプライベートIPを次点選択
        for ip in ip_list:
            if ip.startswith("172."):
                parts = ip.split(".")
                if len(parts) >= 2 and 16 <= int(parts[1]) <= 31:
                    return ip

        # フォールバック
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# -----------------------------------------------------------------------------
# サーバー起動メイン処理
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    local_ip = get_local_ip()
    print("Starting Stroid local server...")
    print(f"  - Local:   http://localhost:5400")
    print(f"  - Network: http://{local_ip}:5400")
    debug(True)
    app.run(host="0.0.0.0", port=5400, reloader=False)
