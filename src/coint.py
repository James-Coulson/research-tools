import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen, JohansenTestResult
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from historical_data import download_binance_trade_data, download_binance_kline_data, get_binance_kline_data, get_binance_trade_data, delete_historical_data

# ------------------------------------------- Classes -------------------------------------------


class CointResult:
    """
    Class used to hold and interpret johansen test result
    """
    def __init__(self, test_result: JohansenTestResult, symbols: dict, interval: str, start_date: str, end_date: str):
        """
        Initializes class

        :param test_result: The test result of the Johansen test
        :param start_date: The start date
        :param end_date: The end date
        """
        self.test_result = test_result
        self.symbols = symbols
        self.interval = interval
        self.start_date = start_date
        self.end_date = end_date

    # ----------------- Printing Results --------------------

    def print_trace_statistics(self):
        """
        Prints the trace statistics
        """
        print("\nTrace statistics")
        print("              Trace stats          90%      95%      99%")
        count = 0
        for symbol in self.symbols:
            print("r={}  var{}    {}  {}".format(count, count+1, self.test_result.lr1[count], self.test_result.cvt[count]))
            count += 1

    def print_eigenvalue_statistics(self):
        """
        Prints the eigenvalue statistics
        """
        print("\nEigenvalue statistics")
        print("              Eigenvalue stats    90%      95%      99%")
        count = 0
        for symbol in self.symbols:
            print("r={}  var{}    {}  {}".format(count, count+1, self.test_result.lr2[count], self.test_result.cvm[count]))
            count += 1

    def print_hedge_ratio(self):
        """
        Prints hedge ratio
        """
        print("\nHedge ratio")
        vec_count = 1
        for vec in self.test_result.evec:
            print("Eigenvector {}".format(vec_count))
            vec_count += 1

            count = 0
            for symbol in self.symbols:
                print("{}: {}".format(symbol, vec[count]))
                count += 1

    # ----------------- Graphing Methods -----------------

    def get_coint_plot(self, include_all_evecs=False, include_underlying=False, evec=0):
        """
        Gets to plot of the cointegration

        :param include_underlying: If the underlying timeseries should be added as subplots (default: False)
        :param include_all_evecs: Includes all possible cointegrating combinations (default: False)
        :param evec: Which eigenvector to use (default: 0)
        :return: Figure of cointegration
        """
        # Define coint DataFrame
        coint = pd.DataFrame()

        # Counter variable
        count = 0

        # Calculating coint
        if not include_all_evecs:
            for symbol in self.symbols:
                # Get kline data
                data = get_binance_kline_data(symbol_data_required={symbol: [self.interval]}, start_date=self.start_date,
                                              end_date=self.end_date)

                # Initialize coint
                if 'price' not in coint.columns:
                    coint['time'] = data['close time']
                    coint['price'] = data['close'] * self.test_result.evec[evec][count]
                    count += 1
                    continue

                # Add price to coint and increment counter
                coint['price'] = coint['price'] + data['close'] * self.test_result.evec[evec][count]
                count += 1
        else:
            for symbol in self.symbols:
                # Get kline data
                data = get_binance_kline_data(symbol_data_required={symbol: [self.interval]},
                                              start_date=self.start_date,
                                              end_date=self.end_date)

                # Initialize coint
                if 'price_0' not in coint.columns:
                    coint['time'] = data['close time']
                    for i in range(len(self.symbols)):
                        coint['price_{}'.format(i)] = data['close'] * self.test_result.evec[i][count]
                    count += 1
                    continue

                # Add price to coint and increment counter
                for i in range(len(self.symbols)):
                    coint['price_{}'.format(i)] = data['close'] * self.test_result.evec[i][count]
                count += 1

        # If only the cointegrating asset should be plotted
        if include_underlying is False:
            if not include_all_evecs:
                fig = make_subplots(rows=1, cols=1, x_title='Time (UNIX)', y_title='Price')
                fig.append_trace(go.Scatter(x=coint['time'], y=coint['price'], name="{}".format('Cointegrating')),
                                 row=1, col=1)
            else:
                fig = make_subplots(rows=len(self.symbols), cols=1, x_title='Time (UNIX)', y_title='Price')
                for i in range(len(self.symbols)):
                    fig.append_trace(go.Scatter(x=coint['time'], y=coint['price_{}'.format(i)], name="{}".format('Cointegrating ({})'.format(i))),
                                     row=i+1, col=1)
            return fig

        # Adding cointegrating to plot
        if not include_all_evecs:
            fig = make_subplots(rows=len(self.symbols)+1, cols=1, x_title='Time (UNIX)', y_title='Price')
            fig.append_trace(go.Scatter(x=coint['time'], y=coint['price'], name="{}".format('Cointegrating')),
                             row=1, col=1)
            # Define counter
            count = 2
        else:
            fig = make_subplots(rows=len(self.symbols)*2, cols=1, x_title='Time (UNIX)', y_title='Price')
            for i in range(len(self.symbols)):
                fig.append_trace(go.Scatter(x=coint['time'], y=coint['price_{}'.format(i)],
                                            name="{}".format('Cointegrating ({})'.format(i))),
                                 row=i+1, col=1)
            # Define counter
            count = len(self.symbols) + 1

        # Adding underlying to plot
        for symbol in self.symbols:
            # Get kline data
            data = get_binance_kline_data(symbol_data_required={symbol: [self.interval]}, start_date=self.start_date,
                                          end_date=self.end_date)

            # Add to figure and increment counter
            fig.append_trace(go.Scatter(x=data['close time'], y=data['close'], name="{}".format(symbol)), row=count, col=1)
            count += 1

        # Return figure
        return fig

# ------------------------------------------- Cointegration Tests -------------------------------------------


def test_coint_johansen(symbols, interval: str, start_date: str, end_date: str, def_order=0, k_ar_diff=3) -> CointResult:
    """
    Performs a Johansen test

    :param symbols: List of symbols
    :param start_date: The start date
    :param end_date: The end date
    :param def_order: TBH I dont know what this does (default: 0)
    :param k_ar_diff: Number of lagged differences in the model (default: 3)
    :return: Returns CointResult class
    """
    # DataFrame to store close data
    close_data = pd.DataFrame()

    # Adding data to close_data
    for symbol in symbols:
        # Get kline data
        data = get_binance_kline_data(symbol_data_required={symbol: [interval]}, start_date=start_date, end_date=end_date)

        # Add close data to close_data
        close_data[symbol] = data['close']

    # Perform Johansen test
    result = coint_johansen(close_data, def_order, k_ar_diff)

    # Returning CointResult
    return CointResult(test_result=result, symbols=symbols, interval=interval, start_date=start_date, end_date=end_date)