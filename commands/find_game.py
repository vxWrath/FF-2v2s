import asyncio
import datetime
import discord
import re
import uuid

from discord import app_commands, ui
from discord.ext import commands

from resources import MatchMaker, Object, Extras, User, Region, RobloxUser, BaseView, BaseModal, Colors, THREAD_CHANNEL

FOOTBALL_FUSION_LINK  = "https://www.roblox.com/games/8204899140/Football-Fusion-2#!/game-instances"
FOOTBALL_FUSION_REGEX = re.compile(r"(?:https:\/\/www\.roblox\.com\/games\/8204899140\/football-fusion-2\?privateserverlinkcode=)([0-9]{25,})", flags=re.IGNORECASE)

class LinkOrSkip(BaseView):
    def __init__(self, interaction: discord.Interaction[MatchMaker], player: str, data: User, rblx: RobloxUser):
        super().__init__(240, interaction, Extras(custom_id=Object(
            skip = Extras(defer=True)
        )))

        self.player = player
        self.data   = data
        self.rblx   = rblx
        
        if self.player == "two":
            self.value = None

    @ui.button(label="Provide Link", style=discord.ButtonStyle.blurple)
    async def provide(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        modal = GetLink(interaction)
        await interaction.response.send_modal(modal)

        if await modal.wait():
            self.stop()
            return await self.on_timeout()
        
        if modal.value is discord.utils.MISSING:
            return
        
        interaction = modal.interaction

        if self.player == "one":
            embed = discord.Embed(
                description = f"**Select your 2v2 teammate below (They must be in this server)**",
                color = Colors.blank
            )
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)

            await interaction.edit_original_response(
                embed = embed,
                view = SelectTeammate(interaction, self.data, self.rblx, modal.value),
            )
        else:
            self.value = modal.value

        self.stop()

    @ui.button(label="Skip & Continue", style=discord.ButtonStyle.gray, custom_id=f"skip:{uuid.uuid4()}")
    async def skip(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if self.player == "one":
            embed = discord.Embed(
                description = f"**Select your 2v2 teammate below (They must be in this server)**",
                color = Colors.blank
            )
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)

            await interaction.edit_original_response(
                embed = embed,
                view = SelectTeammate(interaction, self.data, self.rblx, None),
            )

        self.stop()

class GetLink(BaseModal):
    link = ui.TextInput(
        label = "Private Server URL (NOT REQUIRED)",
        placeholder = f"Please paste your private server URL here",
        min_length = 100,
        required = False
    )
    
    def __init__(self, interaction: discord.Interaction[MatchMaker]):
        super().__init__("Private Server", 120, interaction, Extras(defer_ephemerally=True))
        
        self.value = discord.utils.MISSING

    async def on_submit(self, interaction: discord.Interaction[MatchMaker]):
        value = self.link.value

        if value:
            if not FOOTBALL_FUSION_REGEX.match(value):
                return await interaction.followup.send(content=f"❌ **That was not a link to a Football Fusion 2 private server**", ephemeral=True)

        self.value = value
        self.interaction = interaction
        self.stop()

