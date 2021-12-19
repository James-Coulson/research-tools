# imports
import os, sys, re, shutil
import json
from pathlib import Path
from datetime import *
import urllib.request
from argparse import ArgumentParser, RawTextHelpFormatter, ArgumentTypeError
import pandas as pd

# ----------------------------------------------------------------------------------------------------------------------
# --------------------------------------- binance_data_download\enums.py -----------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

YEARS = ['2017', '2018', '2019', '2020', '2021']
INTERVALS = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1mo"]
DAILY_INTERVALS = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"]
TRADING_TYPE = ["spot", "um", "cm"]
MONTHS = list(range(1,13))
MAX_DAYS = 35
BASE_URL = 'https://data.binance.vision/'
START_DATE = date(int(YEARS[0]), MONTHS[0], 1)
END_DATE = datetime.date(datetime.now())

# ----------------------------------------------------------------------------------------------------------------------
# --------------------------------------- binance_data_download\utility.py ---------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def get_destination_dir(file_url, folder=None):
    store_directory = os.environ.get('STORE_DIRECTORY')
    if folder:
        store_directory = folder
    if not store_directory:
        store_directory = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(store_directory, file_url)


def get_download_url(file_url):
    return "{}{}".format(BASE_URL, file_url)


def get_all_symbols(type):
    if type == 'um':
        response = urllib.request.urlopen("https://fapi.binance.com/fapi/v1/exchangeInfo").read()
    elif type == 'cm':
        response = urllib.request.urlopen("https://dapi.binance.com/dapi/v1/exchangeInfo").read()
    else:
        response = urllib.request.urlopen("https://api.binance.com/api/v3/exchangeInfo").read()
    return list(map(lambda symbol: symbol['symbol'], json.loads(response)['symbols']))


