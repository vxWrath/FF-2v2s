import colorlog
import datetime
import discord
import io
import sys
import traceback

from typing import Optional, Union
from discord import app_commands
from discord.ext import commands
from os import environ as env

from resources import MatchMaker, MatchMakerException, CheckFailure, CheckFailureType, Unverified, MemberBanned

logger = colorlog.getLogger("bot")

ERRORS_WH = env["ERRORS_WH"]

class Errors(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot = bot
        self.bot.tree.on_error = self.app_command_error

        self.webhook = discord.Webhook.from_url(ERRORS_WH, client=self.bot)

    async def app_command_error(self, interaction: discord.Interaction[MatchMaker], error: Union[app_commands.AppCommandError, MatchMakerException]):
        kwargs = None
        
        if isinstance(error, app_commands.CommandInvokeError):
            error  = error.__cause__

        if isinstance(error, Unverified):
            kwargs = {
                "content": "⚠️ **You are not verified. Run /account to verify**",
                "ephemeral": True,
            }
        elif isinstance(error, MemberBanned):
            if error.data.banned_until:
                kwargs = {
                    "content": f"❌ **You are temporarily banned from playing 2v2s until {discord.utils.format_dt(error.data.banned_until, "f")}**",
                    "ephemeral": True,
                }
            else:
                kwargs = {
                    "content": f"❌ **You are permanently banned from playing 2v2s**",
                    "ephemeral": True,
                }
        elif isinstance(error, CheckFailure):
            if error.type == CheckFailureType.staff:
                kwargs = {
                    "content": f"❌ **This command is for staff only**",
                    "ephemeral": True,
                }
            elif error.type == CheckFailureType.admin:
                kwargs = {
                    "content": f"❌ **This command is for admins only**",
                    "ephemeral": True,
                }
        elif isinstance(error, app_commands.TransformerError):
            if error.type == discord.AppCommandOptionType.user:
                kwargs = {
                    "content": f"❌ **Failed to retrieve the member '{error.value}'**",
                    "ephemeral": True,
                }

        elif isinstance(error, discord.NotFound):
            if error.code == 10062:
                if discord.utils.utcnow() < interaction.created_at + datetime.timedelta(seconds=10):
                    try:
                        await interaction.channel.send(
                            content = f"❌ **{interaction.user.mention}, it took too long for the bot to process a request. Try again in 1-2 minutes**",
                        )
                    except Exception:
                        pass
                    
                tb = error.__traceback__.tb_next
                    
                filename = '/'.join(tb.tb_frame.f_code.co_filename.split("\\" if sys.platform == 'win32' else '/')[-3:])
                lineno   = tb.tb_lineno
                func     = tb.tb_frame.f_code.co_name
                
                if self.bot.production and interaction.guild:
                    return await self.webhook.send(content=f"**Unknown Interaction in file \"{filename}\", on line {lineno}, under {func} | Guild: {interaction.guild.name} ({interaction.guild.id})**")
                elif interaction.guild:
                    return logger.error(
                        msg=f"Unknown Interaction in file \"{filename}\", on line {lineno}, under {func} | Guild: {interaction.guild.name} ({interaction.guild.id})"
                    )
            elif error.code == 10008:
                return
            
        if not kwargs and self.bot.production:
            await self.fail(error=error, interaction=interaction)
            
            kwargs = {
                "content": f"❌ **An unknown error occured and the devs have been contacted. Try again later.**",
                "ephemeral": True,
            }
            
        try:
            if kwargs:
                if interaction.response.is_done():
                    return await interaction.followup.send(**kwargs)
                return await interaction.response.send_message(**kwargs)
        except discord.HTTPException as e:
            if e.code == 50027:
                return
            
            if self.bot.production:
                kwargs.pop('ephemeral', None)
                return await interaction.channel.send(**kwargs)

        raise error

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