class SelectTeammate(BaseView):
    def __init__(self, interaction: discord.Interaction, data: User, rblx: RobloxUser, private_server: str):
        super().__init__(240, interaction, Extras(custom_id=Object(
            users = Extras(defer=True, user_data=True),
            cancel = Extras(defer=True)
        )))

        self.data = data
        self.rblx = rblx
        self.private_server = private_server

    @ui.select(cls=ui.UserSelect, placeholder="Users", custom_id=f"users:{uuid.uuid4()}")
    async def users(self, interaction: discord.Interaction[MatchMaker], _: discord.SelectOption):
        other_user = self.users.values[0]
        
        if other_user.bot:
            return await interaction.followup.send(content=f"❌ **You can't party up with a bot**", ephemeral=True)
        
        if other_user.id == interaction.user.id:
            return await interaction.followup.send(content=f"❌ **You can't party up with yourself**", ephemeral=True)
        
        if interaction.client.states.get(interaction.user.id):
            return await interaction.followup.send(content=f"❌ **You can't party up because you {interaction.client.states[interaction.user.id].message}**", ephemeral=True)
            
        if interaction.client.states.get(other_user.id):
            return await interaction.followup.send(content=f"❌ **You can't party up with {other_user.mention} because they {interaction.client.states[other_user.id].message}**", ephemeral=True)
        
        other_data = interaction.extras['users'][other_user.id]
        other_rblx = await interaction.client.roblox_client.get_user(other_data.roblox_id)
        
        if not other_rblx:
            return await interaction.followup.send(content=f"⚠️ **{other_user.mention} is not verified**", ephemeral=True)
        
        if (
            interaction.user.id in other_data.settings.queue_request_blacklist
            or (not other_data.settings.queue_requests and interaction.user.id not in other_data.settings.queue_request_whitelist)
        ):
            return await interaction.followup.send(content=f"❌ **You are not allowed to party up with {other_user.mention}**", ephemeral=True)
        
        if self.data.settings.region != other_data.settings.region:
            return await interaction.followup.send(
                content = (
                    f"❌ **You can't party up with {other_user.mention} because you guys are not in the same match making region "
                    f"(`{Region(self.data.region).name}`)**"
                ),
                ephemeral=True
            )
        
        self.stop()

        timeout = datetime.timedelta(minutes=2, seconds=30)
        embed   = discord.Embed(
            description = (
                f"**Invite sent to {other_user.mention}. "
                f"This party invite will expire {discord.utils.format_dt(discord.utils.utcnow() + timeout, "R")}**\n"
            ),
            color = Colors.blank,
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="This message will be updated whether they accept it or not")

        await interaction.edit_original_response(embed=embed, view=None)

        embed.description = (
            f"## Party Invite (2v2)\n"
            f"You have received a party invite to play 2v2s with {interaction.user.mention}. "
            f"This party invite will expire **{discord.utils.format_dt(discord.utils.utcnow() + timeout, "R")}**\n"
        )
        embed.set_footer(text="If you want to disable queue requests from this user, run /account")
        
        try:
            invite = Invite(timeout=timeout.total_seconds(), inviter=interaction.user, private_server=self.private_server)
            invite.message = await other_user.send(embed=embed, view=invite)
        except discord.HTTPException:
            return await interaction.edit_original_response(content=f"❌ **{other_user.mention} has their DMs closed**", embed=None)
        
        embed    = embed.remove_footer()
        timedout = await invite.wait()

        if timedout:
            await asyncio.sleep(1)

            embed.description = f"**The invite sent to {other_user.mention} has expired**"
            return await interaction.edit_original_response(embed=embed)
        elif invite.result == "declined":
            await asyncio.sleep(1)
            
            embed.description = f"**{other_user.mention} has declined your party invite**"
            return await interaction.edit_original_response(embed=embed)
        elif invite.result == "already":
            await asyncio.sleep(1)
            
            embed.description = f"**You can't party up with {other_user.mention} because you {interaction.client.states[interaction.user.id].message}**"
            return await interaction.edit_original_response(embed=embed)
        
        private_server_text = f"✅ ({interaction.user.mention}'s server)" if self.private_server else None
        private_server_text = f"✅ ({other_user.mention}'s server)" if not private_server_text and invite.private_server else private_server_text or '❌'
        
        trophies = int(round((self.data.trophies + other_data.trophies) / 2, 0))
        embed.description = (
            f"## Your Team\n"
            f"`Player:` {interaction.user.mention}\n"
            f"`Player:` {other_user.mention}\n"
            f"`Trophies:` 🏆 **{trophies}**\n"
            f"`Private Server:` {private_server_text}\n\n"
        )
        
        if not self.private_server and not invite.private_server:
            embed.set_footer(text="Since neither of you have a private server, it may take longer to find a game")

        view = FindGameButton(120, interaction)
        await interaction.edit_original_response(embed=embed, view=view)
        
        embed.set_author(name=other_user.name, icon_url=other_user.display_avatar.url)
        embed.description += f"*Waiting for {interaction.user.mention}...*"
        
        if invite.interaction.response.is_done():
            await invite.interaction.edit_original_response(embed=embed, view=None)
        else:
            await invite.interaction.response.edit_message(embed=embed, view=None)
            
        if await view.wait():
            interaction.client.states.pop(interaction.user.id, None)
            interaction.client.states.pop(other_user.id, None)
            
            embed.remove_footer()
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            
            embed.description = f"❌ **{interaction.user.mention} took too long and the party invite has expired**"
            return await invite.message.edit(embed=embed, delete_after=120)
        
        await view.interaction.response.defer()
        
        interaction = view.interaction
        timeout     = datetime.timedelta(minutes=10)
        
        embed.description = "\n".join(embed.description.split("\n")[:5])
        embed.description += (
            "\n## <a:loading:1217310863623585832> Finding Game...\n"
            f"*You will be kicked out of the queue {discord.utils.format_dt(discord.utils.utcnow() + timeout, "R")}*"
        )
        
        await invite.message.delete()
        
        p2_cancel = CancelMatchmakingButton(None, interaction)
        p2_task   = interaction.client.loop.create_task(p2_cancel.wait())
        
        try:
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            message = await other_user.send(embed=embed, view=p2_cancel)
        except discord.HTTPException:
            interaction.client.states.pop(interaction.user.id, None)
            interaction.client.states.pop(other_user.id, None)
            
            embed.remove_footer()
            
            embed.description = f"❌ **You can't party up with {other_user.mention} anymore because they closed their DMs**"
            return await interaction.edit_original_response(embed=embed, view=None)
        
        timeout_task = interaction.client.loop.create_task(asyncio.sleep(timeout.total_seconds()))
        
        p1_cancel = CancelMatchmakingButton(None, interaction)
        p1_task   = interaction.client.loop.create_task(p1_cancel.wait())
        
        embed.set_author(name=other_user.name, icon_url=other_user.display_avatar.url)
        await interaction.edit_original_response(embed=embed, view=p1_cancel)
        
        parent = interaction.client.get_channel(THREAD_CHANNEL)
        team   = Object(
            player_one=interaction.user.id, 
            player_two=other_user.id, 
            region=other_data.settings.region, 
            trophies=trophies, 
            private_server=self.private_server or invite.private_server,
            score=0
        )
        match_making_task = interaction.client.loop.create_task(interaction.client.queuer.join_queue(team, interaction.client.loop, parent))
        
        done, pending = await asyncio.wait(
            [p1_task, p2_task, timeout_task, match_making_task],
            timeout = None,
            return_when = asyncio.FIRST_COMPLETED,
        )
        task = done.pop()
        
        if task != match_making_task:
            interaction.client.states.pop(interaction.user.id, None)
            interaction.client.states.pop(other_user.id, None)
            
            item = [x for x in interaction.client.queuer.queue if x.team == team][0]
            item.future.set_result(None)
            
            interaction.client.queuer.queue.remove(item)
            
        for pending_task in pending:
            pending_task.cancel()
            
        embed.remove_footer()
            
        p1_cancel.stop()
        p2_cancel.stop()
        
        if task == timeout_task:
            embed.description = f"❌ **Matchmaking took too long**"
            embed.set_author(name=other_user.name, icon_url=other_user.display_avatar.url)
            await interaction.edit_original_response(embed=embed, view=None)
            
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            return await message.edit(embed=embed, view=None, delete_after=120)
        
        if task == p1_task:
            embed.description = f"❌ **Matchmaking canceled**"
            embed.set_author(name=other_user.name, icon_url=other_user.display_avatar.url)
            await p1_cancel.interaction.response.edit_message(embed=embed, view=None)  
            
            embed.description = f"❌ **Matchmaking canceled by {interaction.user.mention}**"
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            return await message.edit(embed=embed, view=None, delete_after=120)
        
        if task == p2_task:
            embed.description = f"❌ **Matchmaking canceled**"
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
            await p2_cancel.interaction.response.edit_message(embed=embed, view=None, delete_after=30)
        
            embed.description = f"❌ **Matchmaking canceled by {other_user.mention}**"
            embed.set_author(name=other_user.name, icon_url=other_user.display_avatar.url)
            return await interaction.edit_original_response(embed=embed, view=None)
        
        matchup = match_making_task.result()
        
        if isinstance(matchup, Object):
            interaction.client.states.pop(interaction.user.id, None)
            interaction.client.states.pop(other_user.id, None)
            
            if matchup.canceled_by.id == interaction.user.id:
                embed.description = f"❌ **Matchmaking canceled by {interaction.user.mention}**"
                embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
                return await message.edit(embed=embed, view=None, delete_after=120)
            else:
                embed.description = f"❌ **Matchmaking canceled by you**"
                embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
                await message.edit(embed=embed, view=None, delete_after=60)
            
                embed.description = f"❌ **Matchmaking canceled by {other_user.mention}**"
                embed.set_author(name=other_user.name, icon_url=other_user.display_avatar.url)
                return await interaction.followup.send(embed=embed, ephemeral=True)
            
        interaction.client.states[interaction.user.id] = Object(last_updated=discord.utils.utcnow(), message="are already in a game", type="in-game")
        interaction.client.states[other_user.id] = Object(last_updated=discord.utils.utcnow(), message="are already in a game", type="in-game")
        
        thread = parent.get_thread(matchup.thread)
        
        embed.description = (
            f"## 2v2 Found!\n"
            f"`Match ID:` **{matchup.id}**\n"
            f"`Thread:` **{thread.mention}**"
        )

        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        await interaction.edit_original_response(embed=embed, view=None)
        
        embed.set_author(name=other_user.name, icon_url=other_user.display_avatar.url)
        await message.edit(embed=embed, view=None)

    @ui.button(label="Queue Solo", style=discord.ButtonStyle.blurple, disabled=True)
    async def solo(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        await interaction.edit_original_response(content="...", view=None)
    
    @ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id=f"cancel:{uuid.uuid4()}")
    async def cancel(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        await self.cancel_view()

class Invite(BaseView):
    def __init__(self, timeout: float, inviter: discord.Member, private_server: str):
        super().__init__(timeout)
        
        self.inviter = inviter

        self.message = None
        self.result  = None
        self.private_server = private_server

    @ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        if interaction.client.states.get(interaction.user.id):
            embed = discord.Embed(
                description = f"❌ **You can't party up because you {interaction.client.states[interaction.user.id].message}. Deleting this message {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=30), "R")}**",
                color = Colors.blank
            )
            embed.set_author(name=self.inviter.name, icon_url=self.inviter.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=None, delete_after=30)

            self.result = "declined"
            self.stop()

        if interaction.client.states.get(self.inviter.id):
            embed = discord.Embed(
                description = f"❌ **You can't party up with {self.inviter.mention} because they {interaction.client.states[self.inviter.id].message}. Deleting this message {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=30), "R")}**",
                color = Colors.blank
            )
            embed.set_author(name=self.inviter.name, icon_url=self.inviter.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=None, delete_after=30)

            self.result = "already"
            self.stop()

        self.result = "accepted"

        interaction.client.states[interaction.user.id] = Object(last_updated=discord.utils.utcnow(), message="are already finding a game", type="finding")
        interaction.client.states[self.inviter.id] = Object(last_updated=discord.utils.utcnow(), message="are already finding a game", type="finding")

        if not self.private_server:
            embed = discord.Embed(
                description = (
                    f"Party invite from {interaction.user.mention} was **accepted**. "
                    f"**If you have an active private server for [Football Fusion 2]({FOOTBALL_FUSION_LINK}), provide the link below.**"
                ),
                color = Colors.blank
            )
            embed.set_author(name=self.inviter.name, icon_url=self.inviter.display_avatar.url)
            
            link = LinkOrSkip(interaction, "two", None, None)
            await interaction.response.edit_message(embed=embed, view=link)

            await link.wait()
            self.private_server = link.value

        self.interaction = interaction
        self.stop()

    @ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        embed = discord.Embed(
            description = f"**You have declined the party invite from {self.inviter.mention}. Deleting this message {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=30), "R")}**",
            color = Colors.blank
        )
        embed.set_author(name=self.inviter.name, icon_url=self.inviter.display_avatar.url)
        await interaction.response.edit_message(embed=embed, view=None, delete_after=30)
        
        self.result = "declined"
        self.stop()
        
    async def on_timeout(self) -> None:
        if self.message:
            embed = discord.Embed(
                description = f"**The party invite from {self.inviter.mention} has expired. Deleting this message {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(120), "R")}**",
                color = Colors.blank
            )
            embed.set_author(name=self.inviter.name, icon_url=self.inviter.display_avatar.url)
            
            try:
                await self.message.edit(embed=embed, view=None, delete_after=120)
            except discord.HTTPException:
                pass

class FindGameButton(BaseView):
    @ui.button(label="Find Game", style=discord.ButtonStyle.blurple)
    async def find_game(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        self.interaction = interaction
        self.stop()
        
class CancelMatchmakingButton(BaseView):
    @ui.button(label="Cancel Matchmaking", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction[MatchMaker], _: discord.Button):
        self.interaction = interaction
        self.stop()

class FindGame(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot
        
    @app_commands.command(
        name="findgame", 
        description="find a 2v2 matchup",
        extras = Extras(defer_ephemerally=True, user_data=True)
    )
    async def findgame(self, interaction: discord.Interaction[MatchMaker]):
        data = interaction.extras['users'][interaction.user.id]
        rblx = await self.bot.roblox_client.get_user(data.roblox_id)
        
        if not rblx:
            return await interaction.followup.send(content=f"⚠️ **You are not verified. Run /account to verify**")
        
        if interaction.client.states.get(interaction.user.id):
            return await interaction.followup.send(content=f"❌ **You can't party up because you {interaction.client.states[interaction.user.id].message}**")
        
        embed = discord.Embed(
            description = f"**If you have an active private server for [Football Fusion 2]({FOOTBALL_FUSION_LINK}), provide the link below.**",
            color = Colors.blank
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(
            embed = embed,
            view  = LinkOrSkip(interaction, "one", data, rblx)
        )
        
async def setup(bot: MatchMaker):
    cog = FindGame(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", True)
    
    await bot.add_cog(cog)