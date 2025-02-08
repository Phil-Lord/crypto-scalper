import matplotlib.pyplot as plt
import pandas as pd


def plot_position_profits(position_profits: pd.DataFrame) -> None:
    plt.figure(figsize=(10, 5))
    plt.bar(position_profits.index, position_profits["profit"], color=[
            "green" if p >= 0 else "red" for p in position_profits["profit"]])
    plt.axhline(0, color="black", linewidth=1)
    plt.xlabel("Trade Index")
    plt.ylabel("Profit per Position (Quote Currency)")
    plt.title("Profit per Position")
    plt.show()


def plot_sma_results(results: pd.DataFrame, pair: str) -> None:
    # Extract buys and sells.
    buys = results[results["signal"] == "buy"]
    sells = results[results["signal"] == "sell"]

    plt.figure(figsize=(12, 6))

    # Plot price.
    plt.plot(results.index, results["price"], label="Price", color="blue", alpha=0.4)

    # Plot SMAs.
    plt.plot(
        results.index,
        results['short_sma'],
        label='Short SMA',
        color='purple',
        linestyle='--'
    )
    plt.plot(
        results.index,
        results['long_sma'],
        label='Long SMA',
        color='green',
        linestyle='--'
    )

    # Plot buys and sells.
    plt.scatter(buys.index, buys["price"], color="green",
                label="Buy Signal", marker="^", alpha=1, s=100)
    plt.scatter(sells.index, sells["price"], color="red",
                label="Sell Signal", marker="v", alpha=1, s=100)

    # Titles, legends, etc.
    plt.title(f"Price Movement for {pair}")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.show()


def plot_trade_data_from_db(trades: pd.DataFrame) -> None:
    trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s")

    plt.figure(figsize=(10, 5))
    plt.plot(
        trades['timestamp'],
        trades['price'],
        label='Trade Price',
        color='blue'
    )
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.title("Trade Prices Over Time")
    plt.legend()
    plt.grid()
    plt.show()
