import json
import time
import yfinance as yf


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


def lambda_handler(event, context):
    # AWS Lambda Function URL の CORS 自動付与との重複を防ぐため、Python 側は Content-Type のみ指定
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
