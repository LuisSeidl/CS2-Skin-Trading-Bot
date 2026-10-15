import schedule
import time 
from datetime import timedelta
from bot import Bot


if __name__ == "__main__":
    limit = 100
    max_pages = 10

    bot = Bot(max_pages=max_pages, limit=limit)

    schedule.every(5).minutes.do(bot.mainApplication)
    schedule.every(1).day.do(bot.cleanUp)

    #while True:
    #    schedule.run_pending()
    #    time.sleep(1)

    bot.mainApplication()
    bot.cleanUp(timedelta(1))