def download_file(base_path, file_name, date_range=None, folder=None):
    download_path = "{}{}".format(base_path, file_name)
    if folder:
        base_path = os.path.join(folder, base_path)
    # if date_range:
    #   date_range = date_range.replace(" ","_")
    #   base_path = os.path.join(base_path, date_range)
    save_path = get_destination_dir(os.path.join(base_path, file_name), folder)

    if os.path.exists(save_path):
        print("\nfile already exists! {}".format(save_path))
        return

    # make the directory
    if not os.path.exists(base_path):
        Path(get_destination_dir(base_path)).mkdir(parents=True, exist_ok=True)

    try:
        download_url = get_download_url(download_path)
        dl_file = urllib.request.urlopen(download_url)
        length = dl_file.getheader('content-length')
        if length:
            length = int(length)
            blocksize = max(4096, length // 100)

        with open(save_path, 'wb') as out_file:
            dl_progress = 0
            print("\nFile Download: {}".format(save_path))
            while True:
                buf = dl_file.read(blocksize)
                if not buf:
                    break
                dl_progress += len(buf)
                out_file.write(buf)
                done = int(50 * dl_progress / length)
                sys.stdout.write("\r[%s%s]" % ('#' * done, '.' * (50 - done)))
                sys.stdout.flush()

    except urllib.error.HTTPError:
        print("\nFile not found: {}".format(download_url))
        pass


def convert_to_date_object(d):
    year, month, day = [int(x) for x in d.split('-')]
    date_obj = date(year, month, day)
    return date_obj


def get_start_end_date_objects(date_range):
    start, end = date_range.split()
    start_date = convert_to_date_object(start)
    end_date = convert_to_date_object(end)
    return start_date, end_date


def match_date_regex(arg_value, pat=re.compile(r'\d{4}-\d{2}-\d{2}')):
    if not pat.match(arg_value):
        raise ArgumentTypeError
    return arg_value


def check_directory(arg_value):
    if os.path.exists(arg_value):
        while True:
            option = input('Folder already exists! Do you want to overwrite it? y/n  ')
            if option != 'y' and option != 'n':
                print('Invalid Option!')
                continue
            elif option == 'y':
                shutil.rmtree(arg_value)
                break
            else:
                break
    return arg_value


def get_path(trading_type, market_data_type, time_period, symbol, interval=None):
    trading_type_path = 'data/spot'
    if trading_type != 'spot':
        trading_type_path = f'data/futures/{trading_type}'
    if interval is not None:
        path = f'{trading_type_path}/{time_period}/{market_data_type}/{symbol.upper()}/{interval}/'
    else:
        path = f'{trading_type_path}/{time_period}/{market_data_type}/{symbol.upper()}/'
    return path


def get_parser(parser_type):
    parser = ArgumentParser(description=("This is a script to download historical {} data").format(parser_type),
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        '-s', dest='symbols', nargs='+',
        help='Single symbol or multiple symbols separated by space')
    parser.add_argument(
        '-y', dest='years', default=YEARS, nargs='+', choices=YEARS,
        help='Single year or multiple years separated by space\n-y 2019 2021 means to download {} from 2019 and 2021'.format(
            parser_type))
    parser.add_argument(
        '-m', dest='months', default=MONTHS, nargs='+', type=int, choices=MONTHS,
        help='Single month or multiple months separated by space\n-m 2 12 means to download {} from feb and dec'.format(
            parser_type))
    parser.add_argument(
        '-d', dest='dates', nargs='+', type=match_date_regex,
        help='Date to download in [YYYY-MM-DD] format\nsingle date or multiple dates separated by space\ndownload past 35 days if no argument is parsed')
    parser.add_argument(
        '-startDate', dest='startDate', type=match_date_regex,
        help='Starting date to download in [YYYY-MM-DD] format')
    parser.add_argument(
        '-endDate', dest='endDate', type=match_date_regex,
        help='Ending date to download in [YYYY-MM-DD] format')
    parser.add_argument(
        '-folder', dest='folder', type=check_directory,
        help='Directory to store the downloaded data')
    parser.add_argument(
        '-c', dest='checksum', default=0, type=int, choices=[0, 1],
        help='1 to download checksum file, default 0')
    parser.add_argument(
        '-t', dest='type', default='spot', choices=TRADING_TYPE,
        help='Valid trading types: {}'.format(TRADING_TYPE))

    if parser_type == 'klines':
        parser.add_argument(
            '-i', dest='intervals', default=INTERVALS, nargs='+', choices=INTERVALS,
            help='single kline interval or multiple intervals separated by space\n-i 1m 1w means to download klines interval of 1minute and 1week')

    return parser

# ----------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- binance_data_download\download_kline.py -------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def download_monthly_klines(trading_type, symbols, num_symbols, intervals, years, months, start_date, end_date, folder, checksum):
  current = 0
  date_range = None

  if start_date and end_date:
    date_range = start_date + " " + end_date

  if not start_date:
    start_date = START_DATE
  else:
    start_date = convert_to_date_object(start_date)

  if not end_date:
    end_date = END_DATE
  else:
    end_date = convert_to_date_object(end_date)

  print("Found {} symbols".format(num_symbols))

  for symbol in symbols:
    print("[{}/{}] - start download monthly {} klines ".format(current+1, num_symbols, symbol))
    for interval in intervals:
      for year in years:
        for month in months:
          current_date = convert_to_date_object('{}-{}-01'.format(year, month))
          if current_date >= start_date and current_date <= end_date:
            path = get_path(trading_type, "klines", "monthly", symbol, interval)
            file_name = "{}-{}-{}-{}.zip".format(symbol.upper(), interval, year, '{:02d}'.format(month))
            download_file(path, file_name, date_range, folder)

            if checksum == 1:
              checksum_path = get_path(trading_type, "klines", "monthly", symbol, interval)
              checksum_file_name = "{}-{}-{}-{}.zip.CHECKSUM".format(symbol.upper(), interval, year, '{:02d}'.format(month))
              download_file(checksum_path, checksum_file_name, date_range, folder)

    current += 1


def download_daily_klines(trading_type, symbols, num_symbols, intervals, dates, start_date, end_date, folder, checksum):
  current = 0
  date_range = None

  if start_date and end_date:
    date_range = start_date + " " + end_date

  if not start_date:
    start_date = START_DATE
  else:
    start_date = convert_to_date_object(start_date)

  if not end_date:
    end_date = END_DATE
  else:
    end_date = convert_to_date_object(end_date)

  #Get valid intervals for daily
  intervals = list(set(intervals) & set(DAILY_INTERVALS))
  print("Found {} symbols".format(num_symbols))

  for symbol in symbols:
    print("[{}/{}] - start download daily {} klines ".format(current+1, num_symbols, symbol))
    for interval in intervals:
      for date in dates:
        current_date = convert_to_date_object(date)
        if current_date >= start_date and current_date <= end_date:
          path = get_path(trading_type, "klines", "daily", symbol, interval)
          file_name = "{}-{}-{}.zip".format(symbol.upper(), interval, date)
          download_file(path, file_name, date_range, folder)

          if checksum == 1:
            checksum_path = get_path(trading_type, "klines", "daily", symbol, interval)
            checksum_file_name = "{}-{}-{}.zip.CHECKSUM".format(symbol.upper(), interval, date)
            download_file(checksum_path, checksum_file_name, date_range, folder)

    current += 1

# ----------------------------------------------------------------------------------------------------------------------
# ---------------------------------------- binance_data_download\download_trade.py -------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def download_monthly_trades(trading_type, symbols, num_symbols, years, months, start_date, end_date, folder, checksum):
    current = 0
    date_range = None

    if start_date and end_date:
        date_range = start_date + " " + end_date

    if not start_date:
        start_date = START_DATE
    else:
        start_date = convert_to_date_object(start_date)

    if not end_date:
        end_date = END_DATE
    else:
        end_date = convert_to_date_object(end_date)

    print("Found {} symbols".format(num_symbols))

    for symbol in symbols:
        print("[{}/{}] - start download monthly {} trades ".format(current + 1, num_symbols, symbol))
        for year in years:
            for month in months:
                current_date = convert_to_date_object('{}-{}-01'.format(year, month))
                if current_date >= start_date and current_date <= end_date:
                    path = get_path(trading_type, "trades", "monthly", symbol)
                    file_name = "{}-trades-{}-{}.zip".format(symbol.upper(), year, '{:02d}'.format(month))
                    download_file(path, file_name, date_range, folder)

                    if checksum == 1:
                        checksum_path = get_path(trading_type, "trades", "monthly", symbol)
                        checksum_file_name = "{}-trades-{}-{}.zip.CHECKSUM".format(symbol.upper(), year,
                                                                                   '{:02d}'.format(month))
                        download_file(checksum_path, checksum_file_name, date_range, folder)

        current += 1


def download_daily_trades(trading_type, symbols, num_symbols, dates, start_date, end_date, folder, checksum):
    current = 0
    date_range = None

    if start_date and end_date:
        date_range = start_date + " " + end_date

    if not start_date:
        start_date = START_DATE
    else:
        start_date = convert_to_date_object(start_date)

    if not end_date:
        end_date = END_DATE
    else:
        end_date = convert_to_date_object(end_date)

    print("Found {} symbols".format(num_symbols))

    for symbol in symbols:
        print("[{}/{}] - start download daily {} trades ".format(current + 1, num_symbols, symbol))
        for date in dates:
            current_date = convert_to_date_object(date)
            if current_date >= start_date and current_date <= end_date:
                path = get_path(trading_type, "trades", "daily", symbol)
                file_name = "{}-trades-{}.zip".format(symbol.upper(), date)
                download_file(path, file_name, date_range, folder)

                if checksum == 1:
                    checksum_path = get_path(trading_type, "trades", "daily", symbol)
                    checksum_file_name = "{}-trades-{}.zip.CHECKSUM".format(symbol.upper(), date)
                    download_file(checksum_path, checksum_file_name, date_range, folder)

# ----------------------------------------------------------------------------------------------------------------------
# ------------------------------------ binance_data_download\download_aggTrade.py --------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

def download_monthly_aggTrades(trading_type, symbols, num_symbols, years, months, start_date, end_date, folder,
                               checksum):
    current = 0
    date_range = None

    if start_date and end_date:
        date_range = start_date + " " + end_date

    if not start_date:
        start_date = START_DATE
    else:
        start_date = convert_to_date_object(start_date)

    if not end_date:
        end_date = END_DATE
    else:
        end_date = convert_to_date_object(end_date)

    print("Found {} symbols".format(num_symbols))

    for symbol in symbols:
        print("[{}/{}] - start download monthly {} aggTrades ".format(current + 1, num_symbols, symbol))
        for year in years:
            for month in months:
                current_date = convert_to_date_object('{}-{}-01'.format(year, month))
                if current_date >= start_date and current_date <= end_date:
                    path = get_path(trading_type, "aggTrades", "monthly", symbol)
                    file_name = "{}-aggTrades-{}-{}.zip".format(symbol.upper(), year, '{:02d}'.format(month))
                    download_file(path, file_name, date_range, folder)

                    if checksum == 1:
                        checksum_path = get_path(trading_type, "aggTrades", "monthly", symbol)
                        checksum_file_name = "{}-aggTrades-{}-{}.zip.CHECKSUM".format(symbol.upper(), year,
                                                                                      '{:02d}'.format(month))
                        download_file(checksum_path, checksum_file_name, date_range, folder)

        current += 1


def download_daily_aggTrades(trading_type, symbols, num_symbols, dates, start_date, end_date, folder, checksum):
    current = 0
    date_range = None

    if start_date and end_date:
        date_range = start_date + " " + end_date

    if not start_date:
        start_date = START_DATE
    else:
        start_date = convert_to_date_object(start_date)

    if not end_date:
        end_date = END_DATE
    else:
        end_date = convert_to_date_object(end_date)

    print("Found {} symbols".format(num_symbols))

    for symbol in symbols:
        print("[{}/{}] - start download daily {} aggTrades ".format(current + 1, num_symbols, symbol))
        for date in dates:
            current_date = convert_to_date_object(date)
            if current_date >= start_date and current_date <= end_date:
                path = get_path(trading_type, "aggTrades", "daily", symbol)
                file_name = "{}-aggTrades-{}.zip".format(symbol.upper(), date)
                download_file(path, file_name, date_range, folder)

                if checksum == 1:
                    checksum_path = get_path(trading_type, "aggTrades", "daily", symbol)
                    checksum_file_name = "{}-aggTrades-{}.zip.CHECKSUM".format(symbol.upper(), date)
                    download_file(checksum_path, checksum_file_name, date_range, folder)

        current += 1

# ----------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------- historical_data.py -------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

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
