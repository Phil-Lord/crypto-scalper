import requests
import datetime
import time
import matplotlib.pyplot as plt


def get_historical_price_data(tradeable, since, until):
    needMoreData = True
    last = since
    data = []
    url = "https://api.kraken.com/0/public/Trades"

    while needMoreData:
        params = {
            "pair": tradeable,
            "since": last
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        batch = response.json()

        if batch['error'] == ['EGeneral:Too many requests']:
            print('Too many calls! Waiting!')
            time.sleep(1)
            continue

        last = int(batch['result']['last'])
        trades = batch['result']['XXBTZGBP']

        if last > until:
            for i in range(len(trades)):
                if trades[i][2] <= until:
                    data.append(trades[i])
                else:
                    break
            needMoreData = False
        else:
            data.extend(trades)

        print('Fetching batch...')

    return data


def format_price_data(data):
    formatted_trades = []
    for trade in data:
        if trade[4] == 'm':
            formatted_trades.append({
                'timestamp': datetime.datetime.fromtimestamp(trade[2]),
                'price': float(trade[0])
            })

    return formatted_trades


def plot_price_data(trades):
    timestamps = []
    prices = []
    for trade in trades:
        timestamps.append(trade['timestamp'])
        prices.append(trade['price'])

    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, prices, label="Price (GBP)")
    plt.xlabel("Date")
    plt.ylabel("Price (GBP)")
    plt.title("BTC/GBP Historical Prices")
    plt.legend()
    plt.grid()
    plt.show()


tradeable = "BTCGBP"

since = datetime.datetime(2024, 11, 28, 0, 0, 0)
since = int(time.mktime(since.timetuple()) * 1000000000)

until = datetime.datetime(2024, 12, 5, 22, 0, 0)
until = int(time.mktime(until.timetuple()) * 1000000000)

data = get_historical_price_data(tradeable, since, until)
trades = format_price_data(data)
plot_price_data(trades)
