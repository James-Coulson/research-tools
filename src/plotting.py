# Standard imports
import matplotlib.pyplot as plt
import mplfinance as mpf
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# User-made imports
from historical_data import get_binance_trade_data, get_binance_kline_data, download_binance_trade_data, download_binance_kline_data, delete_historical_data

# ------------------------------------ Plotting Trade Data ------------------------------------


def get_trade_data_plot(symbols: list, start_date: str, end_date: str):
    """
    Used to plot basic trade data downloaded

    :param symbols: Symbols to be plotted
    :param start_date: The start date
    :param end_date: The end date
    :return: Returns plot
    """
    # Check if more than one symbol is being printed
    if len(symbols) > 1:
        # Make subplot figure
        fig = make_subplots(rows=len(symbols), cols=1, x_title='Time (UNIX)', y_title='Price')

        # row counter
        row_count = 1

        # Iterate through symbols
        for symbol in symbols:
            # Get trade data
            trade_data = get_binance_trade_data(start_date=start_date, end_date=end_date, symbols=[symbol])

            # Add plot to figure and increment row count
            fig.append_trace(go.Scatter(x=trade_data['time'], y=trade_data['price'], name="{}".format(symbol)), row=row_count, col=1)
            row_count += 1

        # Update title and print output
        # fig.update_layout(title_text="Trade data")
        return fig
    else:
        # Create figure
        fig = px.line(get_binance_trade_data(start_date=start_date, end_date=end_date, symbols=[symbols[0]]), x='time',
                      y='price')
        return fig

# ------------------------------------ Plotting Kline Data ------------------------------------


def get_kline_data_plot(symbols_intervals: list, start_date: str, end_date: str):
    """
    Used to plot kline data from

    :param symbols_intervals: List containing tuples of the form (symbol, interval)
    :param start_date: The start date
    :param end_date: The end date
    :return: Returns plot
    """
    fig = make_subplots(rows=len(symbols_intervals))
    row_count = 1
    for (symbol, interval) in symbols_intervals:
        kline_data = get_binance_kline_data(start_date=start_date, end_date=end_date, symbol_data_required={symbol: [interval]})
        fig_temp = go.Candlestick(x=kline_data['close time'], open=kline_data['open'], high=kline_data['high'],
                                     low=kline_data['low'], close=kline_data['close'])
        fig.add_trace(fig_temp, row=row_count, col=1)
        row_count += 1

    fig.update_xaxes(rangeslider_visible=False)

    return fig


if __name__ == '__main__':
    download_binance_trade_data(symbols=['BTCUSDT', 'ADAUSDT'], start_date="2021-11-01", end_date="2021-11-02")
    download_binance_kline_data(symbol_data_required={'BTCUSDT': ['15m', '1m']}, start_date="2021-11-01", end_date="2021-11-02")
    # plot_trade_data(symbols=['BTCUSDT', 'ADAUSDT'], start_date="2021-11-01", end_date="2021-11-02")
    get_kline_data_plot(start_date="2021-11-01", end_date="2021-11-02", symbols_intervals=[('BTCUSDT', '15m'), ('BTCUSDT', '1m')]).write_html("./outputs/kline_data.html", auto_open=True)
    # delete_historical_data()
