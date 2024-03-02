import MetaTrader5 as mt5

# MetaTrader 5 credentials
credentails = {
    'account':30539852,
    'password':'Omegatega360@',
    'server':'Deriv-Demo',
    'webhook_url':'https://discordapp.com/api/webhooks/1124572037097197628/98bgmVJM-MIeZK5dsBiQ6agdtGK8V6Ydhc_TcMxQh5yxg6eq3dAAC16QrAyQSFMvcA_8'

}
account = 30539852
password = 'Omegatega360@'
server = 'Deriv-Demo'
webhook_url = 'https://discordapp.com/api/webhooks/1124572037097197628/98bgmVJM-MIeZK5dsBiQ6agdtGK8V6Ydhc_TcMxQh5yxg6eq3dAAC16QrAyQSFMvcA_8'


# User-defined variables
symbols = 'EURJPY'
timeframe = mt5.TIMEFRAME_H1
lot = 0.01
from_data = 1
to_data = 100
deviation = 10
magic1 = 360
magic2 = 361
magic3 = 362
tp_pips = 50
atr_sl_multiplier = 0.1
atr_period = 14
max_dist_atr_multiplier = 0.2
trail_atr_multiplier = 0.1



"""# MetaTrader 5 credentials
account = 9024010
password = 'Crystmond123@'
server = 'Deriv-Server'
webhook_url = 'https://discordapp.com/api/webhooks/1080463096176443422/ikJK_aoZ__Dp9F6MBz5mXfAlLjJJdWJbUB-yA0X8PiyQTjjyIMjGAPZRCslpf6zF2CzL'


# User-defined variables
symbols = ['EURJPY', 'GBPJPY', 'AUDJPY', 'USDJPY']
timeframe = mt5.TIMEFRAME_M15
lot = 0.01
from_data = 1
to_data = 16
deviation = 10
magic1 = 360
magic2 = 361
magic3 = 362
tp_pips = 50
atr_sl_multiplier = 0.1
atr_period = 14
max_dist_atr_multiplier = 0.2
trail_atr_multiplier = 0.1
"""