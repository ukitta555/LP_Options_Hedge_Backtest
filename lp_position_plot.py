import matplotlib.pyplot as plt
import numpy as np
l = 1
price_low = 80
price_high = 120
strike = 100
# Generate some sample data
price = np.linspace(1, 200, 1000)
lp_position = price*(np.maximum(l/np.sqrt(np.maximum(price, price_low))-l/np.sqrt(price_high), 0)) + np.maximum(l*(np.sqrt(np.minimum(price, price_high))-np.sqrt(price_low)), 0)
put_position = (l/np.sqrt(price_low)-l/np.sqrt(price_high))*np.maximum(strike - price, 0)
#print(np.maximum(l/np.sqrt(price)-l/np.sqrt(price_high),0))
# Create the line plot
def plot_liquidity():
    plt.plot(price, lp_position, label="LP payoff")
    plt.axvline(x=price_low, linestyle='--', color='red', label="Lower range")
    plt.axvline(x=price_high, linestyle='--', color='green', label="Upper range")
    # Add labels and title
    plt.xlabel('Price', size=15)
    plt.ylabel("Payoff", size=15)
    #plt.title("Liquidity provision payoff", size=15)
    plt.legend(loc='center right', fontsize=13)
    plt.xticks(size=11)
    plt.yticks(size=11)
    # Display the plot
    plt.savefig("lp_position.pdf")
    plt.show()

def plot_liquidity_put_payoff():
    plt.plot(price, lp_position, label="LP payoff")
    plt.plot(price, put_position, label="Put payoff", color="green")
    plt.plot(price, lp_position + put_position, label="Zero-loss payoff", linestyle="--", color="orange")

    # Add labels and title
    plt.xlabel('Price', size=15)
    plt.ylabel("Payoff", size=15)
    #plt.title("Zero-loss liquidity provision", size=15)
    plt.legend(loc='center right', fontsize=13)
    plt.xticks(size=11)
    plt.yticks(size=11)
    # Display the plot
    plt.savefig("lp_position_put_payoff.pdf")
    plt.show()

plot_liquidity_put_payoff()
#plot_liquidity()
