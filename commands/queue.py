import asyncio
import discord
import datetime
import re
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import random
import uuid

from resources import MatchMaker, Object, User, RobloxUser, BaseView, BaseModal, Colors, Region

FOOTBALL_FUSION_LINK = re.compile(
    r"(?:https:\/\/www\.roblox\.com\/games\/8204899140\/football-fusion-2\?privateserverlinkcode=)([0-9]{25,})", 
    flags=re.IGNORECASE
)

class PrivateServerOrSkip(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], data: Optional[User]=None, rblx: Optional[RobloxUser]=None):
        super().__init__(120, interaction, extras=Object(custom_id_data={"skip": {"defer": True}}))

        self.data  = data
        self.rblx  = rblx
        self.value = None

    @ui.button(label="Provide URL", style=discord.ButtonStyle.blurple)
    async def private_server(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        modal = GetPrivateServerLink(interaction)
        await interaction.response.send_modal(modal)

        if await modal.wait():
            self.stop()
            return await self.on_timeout()
        
        interaction = modal.interaction

        if self.data and self.rblx:
            await interaction.edit_original_response(
                content = "**Select your 2v2 teammate below (They must be in this server)**", 
                view = TeammateSelection(interaction, self.data, self.rblx, modal.value)
            )
        else:
            self.interaction = modal.interaction
            self.value       = modal.value

        self.stop()

    @ui.button(label="Skip", style=discord.ButtonStyle.gray, custom_id=f"skip:{uuid.uuid4()}")
    async def skip(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if self.data and self.rblx:
            await interaction.edit_original_response(
                content = "**Select your 2v2 teammate below (They must be in this server)**", 
                view=TeammateSelection(interaction, self.data, self.rblx)
            )

        self.interaction = interaction
        self.stop()

class TeammateSelection(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], data: User, rblx: RobloxUser, vip_url: Optional[str]=None):
        super().__init__(120, interaction, Object(custom_id_data={
            "users": {"defer_ephemerally": True, "get_user_data": True},
            "cancel": {"defer": True},
        }))
        
        self.data = data
        self.rblx = rblx
        self.vip_url = vip_url
        
    @ui.select(cls=ui.UserSelect, placeholder="Users", custom_id=f"users:{uuid.uuid4()}")
    async def users(self, interaction: discord.Interaction[MatchMaker], _: discord.SelectOption):
        other_user = self.users.values[0]
        
        if other_user.bot:
            return await interaction.followup.send(content=f"❌ **You can't queue up with a bot**", ephemeral=True)
        
        if other_user.id == interaction.user.id:
            return await interaction.followup.send(content=f"❌ **You can't queue up with yourself**", ephemeral=True)
        
        if interaction.client.states.get(interaction.user.id):
            return await interaction.followup.send(
                content = f"❌ **You can't queue up because you {interaction.client.states[interaction.user.id]}**", 
                ephemeral = True
            )
            
        if interaction.client.states.get(other_user.id):
            return await interaction.followup.send(
                content = f"❌ **You can't queue up with {other_user.mention} because they {interaction.client.states[other_user.id]}**", 
                ephemeral = True
            )
        
        other_data: User = interaction.extras['users'][other_user.id]
        other_rblx = await interaction.client.roblox_client.get_user(other_data.roblox_id)
        
        if not other_rblx:
            return await interaction.followup.send(content=f"⚠️ **{other_user.mention} is not verified**", ephemeral=True)
        
        if (
            interaction.user.id in other_data.settings.queue_request_blacklist
            or (not other_data.settings.queue_requests and interaction.user.id not in other_data.settings.queue_request_whitelist)
        ):
            return await interaction.followup.send(content=f"❌ **You can't queue up with {other_user.mention}**", ephemeral=True)
        
        if self.data.settings.region != other_data.settings.region:
            return await interaction.followup.send(
                content = (
                    f"❌ **You can't queue up with {other_user.mention} because you guys are not in the same match making region "
                    f"(`{Region(self.data.region).name}`)**"
                ),
                ephemeral=True
            )
        
        self.stop()
        
        time = datetime.timedelta(minutes=2, seconds=30)
        
        await interaction.edit_original_response(
            content= (
                f"**Invite sent to {other_user.mention}. "
                f"This queue invitation will expire {discord.utils.format_dt(discord.utils.utcnow() + time, "R")}**\n"
                "- *This message will be updated whether they accept it or not*"
            ), 
            view=None
        )
        
        invitation_view = QueueInvitation(time.total_seconds(), interaction.user)
        
        embed = discord.Embed(
            description = (
                f"## 2v2 Invitation\n"
                f"You have received an invite to play a 2v2 game with {interaction.user.mention} (`{interaction.user.name}`). "
                f"This invitation will expire **{discord.utils.format_dt(discord.utils.utcnow() + time, "R")}**\n"
            ),
            color = Colors.white
        )
        embed.set_footer(text="If you want to disable queue requests or blacklist this user, run /account")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        try:
            invitation_view.message = await other_user.send(embed=embed, view=invitation_view)
        except discord.HTTPException:
            return await interaction.edit_original_response(content=f"**{other_user.mention} has their DMs closed**")
        
        await invitation_view.wait()

        other_vip_url = None
        get_vip_view  = None
        if invitation_view.result == "accepted" and not self.vip_url:
            get_vip_view = PrivateServerOrSkip(interaction)

            await invitation_view.interaction.response.edit_message(
                content = (
                    f"Invitation from {interaction.user.mention} (`{interaction.user.name}`) was **accepted**. "
                    f"**If you have an active private server for FF2, please provide it below**"
                ),
                embed = None,
                view = get_vip_view,
            )
        else:
            await invitation_view.interaction.response.defer()

        await asyncio.sleep(1)
        
        if invitation_view.result == "denied":
            return await interaction.edit_original_response(content=f"**{other_user.mention} has denied your invitation**")
        elif invitation_view.result == "timeout":
            return await interaction.edit_original_response(content=f"**The invitation sent to {other_user.mention} has expired**")
        elif invitation_view.result == "already":
            return await interaction.edit_original_response(
                content = f"**You can't queue up with {other_user.mention} because you {interaction.client.states[interaction.user.id]}**"
            )
        
        interaction.client.states[interaction.user.id] = "are already finding a game"
        interaction.client.states[other_user.id] = "are already finding a game"

        if get_vip_view:
            await get_vip_view.wait()
            other_vip_url = get_vip_view.value
        
        # TODO:
        # leaderboard commands
        # add background commands to disable queue (admin only)
        #   for scheduled downtime, etc
        # add backgrounds to clear database queue & player states (dev only)
        # finish settings
        # stats
        # /result <match id>
        #   google vision API
        # somehow figure out how to verify if the private server is active (mostly impossible)
        
        private_server_text = f"✅ ({interaction.user.mention}'s server)" if self.vip_url else None
        private_server_text = f"✅ ({other_user.mention}'s server)" if not private_server_text and other_vip_url else private_server_text or '❌'
        
        trophies = int(round((self.data.trophies + other_data.trophies) / 2, 0))
        embed = discord.Embed(
            description = (
                f"## Your Team\n"
                f"`Player One:` {interaction.user.mention}\n"
                f"`Player Two:` {other_user.mention}\n"
                f"`Trophies:` 🏆 **{trophies}**\n"
                f"`Private Server:` {private_server_text}\n\n"
            ),
            color = Colors.white
        )

        if not self.vip_url and not other_vip_url:
            embed.set_footer(text="Since neither of you have a private server, it may take longer to find a game")
        
        view = FindGame(120, interaction)
        await interaction.edit_original_response(content=None, embed=embed, view=view)

        embed.description += f"*Waiting for {interaction.user.mention}...*"

        if get_vip_view:
            await get_vip_view.interaction.edit_original_response(content=None, embed=embed, view=None)
        elif invitation_view.interaction.response.is_done():
            await invitation_view.interaction.followup.send(embed=embed)
        
        if await view.wait():
            interaction.client.states.pop(interaction.user.id)
            interaction.client.states.pop(other_user.id)
            
            return await invitation_view.message.edit(
                content=f"⚠️ **{interaction.user.mention} (`{interaction.user.name}`) forgot to click 'find game' and the invitation expired**",
                delete_after = 150
            )
            
        interaction = view.interaction
        timeout     = datetime.timedelta(minutes=10)

        embed.description = "\n".join(embed.description.split("\n")[:4])
        embed.description += (
            "\n## <a:loading:1217310863623585832> Finding Game...\n"
            f"*You will be kicked out of the queue {discord.utils.format_dt(discord.utils.utcnow() + timeout, "R")}*"
        )
        
        try:
            await invitation_view.interaction.delete_original_response()
        except discord.HTTPException:
            pass
        
        player_two_cancel = CancelMatchmaking(None, interaction)
        player_two_task   = interaction.client.loop.create_task(player_two_cancel.wait())
        
        try:
            message = await other_user.send(embed=embed, view=player_two_cancel)
        except discord.HTTPException:
            interaction.client.states.pop(interaction.user.id)
            interaction.client.states.pop(other_user.id)
            
            player_two_cancel.stop()
            player_two_task.cancel()
            
            return await interaction.edit_original_response(
                content = f"**You can't queue up with {other_user.mention} anymore because they have their DMs closed**"
            )
        
        timeout_task = interaction.client.loop.create_task(asyncio.sleep(timeout.total_seconds()))
        
        player_one_cancel = CancelMatchmaking(timeout.total_seconds(), interaction)
        player_one_task   = interaction.client.loop.create_task(player_one_cancel.wait())
        await interaction.response.edit_message(embed=embed, view=player_one_cancel)

        team  = Object(player_one=interaction.user.id, player_two=other_user.id, region=other_data.settings.region, trophies=trophies, vip_url=self.vip_url or other_vip_url)
        queue = interaction.client.loop.create_task(interaction.client.queuer.join_queue(team, interaction.client.loop))
        
        done, pending = await asyncio.wait([player_one_task, player_two_task, queue, timeout_task], timeout=None, return_when=asyncio.FIRST_COMPLETED)
        result = done.pop()

        if result != queue:
            interaction.client.states.pop(interaction.user.id)
            interaction.client.states.pop(other_user.id)

            item = [x for x in interaction.client.queuer.queue if x.team == team][0]
            item.future.set_result(None)

            interaction.client.queuer.queue.remove(item)
        
        for task in pending:
            task.cancel()
            
        player_one_cancel.stop()
        player_two_cancel.stop()

        if result == timeout_task:
            await message.edit(content=f"❌ **Matchmaking took too long**", embed=None, view=None, delete_after=120)
            return await interaction.edit_original_response(content=f"❌ **Matchmaking took too long**", embed=None, view=None)
        
        if result == player_one_task:
            await player_one_cancel.interaction.response.edit_message(
                content = f"❌ **Matchmaking Canceled**", 
                embed = None, 
                view = None
            )
            
            return await message.edit(content=f"❌ **Matchmaking Canceled by {interaction.user.mention}**", embed=None, view=None, delete_after=120)
        
        if result == player_two_task:
            await player_two_cancel.interaction.response.edit_message(
                content = f"❌ **Matchmaking Canceled**",
                embed = None, 
                view = None,
                delete_after=30,
            )
            
            return await interaction.edit_original_response(content=f"❌ **Matchmaking Canceled by {other_user.mention}**", embed=None, view=None)
        
        matchup = queue.result()
        
        if isinstance(matchup, Object):
            interaction.client.states.pop(interaction.user.id)
            interaction.client.states.pop(other_user.id)
            
            canceled_by = matchup.canceled_by
            
            await interaction.delete_original_response()
            
            if canceled_by.id == interaction.user.id:
                return await message.edit(content=f"❌ **Matchmaking Canceled by {interaction.user.mention}**", embed=None, view=None, delete_after=120)
            else:
                await message.edit(content=f"❌ **Matchmaking Canceled**", embed=None, view=None, delete_after=30)
                return await interaction.followup.send(content=f"❌ **Matchmaking Canceled by {other_user.mention}**", ephemeral=True)
        
        interaction.client.states[interaction.user.id] = "are already in a game"
        interaction.client.states[other_user.id] = "are already in a game"
        
        team_one_players = Object(
            player_one=interaction.client.get_user(matchup.team_one.player_one),
            player_two=interaction.client.get_user(matchup.team_one.player_two),
        )

        team_two_players = Object(
            player_one=interaction.client.get_user(matchup.team_two.player_one),
            player_two=interaction.client.get_user(matchup.team_two.player_two),
        )

        embed.description = (
            f"# 2v2 Found\n"
            f":bangbang: `Match ID:` **{matchup.id}**\n"
            f"### Team One\n"
            f"`Player One:` {team_one_players.player_one.mention} (`{team_one_players.player_one.id}`)\n"
            f"`Player Two:` {team_one_players.player_two.mention} (`{team_one_players.player_two.id}`)\n"
            f"`Trophies:` 🏆 **{matchup.team_one.trophies}**\n"
            f"### Team Two\n"
            f"`Player One:` {team_two_players.player_one.mention} (`{team_two_players.player_one.id}`)\n"
            f"`Player Two:` {team_two_players.player_two.mention} (`{team_two_players.player_two.id}`)\n"
            f"`Trophies:` 🏆 **{matchup.team_two.trophies}**\n"
        )
        
        await interaction.edit_original_response(embed=embed, view=None)
        await message.edit(embed=embed, view=None)

    @ui.button(label="Queue Solo", style=discord.ButtonStyle.blurple, disabled=True)
    async def solo(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        await interaction.edit_original_response(content="...", view=None)
    
    @ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id=f"cancel:{uuid.uuid4()}")
    async def cancel(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        self.stop()
        await self.on_timeout()

class GetPrivateServerLink(BaseModal):
    link = ui.TextInput(
        label = "Private Server URL (NOT REQUIRED)",
        placeholder = f"Please paste your private server URL here",
        min_length = 100,
        required = False
    )
    
    def __init__(self, interaction: discord.Interaction[MatchMaker]):
        super().__init__("Private Server", 120, interaction, Object(defer_ephemerally=True))
        
        self.value = None

    async def on_submit(self, interaction: discord.Interaction[MatchMaker]):
        value = self.link.value

        if value:
            if not FOOTBALL_FUSION_LINK.match(value):
                return await interaction.followup.send(content = f"❌ **That was not a link to a FF2 private server**")

            self.value = value

        self.interaction = interaction
        self.stop()

class QueueInvitation(BaseView):
    def __init__(self, timeout: float, inviter: discord.Member):
        super().__init__(timeout)
        
        self.message = None
        self.inviter = inviter
        self.result  = None
        
    @ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if interaction.client.states.get(interaction.user.id):
            self.result = "denied"
            self.stop()
            
            return await interaction.response.edit_message(
                content = f"❌ **You can't queue up because you {interaction.client.states[interaction.user.id]}**", 
                embed = None,
                view = None,
            )
            
        if interaction.client.states.get(self.inviter.id):
            self.result = "already"
            self.stop()
            
            return await interaction.response.edit_message(
                content = f"❌ **You can't queue up with {self.inviter.mention} because they {interaction.client.states[self.inviter.id]}**", 
                embed = None,
                view = None,
            )
            
        #await interaction.response.edit_message(
        #    content = f"Invitation from {self.inviter.mention} (`{self.inviter.name}`) was **accepted**. Now waiting for your team to enter the match making queue.",
        #    embed = None,
        #    view = None,
        #)
        
        self.interaction = interaction
        self.result = "accepted"
        self.stop()
    
    @ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        await interaction.response.edit_message(
            content = f"Invitation from {self.inviter.mention} (`{self.inviter.name}`) was **denied**",
            embed = None,
            view = None,
            delete_after = 30,
        )
        
        self.result = "denied"
        self.stop()
        
    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(
                content = f"Invitation from {self.inviter.mention} (`{self.inviter.name}`) has **expired**",
                embed = None,
                view = None,
                delete_after = 30,
            )
            
        self.result = "timeout"

class FindGame(BaseView):
    @ui.button(label="Find Game", style=discord.ButtonStyle.blurple)
    async def find_game(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        self.interaction = interaction
        self.stop()

class CancelMatchmaking(BaseView):
    @ui.button(label="Cancel Matchmaking", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        self.interaction = interaction
        self.stop()

class Queue(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="queue", 
        description="queue up for a 2v2 game",
        extras = Object(defer_ephemerally=True, get_user_data=True)
    )
    async def queue(self, interaction: discord.Interaction[MatchMaker]):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(content=f"⚠️ **You are not verified. Run /account to verify**")
        
        if interaction.client.states.get(interaction.user.id):
            return await interaction.followup.send(content=f"❌ **You can't queue up because you {interaction.client.states[interaction.user.id]}**")
        
        await interaction.followup.send(
            content = f"**If you have an active private server for FF2, please provide it below**",
            view = PrivateServerOrSkip(interaction, data, rblx)
        )
        
async def setup(bot: MatchMaker):
    cog = Queue(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", True)
    
    await bot.add_cog(cog)