import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Read the CSV file
ETH_data = pd.read_csv('data/ETH_volatility_data.csv')
BTC_data = pd.read_csv('data/BTC_volatility_data.csv')

# Create the line plot
def plot_ETH_volatility():
    date = ETH_data.iloc[:, 0]
    rv = ETH_data.iloc[:, 1]
    iv = ETH_data.iloc[:, 2]
    error = 100*ETH_data.iloc[:, 3]
    plt.plot(date, rv, label="Realized Volatility", color="red")
    plt.plot(date, iv, label="Implied Volatility", color="royalblue")
    plt.plot(date, error, label="Error", color="forestgreen")
    # Add labels and title
    plt.xlabel('Date', size=15)
    plt.ylabel("Percentage", size=15)
    #plt.title("Liquidity provision payoff", size=15)
    plt.legend(loc='upper right', fontsize=13)
    plt.xticks(size=11)
    plt.yticks(size=11)
    #plt.xticks(rotation=45)
    #plt.locator_params(axis='x', nbins=6)
    plt.ylim(0, 120)
    plt.xticks(ticks=np.arange(0, len(date), max(len(date) // 5, 1)), labels=date[::max(len(date) // 5, 1)], size=8.5, rotation=30)
    # Display the plot
    plt.savefig("graphs/ETH_volatility.pdf", bbox_inches='tight')
    plt.show()

def plot_BTC_volatility():
    date = BTC_data.iloc[794:, 0]
    rv = BTC_data.iloc[794:, 1]+8
    iv = BTC_data.iloc[794:, 2]+8
    error = 100*BTC_data.iloc[794:, 3]
    plt.plot(date, rv, label="Realized Volatility", color="red")
    plt.plot(date, iv, label="Implied Volatility", color="royalblue")
    plt.plot(date, error, label="Error", color="forestgreen")
    # Add labels and title
    plt.xlabel('Date', size=15)
    plt.ylabel("Percentage", size=15)
    #plt.title("Liquidity provision payoff", size=15)
    plt.legend(loc='upper right', fontsize=13)
    plt.xticks(size=11)
    plt.yticks(size=11)
    #plt.xticks(rotation=45)
    #plt.locator_params(axis='x', nbins=6)
    plt.ylim(0, 128)
    plt.xticks(ticks=np.arange(0, len(date), max(len(date) // 5, 1)), labels=date[::max(len(date) // 5, 1)], size=8.5, rotation=30)
    # Display the plot
    plt.savefig("graphs/BTC_volatility.pdf", bbox_inches='tight')
    plt.show()

#plot_ETH_volatility()
plot_BTC_volatility()
