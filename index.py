from src.binance_delisting_tracker import BinanceDelistingTracker
from src.init import init_general_config

if __name__ == '__main__':
    init_general_config()
    BinanceDelistingTracker().run()
