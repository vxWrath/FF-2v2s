import asyncio
import datetime
import discord

from discord import app_commands, ui
from discord.ext import commands

from resources import MatchMaker, Object, Extras, THREAD_CHANNEL, BaseView, Match

class CancelGame(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], matchup: Match):
        super().__init__(3600, interaction)
        
        self.matchup   = matchup
        self.cancelers = [interaction.user.id]
        
    @ui.button(label="Cancel Game (33%)", style=discord.ButtonStyle.red)
    async def cancel_game(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if interaction.user.id in self.cancelers:
            self.cancelers.remove(interaction.user.id)
        else:
            self.cancelers.append(interaction.user.id)
            
        if len(self.cancelers) == 0:
            await interaction.response.defer()
            return await interaction.delete_original_response()
        
        elif len(self.cancelers) >= 3:
            await interaction.response.edit_message(
                content = f"**Deleting {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=10), "R")}**",
                view = None
            )
            
            interaction.client.states.pop(self.matchup.team_one.player_one, None)
            interaction.client.states.pop(self.matchup.team_one.player_two, None)
            interaction.client.states.pop(self.matchup.team_two.player_one, None)
            interaction.client.states.pop(self.matchup.team_two.player_two, None)
            
            await asyncio.sleep(10)
            await interaction.channel.delete()
            
            return await interaction.client.database.delete_match(self.matchup)
        
        self.cancel_game.label = f"Cancel Game ({(len(self.cancelers) / 3) * 100:.0f}%)"
        await interaction.response.edit_message(content=f"**Voters:** {', '.join([f"<@{x}>" for x in self.cancelers])}", view=self)
        
    async def check_func(self, interaction: discord.Interaction[MatchMaker]):
        return interaction.user.id in [
            self.matchup.team_one.player_one, 
            self.matchup.team_one.player_two, 
            self.matchup.team_two.player_one, 
            self.matchup.team_two.player_two,
        ]

class Cancel(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="cancel", 
        description="cancel match making",
        extras=Extras(defer=True, user_data=True),
    )
    async def cancel(self, interaction: discord.Interaction[MatchMaker]):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(content=f"⚠️ **You are not verified. Run /account to verify**")
        
        if interaction.channel.type == discord.ChannelType.private_thread and interaction.channel.parent.id == THREAD_CHANNEL:
            matchup = await interaction.client.database.get_match_by_thread(interaction.channel.id)
            
            if not matchup:
                return await interaction.followup.send(content=f"❌ **I couldn't find the matchup within this thread**")
            
            if matchup.team_one.score is not None or matchup.team_two.score is not None:
                return await interaction.followup.send(content=f"❌ **You can't cancel a game that's already finished**")
            
            return await interaction.followup.send(content=f"**Voters:** {interaction.user.mention}", view=CancelGame(interaction, matchup))
        
        item = [
            x for x in interaction.client.queuer.queue 
            if x.team.player_one == interaction.user.id
            or x.team.player_two == interaction.user.id
        ]
        
        if not item:
            return await interaction.followup.send(content=f"❌ **You are not in the match making queue**", ephemeral=True)
        
        item = item[0]
        item.future.set_result(Object(canceled_by=interaction.user))
        interaction.client.queuer.queue.remove(item)
        
        await interaction.followup.send(content=f"❌ **Matchmaking canceled**", ephemeral=True)
        
async def setup(bot: MatchMaker):
    cog = Cancel(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)