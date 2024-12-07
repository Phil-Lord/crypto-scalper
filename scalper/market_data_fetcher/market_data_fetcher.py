import requests
import time
import pandas as pd


class MarketDataFetcher:
    """
    Fetches historic market data.

    :param str base: The base currency code.
    :param str quote: The quote currency code.
    :param int interval: The amount of time to wait between performing the strategy (minutes).
    :param int hours: The number of hours to backtest for.
    :param int sma_long: The long Simple Moving Average window.
    """

    def __init__(self, base: str, quote: str, interval: int, hours: int, sma_long: int) -> None:
        """
        Constructor.
        """
        self.base = base
        self.quote = quote
        self.interval = interval
        self.hours = hours
        self.sma_long = sma_long

    def fetch_market_data(self) -> pd.DataFrame:
        """
        Fetches historic market data.
        """
        data = self.__get_data()
        if data["error"]:
            print("API Error:", data["error"])
            return pd.DataFrame()

        formatted_data = self.__format_data(data)
        return formatted_data

    def __get_data(self) -> dict:
        """
        Performs a GET request for OHLC data using the Kraken API.
        """
        # Get additional data for calculating long SMA
        # TODO: Make this work for any interval, I think it just works for minutely.
        required_data_points = self.sma_long + (self.hours * 60)
        since = int(time.time()) - (required_data_points * self.interval * 60)

        base_url = "https://api.kraken.com/0/public/OHLC"
        params = {
            "pair": self.base + self.quote,
            "interval": self.interval,
            "since": since
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f'HTTP request failed: {e}')

    def __format_data(self, data: dict) -> pd.DataFrame:
        """
        Extracts and formats OHLC json data into a pandas dataframe.

        :param dict data: The unformatted json market data.
        """
        pair_key = self.__getPairKey()
        ohlc_data = data['result'][pair_key]

        columns = ['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
        pd.set_option("mode.copy_on_write", True)  # Turn Copy on Write on globally.
        market_df = pd.DataFrame(ohlc_data, columns=columns)
        market_df['timestamp'] = pd.to_datetime(market_df['timestamp'], unit='s')
        market_df['close'] = pd.to_numeric(market_df['close'])
        return market_df

    def __getPairKey(self) -> str:
        """
        Gets a base/quote currency pair, formatted to match the Kraken API's json data key.
        """
        if self.base == 'DOGE':
            return 'XDGGBP'
        self.base = 'BT' if self.base == 'BTC' else self.base
        pair_key = (4 - len(self.base)) * 'X' + self.base + 'Z' + self.quote
        return pair_key
