import discord

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Object, Extras, THREAD_CHANNEL

class FillQueue(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="fillqueue", 
        description="test command: add a team to the queue",
        extras=Extras(defer_ephemerally=True, user_data=True), # type: ignore
    )
    async def fillqueue(self, interaction: discord.Interaction[MatchMaker]):
        if not interaction.guild:
            return
        
        player_one = interaction.guild.get_member(486232733698359296)
        player_two = interaction.guild.get_member(925841573172891658)

        if not player_one or not player_two:
            return
        
        team    = Object(
            player_one=player_one.id, 
            player_two=player_two.id, 
            region=1, 
            trophies=0, 
            private_server=f"https://www.roblox.com/games/8204899140/Football-Fusion-2?privateServerLinkCode=73943576065693662579174688833743",
            score=None
        )
        
        parent  = interaction.client.get_channel(THREAD_CHANNEL)

        if not parent or not isinstance(parent, discord.TextChannel):
            return

        matchup = await interaction.client.queuer.join_queue(team, interaction.client.loop, parent)
        
        await interaction.followup.send(content="matchup found")
        
async def setup(bot: MatchMaker):
    cog = FillQueue(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)