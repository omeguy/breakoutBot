import MetaTrader5 as mt5
from datetime import datetime
import numpy as np
import pandas as pd
import requests
import json

import random
import schedule
import time

class MT5Connector:
    def __init__(self, account, password, server):
        self.account = account
        self.password = password
        self.server = server
        self.is_connected = False

    def connect(self, max_retries=3):
        for i in range(max_retries):
            try:
                is_initialized = mt5.initialize()
                print("-------------------------------")
                print('initialize:', is_initialized)
                
                # Try to authorize with provided account, password and server
                authorized = mt5.login(self.account, self.password, self.server)
                if authorized:
                    print("----------------------------")
                    print('logged in: ', authorized)
                    self.is_connected = True
                    break
            except Exception as e:
                print("----------------------------------------")
                print(f"Failed to connect to MT5 server: {e}")
                if i < max_retries - 1:  # i is zero indexed
                    print("Retrying...")
                else:
                    print("-----------------------------------")
                    print("Max retries reached. Giving up.")

    def disconnect(self):
        # Disconnect from the MT5 platform
        if self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            print("-------------------------")
            print("Disconnected from MT5")

class MarketStatus:
    def __init__(self, mt5_connector):
        self.mt5_connector = mt5_connector
        self.is_market_open = self.check_market_open()

    def check_market_open(self):
        #Check if the market is open
        current_time = datetime.utcnow()
        current_day_of_week = current_time.weekday()
        current_hour = current_time.hour

        # if friday and time is past 10pm
        if current_day_of_week == 4 and current_hour > 22:
            return False
        
        # If it's Saturday (5) or Sunday (6), the market is closed
        if current_day_of_week == 5:
            return False
        
        elif current_day_of_week == 0 and current_hour < 23:
            return False

        # Otherwise, the market is open
        else:
            return True

    def update_market_status(self):
        #Update the market status and disconnect from MT5 if the market is closed
        self.is_market_open = self.check_market_open()
        if not self.is_market_open and self.mt5_connector.is_connected:
            self.mt5_connector.disconnect()

class DataFetcher:
    def __init__(self, mt5_connector, symbol, timeframe, from_data, to_data):
        self.mt5_connector = mt5_connector
        self.symbol = symbol
        self.timeframe = timeframe
        self.from_data = from_data
        self.to_data = to_data
        

    def fetch(self):
        try:
            data = pd.DataFrame(mt5.copy_rates_from_pos(self.symbol, self.timeframe, self.from_data, self.to_data))
            return data

        except Exception as e:
            print("------------------------------------------------------------------")
            print(f"[{datetime.now()}] Failed to fetch data for {self.symbol} - {e}")


class MarketOrder:
    def __init__(self, symbol, lot, deviation, magic, trade_type, stop_loss=None, take_profit=None):
        self.symbol = symbol
        self.lot = lot
        self.deviation = deviation
        self.magic = magic
        self.trade_type = trade_type
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def execute(self):
        # Define the trade request dictionary
        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,  # immediate execution
            "symbol": self.symbol,
            "volume": self.lot,
            "type": self.trade_type,  # buy or sell
            "price": mt5.symbol_info_tick(self.symbol).ask if self.trade_type == 0 else mt5.symbol_info_tick(self.symbol).bid,
            "sl": self.stop_loss,
            "tp": self.take_profit,
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": "Buy" if self.trade_type == 0 else "Sell",
            "type_time": mt5.ORDER_TIME_GTC,  # good till cancelled
            "filling_type": mt5.ORDER_FILLING_IOC,
        }

        # Send the trade request
        try:
            result = mt5.order_send(trade_request)
            
            return result
        
        except Exception as e:
            print("-------------------------------------------------------")
            print(f"[{datetime.now()}] Failed to send market order for {self.symbol} - {e}")
            return None


class IndicatorCalculator:
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher

    def calculate_atr(self, period):
        # Fetch the data
        self.data_fetcher.fetch()
        data = self.data_fetcher.data
        # Calculate the true range
        data['high_low'] = data['high'] - data['low']
        data['high_close'] = np.abs(data['high'] - data['close'].shift())
        data['low_close'] = np.abs(data['low'] - data['close'].shift())
        data['tr'] = data[['high_low', 'high_close', 'low_close']].max(axis=1)

        # Calculate the ATR
        data['atr'] = data['tr'].rolling(period).mean()

        return data['atr'].iloc[-1]

    # Add other indicator calculation methods here


