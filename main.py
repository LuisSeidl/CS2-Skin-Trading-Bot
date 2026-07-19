import schedule
import time 
from datetime import timedelta
from bot import Bot


if __name__ == "__main__":
    bot = Bot()

    #schedule.every(5).minutes.do(bot.mainApplication)
    #schedule.every(1).day.do(bot.cleanUp)

    #while True:
    #    schedule.run_pending()
    #    time.sleep(1)

    bot.cleanUp(timedelta(7))
    bot.mainApplication()