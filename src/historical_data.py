# Imports from standard libraries
from datetime import datetime
import os
import shutil
import pandas as pd

# Imports from binance download libraries
from binance_data_download.download_kline import download_daily_klines
from binance_data_download.download_trade import download_daily_trades

# ----------------------------------------------- Utility functions -----------------------------------------------


def trade_data_collation(filename, symbol, limit_rows=False, nrows=50000):
    """
    Collates trade data from csv file into 10 second intervals

    :param nrows: The maximum number of rows imported (defaults to 50000)
    :param limit_rows: If set to true the number of rows imported is limited
    :param filename: the pathname of the csv files
    :param symbol: associated symbol of trade data
    """
    # Read CSV file
    if limit_rows:
        df = pd.read_csv(filename, compression='zip', header=None, sep=',', quotechar='"',
                         names=["tradeID", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"],
                         nrows=nrows)
    else:
        df = pd.read_csv(filename, compression='zip', header=None, sep=',', quotechar='"',
                             names=["tradeID", "price", "qty", "quoteQty", "time", "isBuyerMaker", "isBestMatch"])

    # Floors time to 10 seconds and then converts back to milliseconds
    df["time"] = df["time"].floordiv(10000) * 10000
    # Grouping data and suming and averaging necessary columns
    df = df.groupby("time", as_index=False).agg({'price': 'mean', 'qty': 'sum', 'quoteQty': 'sum'})
    # Add symbol column
    df["symbol"] = symbol
    # Return DataFrame
    return df


def downloaded_filepaths(type_, start_date, end_date, symbol_data_required):
    """
    Returns dictionary of downloaded data with key of filepath and value of (symbol, interval)

    :params type_: Either klines or trades, depending on the needed data
    :params start_date: The start date of the requested data
    :params end_date: The end date of the requested data
    :symbol_data_required: The symbols required for the backtest
    """

    # Getting list of relevant dates
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = pd.date_range(start_date, end_date, freq='d')

    # Iterating over required files and adding to dictionary
    file_format = "{}/test_data/binance/data/spot/daily/{}/{}/{}-{}-{}.zip"
    filepaths = dict()

    for symbol in symbol_data_required.keys():
        if len(symbol_data_required[symbol]) > 0:
            for interval in symbol_data_required[symbol]:
                for date in date_range:
                    date_format = date.strftime("%Y-%m-%d")
                    if type_ == "klines":
                        filepath = file_format.format(os.getcwd(), type_, "{}/{}".format(symbol, interval), symbol,
                                                      interval, date_format)
                    elif type_ == "trades":
                        filepath = file_format.format(os.getcwd(), type_, symbol, symbol, type_, date_format)
                    else:
                        raise ValueError("Tried to det filepaths of type that was not recognised: type={}".format(type_))
                    filepaths[filepath] = (symbol, interval)
        else:
            for date in date_range:
                date_format = date.strftime("%Y-%m-%d")
                if type_ == "trades":
                    filepath = file_format.format(os.getcwd(), type_, symbol, symbol, type_, date_format)
                filepaths[filepath] = (symbol, None)

    return filepaths

# ----------------------------------------------- Get Historical Data -----------------------------------------------


def get_binance_kline_data(start_date, end_date, symbol_data_required):
    """
    Used to get binance market data

    :param start_date: The start date of the data wanting the be obtained
    :param end_date: The finish date of the data wanting the be obtained
    :param symbol_data_required: Dictionary containing symbols as keys and list of intervals as values
    :return: Returns a pandas DataFrame of the data
    """
    # Headers for the CSV
    headers = ['open time', 'open', 'high', 'low', 'close', 'volume', 'close time', 'quote asset volume',
               'number of trades', 'taker buy asset volume', 'taker buy quote asset volume', 'ignore']

    # Creating DataFrame
    kline_data = pd.DataFrame()

    # Iterating over downloaded files
    filepaths = downloaded_filepaths("klines", start_date, end_date, symbol_data_required)
    for filepath in filepaths.keys():
        part_df = pd.read_csv(filepath, compression='zip', names=headers)
        part_df["symbol"] = filepaths[filepath][0]
        part_df["interval"] = filepaths[filepath][1]
        kline_data = kline_data.append(part_df)

    kline_data = kline_data.sort_values(by="close time")
    return kline_data


def get_binance_trade_data(start_date, end_date, symbols):
    """
    Used to get trade data and collate it into 10 second intervals
    - For now only uses established filenames

    :param symbols: List of symbols wanting to be received
    :param end_date: The end date
    :param start_date: The start date
    :return: Returns a pandas DataFrame of the data
    """
    # Initialize DataFrame
    trade_data = pd.DataFrame()

    # Changing symbols list to dictionary
    symbols_dict = dict()
    for symbol in symbols:
        symbols_dict[symbol] = []

    # Get filepaths dictionary
    filepaths = downloaded_filepaths("trades", start_date, end_date, symbols_dict)

    # Iterate through filepaths
    for filepath in filepaths.keys():
        # Importing data with debug features
        part_data = trade_data_collation(filepath, filepaths[filepath][0])
        trade_data = trade_data.append(part_data, ignore_index=True)

    # Return trade data
    return trade_data.sort_values(by="time")

# -------------------------------------------- Downloading Data Methods --------------------------------------------


def download_binance_trade_data(symbols: list, start_date, end_date):
    """
    Used to download trade data from Binance.

    :param start_date: The start date
    :param end_date: The end date
    :param symbols: list of symbols to be downloaded
    """
    print("\n----------------------------------- Downloading Historical Data -----------------------------------")

    trades_base_path = "{}/test_data/binance".format(os.getcwd())

    # for symbol in symbol_data_required.keys():
    # Get all dates between two dates
    dates = pd.date_range(start=start_date, end=end_date, freq='D').to_pydatetime().tolist()
    dates = [date.strftime("%Y-%m-%d") for date in dates]

    # Download daily data
    download_daily_trades(trading_type='spot', symbols=symbols, num_symbols=len(symbols), dates=dates,
                          start_date=start_date, end_date=end_date, folder=trades_base_path, checksum=0)

    print("\n----------------------------------- Finished Downloading Historical Data ---------"
          "--------------------------\n")


def download_binance_kline_data(symbol_data_required: dict, start_date, end_date):
    """
    Used to download kline data from Binance.

    :param start_date: The start date
    :param end_date: The end date
    :param symbol_data_required: Dictionary with symbols as keys and a list of required intervals as values
    """
    print("\n----------------------------------- Downloading Historical Data -----------------------------------")

    kline_base_path = "{}/test_data/binance/".format(os.getcwd())

    # for symbol in symbol_data_required.keys():
    # Get all dates between two dates
    dates = pd.date_range(start=start_date, end=end_date, freq='D').to_pydatetime().tolist()
    dates = [date.strftime("%Y-%m-%d") for date in dates]

    # Iterate through intervals
    for symbol, intervals in symbol_data_required.items():
        # Download interval data
        download_daily_klines(trading_type='spot', symbols=[symbol], num_symbols=1, intervals=intervals,
                              dates=dates, start_date=start_date, end_date=end_date, folder=kline_base_path,
                              checksum=0)

    print("\n----------------------------------- Finished Downloading Historical Data ---------"
          "--------------------------\n")

# --------------------------------------------- Delete Downloaded Data ---------------------------------------------


def delete_historical_data():
    """
    Deletes historical data used for the backtest
    """
    # Get path to delete
    path = "{}/test_data".format(os.getcwd())

    # Delete historical data
    print("Deleting historical data files")
    shutil.rmtree(path=path)
    print("Historical data deleted")


if __name__ == '__main__':
    download_binance_trade_data(['BTCUSDT', 'ADAUSDT'], start_date="2021-11-01", end_date="2021-11-02")
    download_binance_kline_data({'ADAUSDT': ['15m']}, start_date="2021-11-01", end_date="2021-11-02")
    print(get_binance_trade_data(start_date="2021-11-01", end_date="2021-11-02", symbols=["BTCUSDT", 'ADAUSDT']))
    print(get_binance_kline_data(start_date="2021-11-01", end_date="2021-11-02",
                                 symbol_data_required={"ADAUSDT": ['15m']}))
    # delete_historical_data()

