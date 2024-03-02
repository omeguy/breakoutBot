import MetaTrader5 as mt5
from meta_bot import DataFetcher, MarketOrder, OpenPositionManager, Messenger
from db_manager import DatabaseManager
from datetime import datetime
import time


class Bot:
    def __init__(self, mt5_connector, market_status, symbol, timeframe, from_data, to_data, lot, deviation, magic1, magic2, magic3, tp_pips, atr_sl_multiplier, atr_period, max_dist_atr_multiplier, trail_atr_multiplier, webhook_url):
        self.mt5_connector = mt5_connector
        self.market_status = market_status
        self.symbol = symbol
        self.timeframe = timeframe
        self.from_data = from_data
        self.to_data = to_data
        self.lot = lot
        self.deviation = deviation
        self.magic1 = magic1
        self.magic2 = magic2
        self.magic3 = magic3
        self.tp_pips = tp_pips
        self.atr_sl_multiplier = atr_sl_multiplier
        self.atr_period = atr_period
        self.max_dist_atr_multiplier = max_dist_atr_multiplier
        self.trail_atr_multiplier = trail_atr_multiplier
        self.webhook_url = webhook_url
        self.should_stop = False


        self.username = 'Tracy'
        self.box = None


        #initialize data fetcher
        self.data_fetcher = DataFetcher(mt5_connector, symbol, timeframe, from_data, to_data)

        #initialize position manager
        self.position_manager = OpenPositionManager(mt5_connector, self.symbol, self.timeframe, self.from_data, self.to_data, self.atr_period, self.max_dist_atr_multiplier, self.atr_sl_multiplier, self.trail_atr_multiplier)

        #initialize Messanger
        self.messanger = Messenger(self.webhook_url, self.username)

        #initialize flags
        self.data_fetched = False
        self.box_calculated = False
        self.levels_calculated = False
        self.trade_executed = False
        self.trading_notification = False
        self.trade_signal_notification = False
        self.position_manager_nofitication = False

        self.daily_data_reset = False

        self.db_manager = DatabaseManager('trades.db')

       
        # Define the schema for your opened_trades table, now with symbol added
        trade_schema = """
            date_time TEXT,
            ticket_id INTEGER,
            symbol TEXT,
            trade_type TEXT,
            open_price REAL,
            magic_number INTEGER
        """
        
        # Create the table in the database
        self.db_manager.create_table('opened_trades', trade_schema)

        # Define the schema for your closed_trades table
        closed_trade_schema = """
            date_time_open TEXT,
            ticket_id INTEGER,
            trade_type TEXT,
            open_price REAL,
            magic_number INTEGER,
            date_time_close TEXT,
            close_price REAL,
            profit REAL
        """

        # Create the table in the database
        self.db_manager.create_table('closed_trades', closed_trade_schema)


    def calculate_box(self):
        # Get the historical data
        data = self.data_fetcher.data

        # Check if data is None
        if data is None:
            print("-------------------------------------")
            print(f"No data fetched: {self.symbol}")
            return

        # Calculate the high and low of the box
        high = max(data['high'])
        low = min(data['low'])
        box_height = high - low

        # Store the levels in a dictionary
        self.box = {
            'buy_level': high,
            'sell_level': low,
            'buy_stoploss': low,
            'sell_stoploss': high,
            'box_height': box_height
        }
        print("-------------------------------------")
        print(f"Box_levels: {self.symbol}: {self.box}")

    def calculate_levels(self):  
        # Fetch data
        if not self.data_fetched:
            self.data_fetcher.fetch()
            self.data_fetched = True
            print("----------------------------------------------")
            print(f"Data fetched successfully: {self.symbol}.")
        if self.data_fetched and not self.box_calculated:
            print("----------------------------------------------")
            print(f"calculating box levels: {self.symbol}.")
            # Calculate the box            
            self.calculate_box()
            self.box_calculated = True
    
    def check_for_break(self):

        # Get the last candle
        self.data_fetcher.fetch()
        last_candle = self.data_fetcher.data.close.iloc[-1]

        # Check if the price has broken out of the box
        if last_candle > self.box['buy_level']:
            print("----------------------------------------------")
            print(f"Breakout detected: {self.symbol} - price has gone above the buy level.")
            return 0
        elif last_candle < self.box['sell_level']:
            print("----------------------------------------------")
            print(f"Breakout detected: {self.symbol} - price has gone below the sell level.")
            return 1
        # Return None if no breakout has occurred
        else:
            return None



    def manage_positions(self, open_positions):
        
        # Loop over all open positions
        for index, position in open_positions.iterrows():

            if not position[6]:
                update_stop = self.position_manager.calculate_manual_stop(position)
                if update_stop:
                    print("-------------------------------------------------")
                    print(f'{self.symbol}: stop_loss set : {update_stop.comment}')

                #trail position
                if position[11] != 0.0:
                    update_result = self.position_manager.calculate_atr_trailing_stop(position)
                  
                    if update_result:
                        print("-------------------------------------------------")
                        print(f'{self.symbol}: manual Position Trailled : {update_result.comment}')

            if position[6] == self.magic2:
                #trail position with magic number
                update_result = self.position_manager.calculate_atr_trailing_stop(position)
                if update_result:
                    print("-------------------------------------------------")
                    print(f'{self.symbol}: Position Trailled : {update_result.comment}')


    def calculate_win_loss_ratio(self):
        # Fetch all closed trades
        closed_trades = self.db_manager.select_all('closed_trades')
        # Count wins and losses
        wins = sum(1 for trade in closed_trades if trade[7] > 0)
        losses = sum(1 for trade in closed_trades if trade[7] < 0)
        # Calculate win/loss ratio
        win_loss_ratio = wins / losses if losses > 0 else 'N/A'
        return win_loss_ratio

    def calculate_average_profit_loss(self):
        # Fetch all closed trades
        closed_trades = self.db_manager.select_all('closed_trades')
        # Calculate average profit and loss
        avg_profit = sum(trade[7] for trade in closed_trades if trade[7] > 0) / len(closed_trades)
        avg_loss = sum(trade[7] for trade in closed_trades if trade[7] < 0) / len(closed_trades)
        return avg_profit, avg_loss


    def reset_data(self):
           
        # Reset the trading data
        self.box = None

        # Reset flags
        self.data_fetched = False
        self.box_calculated = False
        self.levels_calculated = False
        self.trade_executed = False
        self.trading_notification = False
        self.trade_signal_notification = False
        self.position_manager_notification = False

        self.daily_data_reset = True
        # Send a reset message
        self.messanger.send(f'{self.symbol}:Today data reset:{self.daily_data_reset}')
        print('------------------------------------------------------------')
        print(f'{self.symbol}:Today data reset:{self.daily_data_reset}')
           
    def stop(self):
            self.should_stop = True
            print('...')
            

    def run(self):
        while not self.should_stop:
            #-----------------------------------------------
            start_time = time.time()  # Save the start time
            #-----------------------------------------------

            open_positions = self.position_manager.get_positions()
            num_pos_symb = len(open_positions)


            # Check if it's the right time to calculate levels (2:00 GMT)
            current_time = datetime.utcnow().time()
            if current_time == 1 and not self.daily_data_reset:
                self.reset_data()

            if current_time.hour == 2 and not self.levels_calculated:
                print("------------------------------------------------------------------")
                print(f'Time(GMT): {current_time}')
                print("----------------------------")        
                self.calculate_levels()
                self.levels_calculated = True
                print("----------------------------")
                print(f'Levels Calculated: {self.symbol}: {self.levels_calculated}')
                self.daily_data_reset = False


            if num_pos_symb > 0:
                if not self.position_manager_nofitication:
                    print("----------------------------")
                    print('Managing Opened Positions')
                    self.position_manager_nofitication = True
                #Manage open position
                self.manage_positions(open_positions)
 

             # Only check for breakout if levels have been calculated and a trade hasn't been executed yet
            if self.levels_calculated and not self.trade_executed:
                if not self.trading_notification:
                    print("----------------------------")
                    print('Waiting to execute trade')
                    self.trading_notification = True

                trade_signal = self.check_for_break()
                
                if trade_signal is not None:
                    print("------------------------------------------------------------------")
                    print(f'Time(GMT): {current_time}')
                    print("----------------------------")
                    if not self.trade_signal_notification:
                        print("----------------------------------------------")
                        print(f'Buy_level broken' if trade_signal == 0 else 'Sell_level broken')
                        self.messanger.send(f'Buy_level broken' if trade_signal == 0 else 'Sell_level broken')
                        print("-------------------------------------")
                        print("Executing Trade")  
                        self.trade_signal_notification = True

                     # Calculate the take profit based on the box height and trade signal
                    current_price = mt5.symbol_info_tick(self.symbol).ask
                    box_take_profit = current_price + self.box['box_height'] if trade_signal == 0 else current_price - self.box['box_height']
                     # Points for 50 pips

                    # Execute the trades
                    trade1 = MarketOrder(self.symbol, self.lot, self.deviation, self.magic1, trade_signal, self.box['buy_stoploss'] if trade_signal == 0 else self.box['sell_stoploss'], box_take_profit)
                    trade1_result = trade1.execute()
                    trade2 = MarketOrder(self.symbol, self.lot, self.deviation, self.magic2, trade_signal, self.box['buy_stoploss'] if trade_signal == 0 else self.box['sell_stoploss'], 0.0)
                    trade2_result = trade2.execute()
                    

                    if trade1_result.retcode == mt5.TRADE_RETCODE_DONE:
                        print("-------------------------------------")
                        print(f'{self.symbol}: {trade1_result.comment}')
                        print("-------------------------------------")
                        self.messanger.send(f'{self.symbol}: {trade1_result.comment}')
                        # Prepare the columns and values
                        columns = ['date_time', 'ticket_id', 'symbol', 'trade_type', 'open_price', 'magic_number']
                        values = [datetime.now(), trade1_result.order, self.symbol, 'Buy' if trade_signal == 0 else 'Sell', trade1_result.price, self.magic1]
                        # Insert the data into the database
                        self.db_manager.insert_item('opened_trades', columns, values)



                    if trade2_result.retcode == mt5.TRADE_RETCODE_DONE:
                        print("-------------------------------------")
                        print(f'{self.symbol}: {trade2_result.comment}')
                        print("-------------------------------------")
                        self.messanger.send(f'{self.symbol}: {trade2_result.comment}')
                        # Prepare the columns and values
                        columns = ['date_time', 'ticket_id', 'symbol', 'trade_type', 'open_price', 'magic_number']
                        values = [datetime.now(), trade2_result.order, self.symbol, 'Buy' if trade_signal == 0 else 'Sell', trade2_result.price, self.magic2]
                        # Insert the data into the database

                        self.db_manager.insert_item('opened_trades', columns, values)

                        self.trade_executed = True
                        print("-------------------------------------")
                        print(f'Trade executed: {self.symbol}: {self.trade_executed}')




                    else:
                        print("-------------------------------------")
                        print("Failed to execute trades")
                        self.messanger.send(f"{self.symbol}: Failed to execute trades")
                        # Handle error here or try to execute trade again
                                        
                
            if current_time.hour == 22 and not self.daily_data_reset:
                self.reset_data()

            
            
            elapsed_time = time.time() - start_time  # Calculate elapsed time
            if elapsed_time < 55:  # Check if elapsed_time is less than 55 seconds
                sleep_time = 60 - elapsed_time  # Sleep for the remaining time
            else:  # If execution took longer than 55 seconds
                sleep_time = 5  # Sleep for at least 5 seconds

            time.sleep(sleep_time)  # Sleep for the determined time