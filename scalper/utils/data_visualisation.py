import matplotlib.pyplot as plt
import pandas as pd


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