class OpenPositionManager:
    def __init__(self, connector, symbol, timeframe, from_data, to_data, atr_period, max_dist_atr_multiplier, atr_sl_multiplier, trail_atr_multiplier):
        self.connector = connector
        self.symbol = symbol
        self.timeframe = timeframe
        self.from_data = from_data
        self.to_data = to_data
        self.atr_period = atr_period
        self.max_dist_atr_multiplier = max_dist_atr_multiplier
        self.atr_sl_multiplier = atr_sl_multiplier
        self.trail_atr_multiplier = trail_atr_multiplier
        self.indicator_calculator = IndicatorCalculator(DataFetcher(connector, symbol, timeframe, from_data, to_data))

    def get_positions(self):
        positions = pd.DataFrame(mt5.positions_get(symbol=self.symbol))
        return positions
    

    def calculate_atr_trailing_stop(self, position):
        
        # get position data
        order_type = position[5]
        price_current = position[13]
        price_open = position[10]
        sl = position[11]
        ticket = position[7]

        dist_from_sl = abs(round(price_current - sl, 6))
        max_dist_sl = self.max_dist_atr_multiplier 
        trail_amount = self.trail_atr_multiplier 

        if dist_from_sl > max_dist_sl:
    
            # calculating new sl
            if sl != 0.0:
                if order_type == 0:  # 0 stands for BUY
                    new_sl = sl + trail_amount
                else:  # 1 stands for SELL
                    new_sl = sl - trail_amount
            
                
            request = {
                'action': mt5.TRADE_ACTION_SLTP,
                'position': ticket,
                'sl': new_sl,
            }

            result = mt5.order_send(request)
            return result
        else:
            return None
        
    def calculate_manual_stop(self, position):
        
        # get position data
        order_type = position[5]
        price_open = position[10]
        sl = position[11]
        ticket = position[7]

        stop = self.atr_sl_multiplier

   

        # calculating new sl
        if sl == 0.0:
            # setting default SL if there is no SL on the symbol
            if order_type == 0:  # Buy order
                new_sl = price_open - stop
            else:  # Sell order
                new_sl = price_open + stop
        
            
            request = {
                    'action': mt5.TRADE_ACTION_SLTP,
                    'position': ticket,
                    'sl': new_sl,
                }

            result = mt5.order_send(request)
            return result
        else:
            return None
        


class TradeHistory:
    def __init__(self, mt5_connector, symbol):
        self.mt5_connector = mt5_connector
        self.symbol = symbol

    def get_history(self, from_date, to_date):
        # Get the history orders within the specified interval
        history_orders = mt5.history_orders_get(from_date, to_date, group=self.symbol)
        
        if history_orders is None or len(history_orders) == 0:
            print(f"No history orders are found for {self.symbol} within the specified interval")
            return pd.DataFrame()  # return empty dataframe
        else:
            # Convert the obtained data to pandas dataframe
            df = pd.DataFrame(list(history_orders), 
                              columns=history_orders[0]._asdict().keys())
            df.sort_values(by=['time_done'], inplace=True, ascending=True)

            return df

        

class Messenger:
    def __init__(self, webhook_url, username='Tracy'):
        self.webhook_url = webhook_url
        self.username = username

    def send(self, content):
        data = {
            "content": content,
            "username": self.username
        }
        response = requests.post(
            self.webhook_url, data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code != 204:
            raise ValueError(
                'Request to discord returned an error %s, the response is:\n%s'
                % (response.status_code, response.text)
            )
        else:
            print(".......")

            
class InspireTraders:
    def __init__(self, messenger, kill_threads, json_file, schedules=None):
  
        self.messenger = messenger
        self.kill_threads = kill_threads
        self.json_file = json_file
        self.schedules = schedules

    def get_random_message(self, key):
        with open(self.json_file, 'r', encoding='utf-8') as file:  # add encoding parameter here
            data = json.load(file)
        return random.choice(data[key])

    def send_message(self, key):
        message = self.get_random_message(key)
        self.messenger.send(message)
        print(f"{message} (Inspiring message sent!)")

    def run(self):
        print("InspireTraders thread started...")
        for schedule_time, key in self.schedules:
            schedule.every().day.at(schedule_time).do(self.send_message, key)
        while not self.kill_threads[0]:
            schedule.run_pending()
            time.sleep(1)
        print("InspireTraders thread stopped.")
