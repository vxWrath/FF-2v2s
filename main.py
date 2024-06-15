import asyncio
import datetime
from os import environ as env

import colorlog
import pytz
from dotenv import load_dotenv

load_dotenv()

from resources import MatchMaker

class Formatter(colorlog.ColoredFormatter):
    def converter(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp=timestamp, tz=pytz.timezone('US/Central')).timetuple()
    
class DiscordHandler(colorlog.StreamHandler):
    def __init__(self, bot: MatchMaker):
        super().__init__()
        
        self.bot = bot
        
    def handle(self, record) -> bool:
        if self.bot.production and record.levelno in [colorlog.WARN, colorlog.ERROR, colorlog.FATAL]:
            _, error, _ = record.exc_info or (None, None, None)
            self.bot.dispatch("fail", error=error)
        else:
            return super().handle(record)
    
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

    discord_handler   = DiscordHandler(bot)
    discord_formatter = Formatter(' %(log_color)s[%(asctime)s][DISCORD][%(levelname)s] %(message)s', datefmt='%m/%d/%Y %r', log_colors=colors | {"INFO": "black"})
    discord_logger    = colorlog.getLogger("discord")

    discord_handler.setFormatter(discord_formatter)
    discord_logger.addHandler(discord_handler)
    discord_logger.setLevel(colorlog.INFO)

    try:
        async with bot:
            await asyncio.wait_for(bot.database.redis.ping(), timeout=10)
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

    