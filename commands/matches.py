import discord

from discord import app_commands
from discord.ext import commands

from resources import MatchMaker, Object, Extras, Colors, Region

class ViewMatches(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="matches", 
        description="view your recent matches",
        extras=Extras(defer_ephemerally=True, user_data=True),
    )
    async def matches(self, interaction: discord.Interaction[MatchMaker]):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(content=f"⚠️ **You are not verified. Run /account to verify**")
        
        # TODO
        # make this a pager
        # << | < | 0/0 | > | >>
        # maybe limit it to 5 instead of 10
        
        matches = list(discord.utils.as_chunks(await interaction.client.database.get_users_matches(interaction.user.id), 10))
        
        embeds = []
        for matchup in matches[0]:
            embed = discord.Embed(
                description = (
                    f"# 2v2 Matchup\n"
                    f"`{matchup.team_one.score or 'NA':>2}` **- <@{matchup.team_one.player_one}> & <@{matchup.team_one.player_two}>** (🏆 {matchup.team_one.trophies})\n"
                    f"`{matchup.team_two.score or 'NA':>2}` **- <@{matchup.team_two.player_one}> & <@{matchup.team_two.player_two}>** (🏆 {matchup.team_one.trophies})\n\n"
                    f"`Region:` **{Region(matchup.region).name}**\n"
                    f"`Created:` {discord.utils.format_dt(matchup.created_at, "f")}\n"
                ),
                color = Colors.blank,
                timestamp = discord.utils.utcnow(),
            )
            embed.set_footer(text=f"ID: {matchup.id}")
            
            embeds.append(embed)

        await interaction.followup.send(embeds=embeds)
        
async def setup(bot: MatchMaker):
    cog = ViewMatches(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)