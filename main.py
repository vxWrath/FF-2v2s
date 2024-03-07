import asyncio
import datetime
from os import environ as env

import colorlog
import pytz
from dotenv import load_dotenv

load_dotenv()

from resources import MatchMaker, Database

class Formatter(colorlog.ColoredFormatter):
    def converter(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('US/Central')).timetuple()
    
async def main():
    token  = env['TOKEN']
    bot    = MatchMaker()
    colors = colorlog.default_log_colors | {"DEBUG": "white"}
    
    bot_handler   = colorlog.StreamHandler()
    bot_formatter = Formatter('%(log_color)s[%(asctime)s][BOT][%(levelname)s] %(message)s', datefmt='%m/%d/%Y %r', log_colors=colors | {"INFO": "bold_purple"})
    bot_logger    = colorlog.getLogger("bot")
    
    bot_handler.setFormatter(bot_formatter)
    bot_logger.addHandler(bot_handler)
    bot_logger.setLevel(colorlog.DEBUG)
    
    try:
        async with bot:
            await bot.start(token)
    except asyncio.CancelledError:
        pass
    finally:
        bot_logger.info("Turning Off...")
        
        await bot.close()
        await bot.database.redis.aclose()
        await bot.external_session.close()
            
        bot_logger.info("Turned Off!")
        
if __name__ == '__main__':
    asyncio.run(main())