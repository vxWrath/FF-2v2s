import colorlog
import discord
import io
import traceback

from typing import Optional
from discord.ext import commands, tasks
from resources import MatchMaker
from os import environ as env

logger = colorlog.getLogger("bot")

ERRORS_WH = env["ERRORS_WH"]

class Errors(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot = bot
        self.bot.tree.on_error = self.app_command_error

        self.webhook = discord.Webhook.from_url(ERRORS_WH, client=self.bot)

    @commands.Cog.listener(name="on_fail")
    async def fail(self, error: Exception, interaction: Optional[discord.Interaction[MatchMaker]]=None):
        if tb is None:
            return
        
        try:
            tb      = ''.join(traceback.format_exception(error.__class__, error, error.__traceback__))
            content = f"<t:{int(discord.utils.utcnow().timestamp())}:f>"
            
            if interaction:
                if interaction.guild:
                    content += f"\n\n` Server:` {interaction.guild.name} ({interaction.guild.id})"
                
                if interaction.channel:
                    content += f"\n`Channel:` #{getattr(interaction.channel, 'name', 'no-channel')}"
                    
                if interaction.user:
                    content += f"\n`   User:` {interaction.user.name} ({interaction.user.id})"
            
            if len(tb) + len(content) > 1900:
                f = discord.File(io.StringIO(tb), filename="error.py")
                await self.webhook.send(content=content, file=f)
            else:
                await self.webhook.send(content=content + f"\n\n```python\n{tb}```")
        except Exception as e:
            logger.error(msg = "Failed to send error to webhook!", exc_info = error)
            logger.error(msg = "Error that was supposed to send", exc_info = e)

async def setup(bot: MatchMaker):
    await bot.add_cog(Errors(bot))