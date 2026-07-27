import json
import time
from datetime import datetime
import zoneinfo
import yfinance as yf


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
    name = info.get("longName") or info.get("shortName") or ticker
    symbol = info.get("symbol", ticker)
    title = f"{name} ({symbol})"

    # タイムゾーンの変換オブジェクト作成
    tz_name = fast.get("timezone") or info.get("timezone", "UTC")
    try:
        tz_obj = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz_obj = zoneinfo.ZoneInfo("UTC")

    # 通常取引時刻 (時間外と統一した Month Day at HH:MM:SS AM/PM Timezone フォーマット)
    reg_time = info.get("regularMarketTime")
    if reg_time:
        dt_reg = datetime.fromtimestamp(reg_time, tz=tz_obj)
        time_str = dt_reg.strftime("%B %d at %I:%M:%S %p %Z").strip()
        market_time = f"{time_str}"
    else:
        m_time = time.strftime("%B %d at %I:%M:%S %p UTC", time.gmtime())
        market_time = f"{m_time}"

    # 出来高 (Volume)
    raw_vol = fast.get("last_volume") or info.get("regularMarketVolume")
    if isinstance(raw_vol, (int, float)) and raw_vol > 0:
        volume = f"Vol: {int(raw_vol):,}"
    else:
        volume = None

    # 仮想通貨 (Cryptocurrency) のみ時間外チェックをスキップ
    quote_type = str(info.get("quoteType") or fast.get("quote_type") or "").upper()
    is_crypto = (quote_type == "CRYPTOCURRENCY") or ticker.endswith("-USD") or ticker.endswith("-EUR") or ticker.endswith("-BTC")

    # 時間外データ (仮想通貨以外の場合に Pre/Post Market をチェック)
    fmt_post_price = None
    fmt_post_change = None
    fmt_post_pct = None
    fmt_post_time = None

    if not is_crypto:
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


def lambda_handler(event, context):
    response_headers = {
        "Content-Type": "application/json; charset=UTF-8",
    }

    params = event.get("queryStringParameters", {}) or {}
    ticker = params.get("t", "").strip().upper()

    if not ticker:
        return {
            "statusCode": 400,
            "headers": response_headers,
            "body": json.dumps({"error": "Missing parameter: t"}),
        }

    try:
        result_data = fetch_data(ticker)
        if result_data is None:
            return {
                "statusCode": 204,
                "headers": response_headers,
                "body": "",
            }
        return {
            "statusCode": 200,
            "headers": response_headers,
            "body": json.dumps(result_data, ensure_ascii=False),
        }
    except Exception as e:
        print(f"Error getting data for {ticker}: {str(e)}")
        return {
            "statusCode": 500,
            "headers": response_headers,
            "body": json.dumps({"error": str(e)}),
        }
