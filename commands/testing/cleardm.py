import asyncio
import discord

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Extras

class ClearDM(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="cleardm", 
        description="test command: clears DMs with the bot",
        extras=Extras(defer_ephemerally=True), # 
    )
    async def fillqueue(self, interaction: discord.Interaction[MatchMaker]):
        channel = interaction.user.dm_channel or await interaction.user.create_dm()

        async for message in channel.history(limit=100):
            if not message.author == interaction.client.user:
                continue

            await message.delete()
            await asyncio.sleep(0.25)
        
        await interaction.followup.send(content="done")
        
async def setup(bot: MatchMaker):
    cog = ClearDM(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)