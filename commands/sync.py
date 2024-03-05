from typing import Literal, Optional

import colorlog
import discord
from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Object

logger = colorlog.getLogger('bot')

async def owner_only(interaction: discord.Interaction[MatchMaker]):
    return interaction.user.id in [interaction.client.owner_id]

@app_commands.guild_only()
class Sync(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot = bot
        
    @app_commands.command(
        name='extensions', 
        description='(un)load the cogs & (un)sync the commands', 
        extras=Object(defer_ephemerally=True, get_user_data=False)
    )
    @app_commands.describe(command="the command to execute", globally="whether to globally (un)sync the commands", guild="the guild to (un)sync")
    #@app_commands.check(owner_only)
    async def sync(self, interaction: discord.Interaction[MatchMaker], 
                   command : Literal['load', 'sync', 'load & sync', 'unload', 'unsync'], 
                   globally: Optional[Literal["yes", "no"]]="no",
                   guild: Optional[str]=None
                ):
        if guild and guild != "*":
            try:
                int(guild)
            except ValueError:
                return await interaction.followup.send(content="Not a valid guild ID", ephemeral=True)
                
            guild = interaction.client.get_guild(int(guild))
            
            if not guild:
                return await interaction.followup.send(content="Couldn't find guild", ephemeral=True)
        
        globally = True if globally == "yes" else False
        log = "Extensions "
        
        try:
            guild = guild or interaction.guild
            
            for command in command.split(' & '):
                log += f"{command.title()}ed & "
                
                if command == "load":
                    await self.bot.load_extensions()
                
                elif command == "sync":
                    if globally:
                        app_commands = await self.bot.tree.sync()
                    else:
                        if not guild == "*":
                            self.bot.tree.copy_global_to(guild=guild)
                        app_commands = await self.bot.tree.sync(guild=guild)
                        
                    for command in app_commands:
                        if any([x.type == discord.AppCommandOptionType.subcommand for x in command.options]):
                            for subcommand in command.options:
                                self.bot.command_mentions[subcommand.qualified_name] = subcommand.mention
                        else:
                            self.bot.command_mentions[command.name] = command.mention
                        
                elif command == "unload":
                    await self.bot.unload_extensions()
                    await self.bot.load_extension("commands.sync")
                    
                elif command == "unsync":
                    await self.bot.unload_extensions()
                    
                    if globally:
                        app_commands = await self.bot.tree.sync()
                    else:
                        app_commands = await self.bot.tree.sync(guild=guild)
                        
                    await self.bot.load_extensions()
        except Exception as e:
            await interaction.followup.send(content="❌")
            raise e
        
        logger.info(log[:-3])
        await interaction.followup.send(content="✅")
        
async def setup(bot: MatchMaker):
    cog = Sync(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", True)
    
    await bot.add_cog(cog)