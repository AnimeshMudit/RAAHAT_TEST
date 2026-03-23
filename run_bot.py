import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.bot.telegram_bot import run

if __name__ == '__main__':
    logging.info("🚀 Starting RAAHAT Bot...")
    run()
