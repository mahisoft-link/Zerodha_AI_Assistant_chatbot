import yfinance as yf
import pandas as pd
#taking data from the portfolios
def get_market_data(symbols):
    market_data = {}
    for symbol in symbols:


        try:
            yahoo_symbol = "^NSEI" if symbol == "^NSEI" else f"{symbol}.NS"
            stock = yf.Ticker(yahoo_symbol)
            # NOTE: "2d" is NOT a valid yfinance period. Valid values are:
            # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            history = stock.history(period="5d")  # gives last few trading days
            if history.empty:
                print(f"No price history returned for {symbol}")
                continue

            # yfinance sometimes returns a trailing row (e.g. "today")
            # with a NaN Close if the day's data isn't fully settled yet.
            # Drop those before picking the latest price, otherwise
            # current_price ends up NaN even though older rows are fine.
            history = history.dropna(subset=["Close"])
            if history.empty:
                print(f"No valid Close price found for {symbol}")
                continue

            current_price = round(history["Close"].iloc[-1],2) #give last data
            
            if len(history) > 1:
                previous_close = round(history["Close"].iloc[-2],2)
            else:
                previous_close = current_price
            change = round(current_price - previous_close,2)

            if previous_close != 0:
                change_pct = round((change/previous_close) * 100,2)
            else:
                change_pct = 0

            market_data[symbol] = {
                "current_price": current_price,
                "Previous Close": previous_close,
                "change": change,
                "change_pct": change_pct
            }
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
    return market_data

def get_historical_stock_data(symbol, period="365d"):

    try:

        yahoo_symbol = (
            "^NSEI"
            if symbol == "^NSEI"
            else f"{symbol}.NS"
        )

        stock = yf.Ticker(yahoo_symbol)

        history = stock.history(
            period=period
        )

        if history.empty:
            return pd.DataFrame()

        history = history.reset_index()

        history = history[
            ["Date", "Close"]
        ]

        history.rename(
            columns={
                "Close": "Price"
            },
            inplace=True
        )

        return history

    except Exception as e:

        print(
            f"Error fetching historical data for {symbol}: {e}"
        )

        return pd.DataFrame()
            


def updated_current_price(df):
    symbols = df["Stock Symbol"].tolist()
    market_data = get_market_data(symbols)

    current_price = []
    previous_close = []
    change = []
    change_pct = []

    for symbol in symbols:
        data = market_data.get(symbol,{})
        current_price.append(data.get("current_price"))
        previous_close.append(data.get("Previous Close"))
        change.append(data.get("change"))
        change_pct.append(data.get("change_pct"))
    df["Current Price"] = current_price
    df["Previous Close"] = previous_close
    df["Change"] = change
    df["Change %"] = change_pct
    return df


def get_stock_info(symbol):
    try:
        stock = yf.Ticker(f"{symbol}.NS")
        info = stock.info
        return {"Company name": info.get("longName"),
                "Current Price": info.get("currentPrice"),
                "sector": info.get("sector"),
                "Industry": info.get("industry"),
                "Market Cap": info.get("marketCap"),
                "PE Ratio": info.get("trailingPE"),
                "52 Week High": info.get("fiftyTwoWeekHigh"),
                "52 Week Low": info.get("fiftyTwoWeekLow"),
                "Dividend Yield": info.get("dividendYield"),
                "Website": info.get("website")}

    except Exception as e:
        print(f"Error feching data for {symbol} : {e}")
        return {}
