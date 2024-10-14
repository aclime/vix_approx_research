import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
from datetime import datetime
from datetime import timedelta

est = pytz.timezone('US/Eastern')
fmt = '%Y-%m-%d %H:%M:%S %Z%z'
now = datetime.today().astimezone(est).strftime(fmt)

ticker = "TSLA"         # ticker to pull


def pull_latest_data(underlying_ticker,maturity):
    kind = "call"       # call or put
    #maturity = 4        # option maturity in order of maturities trading (weeks apart)
    tick = yf.Ticker(underlying_ticker.upper())

    # Get maturity date
    #print(tick.options)
    date=maturity
    #date = tick.options[4]
    #date = tick.options[maturity]
    #tick.options[maturity]
    #date=tick.options[0] #most recent matruity date

    # Pull options data
    df = (
        tick.option_chain(date).calls
        if kind == "call"
        else tick.option_chain(date).puts
    )
    df.lastTradeDate = df.lastTradeDate.map(
        lambda x: x.astimezone(est).strftime(fmt)
    )
    df['maturity']=date
    return df

def pull_history_data(contract_symbol, days_before_expiration=30):
    option = yf.Ticker(contract_symbol)
    option_info = option.info
    option_expiration_date = datetime.fromtimestamp(option_info["expireDate"])
    start_date = option_expiration_date - timedelta(days=days_before_expiration)
    option_history = option.history(start=start_date)
    option_history['contractSymbol']=contract_symbol
    option_history['expiration']=option_expiration_date
    option_history.reset_index(inplace=True)
    return option_history

def agg_hist_data(df):
    return pd.concat([get_option_history_data(i) for i in df.contractSymbol])