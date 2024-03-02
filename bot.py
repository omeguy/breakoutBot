import numpy as np
import MetaTrader5 as mt5
import matplotlib.pyplot as plt
from meta_bot import MT5Connector, DataFetcher
import pandas as pd
from scipy.signal import argrelextrema
from sklearn.cluster import KMeans


from collections import Counter


class Bot:
    def __init__(self, mt5_connector, datafetcher, symbol, timeframe, from_data, to_data):  
        self.mt5_connector = mt5_connector 
        self.datafetcher = datafetcher
        self.symbol = symbol
        self.timeframe = timeframe
        self.from_data = from_data
        self.to_data = to_data



    def identify_support_resistance(self, n_clusters):
        # Fetch historical data
        data = self.datafetcher.fetch()

        # Convert into numpy arrays
        highs = np.array(data['high']).reshape(-1,1)
        lows = np.array(data['low']).reshape(-1,1)

        # Combine highs and lows
        price_levels = np.concatenate([highs, lows])

        # Apply K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters)
        kmeans.fit(price_levels)

        # Fetch the respective price levels (cluster centers)
        support_resistance_levels = kmeans.cluster_centers_

        # Print the support and resistance levels
        print(support_resistance_levels)

        # Create a figure and a set of subplots
        fig, ax = plt.subplots()

        # Plot the close price
        ax.plot(data['close'], label='Close price')

        # Plot the support and resistance levels
        for level in support_resistance_levels:
            ax.hlines(level, xmin=0, xmax=len(data['close']), colors='g', linestyles='dashed', label='Support/Resistance')

        # Display the legend
        ax.legend()

        plt.show()



            

    def run(self):
        self.identify_support_resistance(n_clusters=10) # for example
