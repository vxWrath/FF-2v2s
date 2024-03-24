import discord
import random

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Object, Extras

class FillQueue(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="fillqueue", 
        description="test command: add a team to the queue",
        extras=Extras(defer_ephemerally=True, user_data=True),
    )
    async def fillqueue(self, interaction: discord.Interaction[MatchMaker]):
        player_one, player_two = tuple(random.choices([x for x in interaction.guild.members if x.id not in [450136921327271946, 1104883688279384156]], k=2))
        
        print(player_one.name, player_two.name)
        
        team    = Object(player_one=player_one.id, player_two=player_two.id, region=1, trophies=0)
        matchup = await interaction.client.queuer.join_queue(team, interaction.client.loop)
        
        await interaction.followup.send(content="matchup found")
        
async def setup(bot: MatchMaker):
    cog = FillQueue(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)