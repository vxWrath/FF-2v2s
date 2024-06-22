import datetime
import discord

from discord import app_commands, ui
from discord.ext import commands
from typing import Optional

from resources import MatchMaker, Extras, Colors, staff_only, Config

class Ban(commands.Cog):
    def __init__(self, bot: MatchMaker):
        self.bot: MatchMaker = bot

    @app_commands.command(
        name="playban", 
        description="ban someone from playing 2v2s",
        extras=Extras(defer=True, user_data=True),
    )
    @app_commands.describe(member="the member to ban from playing", time="how long the member should be banned")
    @app_commands.choices(time=[
        app_commands.Choice(name="1 hour", value=3600),
        app_commands.Choice(name="4 hours", value=14400),
        app_commands.Choice(name="8 hours", value=28800),
        app_commands.Choice(name="12 hours", value=43200),
        app_commands.Choice(name="1 day", value=86400),
        app_commands.Choice(name="3 days", value=259200),
        app_commands.Choice(name="7 days", value=604800),
        app_commands.Choice(name="14 days", value=1209600),
        app_commands.Choice(name="30 days", value=2592000),
        app_commands.Choice(name="60 days", value=51840000),
        app_commands.Choice(name="90 days", value=7776000),
        app_commands.Choice(name="Permanently", value=0),
    ])
    @staff_only()
    async def ban(self, interaction: discord.Interaction[MatchMaker], member: discord.Member, time: app_commands.Choice[int]):
        member_data  = interaction.extras['users'][member.id]
        ban_extended = True if member_data.banned else False

        member_data.total_bans  += 1
        member_data.banned       = True
        member_data.banned_until = None

        if time.value == 0:
            content = f"{member.mention} has been permanently banned from playing by {interaction.user.mention}"
        else:
            banned_until  = discord.utils.utcnow() + datetime.timedelta(seconds=time.value)
            if time.value >= 86400:
                banned_until += datetime.timedelta(seconds=(60 - banned_until.minute) * 60 - banned_until.second) # round up to the nearest hour

            member_data.banned_until = banned_until

            content = f"{member.mention} has been temporarily banned from playing until {discord.utils.format_dt(banned_until, "f")} by {interaction.user.mention}"

        if ban_extended:
            content += f" (ban extended)"

        await interaction.followup.send(content=content)
        await interaction.client.database.update_user(member_data)

        embed = discord.Embed(
            description = "## Member Banned",
            color = Colors.red,
            timestamp = discord.utils.utcnow()
        )
        embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
        embed.add_field(name="Members Bans", value=f"`{member_data.total_bans}`", inline=True)

        embed.add_field(name="Banned Until", value=(
            f"{discord.utils.format_dt(banned_until, "f") if time.value else '`Permanently`'} "
            f"{f"({discord.utils.format_dt(banned_until, "R")})" if time.value else ''}"
        ), inline=False)

        embed.add_field(name="Staff Member", value=f"{interaction.user.mention} ({interaction.user.id})", inline=True)
        embed.add_field(name="Ban Extended", value=f"{'✅' if ban_extended else '❌'}", inline=True)

        embed.set_footer(text="Banned at")

        channel = interaction.client.get_channel(Config.get().BAN_LOG)
        await channel.send(embed=embed)

    @app_commands.command(
        name="unplayban", 
        description="unban someone from playing 2v2s",
        extras=Extras(defer=True, user_data=True),
    )
    @app_commands.describe(member="the member to unban")
    @staff_only()
    async def unban(self, interaction: discord.Interaction[MatchMaker], member: discord.Member):
        member_data  = interaction.extras['users'][member.id]

        if not member_data.banned:
            return await interaction.followup.send(content=f"{member.mention} is not banned", ephemeral=True)

        member_data.total_bans  -= 1
        member_data.banned       = False

        await interaction.followup.send(content=f"{member.mention} has been unbanned from playing by {interaction.user.mention}")

        embed = discord.Embed(
            description = "## Member Unbanned",
            color = Colors.blank,
            timestamp = discord.utils.utcnow()
        )
        embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
        embed.add_field(name="Members Bans", value=f"`{member_data.total_bans}`", inline=True)

        embed.add_field(name="Staff Member", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        embed.set_footer(text="Unbanned at")

        channel = interaction.client.get_channel(Config.get().BAN_LOG)
        await channel.send(embed=embed)

        member_data.banned_until = None
        await interaction.client.database.update_user(member_data)
        
async def setup(bot: MatchMaker):
    cog = Ban(bot)
    
    for command in cog.walk_app_commands():
        if hasattr(command, "callback"):
            setattr(command.callback, "__name__", f"{cog.qualified_name.lower()}_{command.callback.__name__}")
            setattr(command, "guild_only", False)
    
    await bot.add_cog(cog)