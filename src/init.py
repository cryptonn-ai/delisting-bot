from dotenv import load_dotenv
import os
import certifi
import time
import logging


def init_general_config() -> None:
    load_dotenv()

    # it uses os.environ['TZ']
    time.tzset()

    os.environ['SSL_CERT_FILE'] = certifi.where()

    # 0 = all messages, 1 = filter INFO, 2 = filter WARNING, 3 = filter all
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
