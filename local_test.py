#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stroid - ローカル開発用 Bottle サーバー
------------------------------------------
ローカル環境 (http://127.0.0.1:5400) で Stroid Web アプリを起動・テストするためのサーバーです。
yfinance ライブラリにより高精度な株価・為替・時間外情報を取得します。
"""

import json
import socket
import time
from datetime import datetime
import zoneinfo
from bottle import TEMPLATE_PATH, Bottle, debug, request, response, static_file, template  # type: ignore
import yfinance as yf

# Bottle アプリの初期化
app = Bottle()

# HTML テンプレート (index.html) の参照先フォルダを指定
TEMPLATE_PATH.append("./public")


# -----------------------------------------------------------------------------
# ルート 1: トップページ (HTML 配信)
# -----------------------------------------------------------------------------
@app.get("/")  # type: ignore
@app.get("/index.html")  # type: ignore
def index():
    """public/index.html をレンダーして表示"""
    return template("index")  # type: ignore


# -----------------------------------------------------------------------------
# ルート 2: 株価データ取得 API エンドポイント
# -----------------------------------------------------------------------------
def fetch_data(ticker):
    """
    yfinance ライブラリを利用して株価・為替・時間外データを高精度に取得
    """
    t = yf.Ticker(ticker)
    fast = t.fast_info
    info = getattr(t, "info", {}) or {}

    # 価格と前日終値の取得
    price = fast.get("last_price") or fast.get("regular_market_price")
    prev_close = fast.get("previous_close")

    if price is None:
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")

    if price is None:
        raise Exception(f"{ticker}: not found")

    if prev_close is not None and prev_close > 0:
        change = price - prev_close
        change_pct = (change / prev_close) * 100
        fmt_change = f"+{change:,.2f}" if change >= 0 else f"{change:,.2f}"
        fmt_pct = f"(+{change_pct:.2f}%)" if change_pct >= 0 else f"({change_pct:.2f}%)"
    else:
        fmt_change = ""
        fmt_pct = ""

    # タイトル
    name = info.get("longName") or info.get("shortName") or ticker
    symbol = info.get("symbol", ticker)
    title = f"{name} ({symbol})"

    # 銘柄タイプの判定
    quote_type = str(fast.get("quote_type") or info.get("quoteType") or "").upper()
    is_crypto = (quote_type == "CRYPTOCURRENCY")
    is_currency = (quote_type == "CURRENCY")

    # タイムゾーンの決定
    if is_crypto:
        tz_obj = zoneinfo.ZoneInfo("UTC")
    elif is_currency:
        tz_obj = zoneinfo.ZoneInfo("America/New_York")
    else:
        tz_name = fast.get("timezone") or info.get("timezone")
        tz_obj = zoneinfo.ZoneInfo(tz_name or "UTC")

    # 通常取引時刻 (時間外と統一した Month Day at HH:MM:SS AM/PM Timezone フォーマット)
    reg_time = info.get("regularMarketTime")
    if reg_time:
        dt_reg = datetime.fromtimestamp(reg_time, tz=tz_obj)
        time_str = dt_reg.strftime("%B %d at %I:%M:%S %p %Z").strip()
        market_time = time_str
    else:
        m_time = time.strftime("%B %d at %I:%M:%S %p UTC", time.gmtime())
        market_time = m_time

    # 出来高 (Volume)
    raw_vol = fast.get("last_volume") or info.get("regularMarketVolume")
    if isinstance(raw_vol, (int, float)) and raw_vol > 0:
        volume = f"Vol: {int(raw_vol):,}"
    else:
        volume = None

    # 時間外データ (仮想通貨・為替以外の場合に Pre/Post Market をチェック)
    fmt_post_price = None
    fmt_post_change = None
    fmt_post_pct = None
    fmt_post_time = None

    if not (is_crypto or is_currency):
        try:
            post_price = info.get("postMarketPrice") or fast.get("post_market_price")
            post_change = info.get("postMarketChange")
            post_pct = info.get("postMarketChangePercent")
            post_time_unix = info.get("postMarketTime")

            pre_price = info.get("preMarketPrice") or fast.get("pre_market_price")
            pre_change = info.get("preMarketChange")
            pre_pct = info.get("preMarketChangePercent")
            pre_time_unix = info.get("preMarketTime")

            if isinstance(post_price, (int, float)) and post_price > 0:
                fmt_post_price = f"{post_price:,.2f}"
                if isinstance(post_change, (int, float)):
                    fmt_post_change = f"+{post_change:,.2f}" if post_change >= 0 else f"{post_change:,.2f}"
                if isinstance(post_pct, (int, float)):
                    fmt_post_pct = f"(+{post_pct:.2f}%)" if post_pct >= 0 else f"({post_pct:.2f}%)"
                if post_time_unix:
                    dt_post = datetime.fromtimestamp(post_time_unix, tz=tz_obj)
                    fmt_post_time = dt_post.strftime("%B %d at %I:%M:%S %p %Z")

            elif isinstance(pre_price, (int, float)) and pre_price > 0:
                fmt_post_price = f"{pre_price:,.2f}"
                if isinstance(pre_change, (int, float)):
                    fmt_post_change = f"+{pre_change:,.2f}" if pre_change >= 0 else f"{pre_change:,.2f}"
                if isinstance(pre_pct, (int, float)):
                    fmt_post_pct = f"(+{pre_pct:.2f}%)" if pre_pct >= 0 else f"({pre_pct:.2f}%)"
                if pre_time_unix:
                    dt_pre = datetime.fromtimestamp(pre_time_unix, tz=tz_obj)
                    fmt_post_time = dt_pre.strftime("%B %d at %I:%M:%S %p %Z")


        except Exception as ex:
            print(f"yfinance pre/post market check failed for {ticker}: {ex}")

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
    株価データ取得 API エンドポイント
    """
    response.content_type = "application/json; charset=UTF-8"
    response.headers["Access-Control-Allow-Origin"] = "*"

    ticker = str(request.query.get("t", "")).strip().upper()  # type: ignore
    if not ticker:
        response.status = 400
        return json.dumps({"error": "Missing parameter: t"})

    try:
        data = fetch_data(ticker)
        if data is None:
            response.status = 204
            return ""
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        response.status = 500
        return json.dumps({"error": str(e)})


# -----------------------------------------------------------------------------
# ルート 3: 静的ファイル配信 (CSS, JS, Favicon)
# -----------------------------------------------------------------------------
@app.get("/static/<filepath:path>")  # type: ignore
def server_static(filepath):
    """public/static/ 配下の CSS, JS, 画像等を配信"""
    return static_file(filepath, root="./public/static")  # type: ignore


# -----------------------------------------------------------------------------
# ネットワーク IP 取得ヘルパー
# -----------------------------------------------------------------------------
def get_local_ip():
    """VPN アクティブ時も LAN 内の物理 IP (192.168.x.x) を優先取得"""
    try:
        hostname = socket.gethostname()
        addresses = socket.gethostbyname_ex(hostname)[2]
        lan_ips = [ip for ip in addresses if ip.startswith("192.168.")]
        if lan_ips:
            return lan_ips[0]
        other_ips = [ip for ip in addresses if not ip.startswith("127.") and not ip.startswith("10.")]
        if other_ips:
            return other_ips[0]
    except Exception:
        pass
    return "127.0.0.1"


# -----------------------------------------------------------------------------
# サーバー起動メイン処理
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 5400

    print("\n" + "=" * 50)
    print(" 🚀 Stroid Local Bottle Server Running!")
    print(f"  - Local:   http://127.0.0.1:{port}")
    print(f"  - Network: http://{local_ip}:{port}")
    print("=" * 50 + "\n")

    debug(True)
    app.run(host="0.0.0.0", port=port, reloader=True)
