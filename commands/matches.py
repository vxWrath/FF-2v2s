import discord

from discord import app_commands, ui
from discord.ext import commands
from typing import List

from resources import MatchMaker, Extras, Colors, Region, BaseView, Match

class MatchScroller(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], matches: List[Match]):
        super().__init__(300, interaction)
        
        self.matches = matches
        
        self.index   = 0
        self.groups  = [matches[i:i+5] for i in range(0, len(matches), 5)]
            
        if len(self.groups) <= 1:
            self.right.disabled = True
            self.superright.disabled = True

    def format_page(self) -> List[discord.Embed]:
        embeds = []
        if not self.groups:
            embed = discord.Embed(
                description = "You have no matches played",
                color = Colors.blank,
            )
            embeds.append(embed)
        else:
            for matchup in self.groups[self.index]:
                embed = discord.Embed(
                    description = (
                        f"# 2v2 Matchup\n"
                        f"`{matchup.team_one.score or 'NA':>2}` **- <@{matchup.team_one.player_one}> & <@{matchup.team_one.player_two}>** (🏆 {matchup.team_one.trophies})\n"
                        f"`{matchup.team_two.score or 'NA':>2}` **- <@{matchup.team_two.player_one}> & <@{matchup.team_two.player_two}>** (🏆 {matchup.team_two.trophies})\n\n"
                        f"`Region:` **{Region(matchup.region).name}**\n"
                        f"`Started:` {discord.utils.format_dt(matchup.created_at, "f")}\n"
                    ),
                    color = Colors.blank,
                    timestamp = discord.utils.utcnow(),
                )
                embed.set_footer(text=f"ID: {matchup.id}")
                embeds.append(embed)

        self.page_num.label = f"Page {self.index + 1}/{max(len(self.groups), 1)}"
        
        return embeds
    
    @ui.button(label="◀◀", disabled=True)
    async def superleft(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if self.index == 0:
            self.left.disabled = True
            self.superleft.disabled = True
            return await interaction.response.defer()
        
        self.index = 0
        
        self.left.disabled = True
        self.superleft.disabled = True
        
        self.right.disabled = False
        self.superright.disabled = False
        
        await interaction.response.edit_message(embeds=self.format_page(), view=self)
        
    @ui.button(label="◀", disabled=True)
    async def left(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if self.index == 0:
            self.left.disabled = True
            self.superleft.disabled = True
            return await interaction.response.defer()
        
        self.index -= 1
        
        if self.index == 0:
            self.left.disabled = True
            self.superleft.disabled = True
        
        self.right.disabled = False
        self.superright.disabled = False
        
        await interaction.response.edit_message(embeds=self.format_page(), view=self)
        
    @ui.button(style=discord.ButtonStyle.blurple, disabled=True,)
    async def page_num(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        pass
        
    @ui.button(label="▶")
    async def right(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if self.index == len(self.groups) - 1:
            self.right.disabled = True
            self.superright.disabled = True
            return await interaction.response.defer()
        
        self.index += 1
        
        self.left.disabled = False
        self.superleft.disabled = False
        
        if self.index == len(self.groups) - 1:
            self.right.disabled = True
            self.superright.disabled = True
        
        await interaction.response.edit_message(embeds=self.format_page(), view=self)
        
    @ui.button(label="▶▶")
    async def superright(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if self.index == len(self.groups) - 1:
            self.right.disabled = True
            self.superright.disabled = True
            return await interaction.response.defer()
        
        self.index = len(self.groups) - 1
        
        self.left.disabled = False
        self.superleft.disabled = False
        
        self.right.disabled = True
        self.superright.disabled = True
        
        await interaction.response.edit_message(embeds=self.format_page(), view=self)

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

        matches = await interaction.client.database.get_user_matches(interaction.user.id)
        view    = MatchScroller(interaction, matches)
        embeds  = view.format_page()

        await interaction.followup.send(embeds=embeds, view=view)
        
async def setup(bot: MatchMaker):
    cog = ViewMatches(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)