from bot import Bot   
from meta_bot import MT5Connector, DataFetcher
from config import credentails, symbols, timeframe, from_data, to_data

# Create an instance of MT5Connector and MarketStatus
connector = MT5Connector(account=credentails['account'], password=credentails['password'], server=credentails['server'])
datafetcher = DataFetcher(connector, symbols, timeframe, from_data, to_data)


connector.connect()

bot = Bot(connector, datafetcher, symbols, timeframe, from_data, to_data)
bot.run()