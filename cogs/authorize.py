import discord
from discord.ext import commands

from .general import (
    ZATSUDAN_FORUM_ID,
    authorize_message,
    authorize_message_channel,
    default_roles_id,
    main_channel
)


class Authorize(commands.Cog):

    def __init__(self, bot, name=None):
        self.bot: commands.Bot = bot
        self.name = name if name is not None else type(self).__name__

    def get_member(self, _id):
        return self.bot.get_guild(ZATSUDAN_FORUM_ID).get_member(_id)

    @property
    def default_roles(self):
        guild = self.bot.get_guild(ZATSUDAN_FORUM_ID)
        return [guild.get_role(i) for i in default_roles_id]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if (
            payload.channel_id != authorize_message_channel
            or payload.message_id != authorize_message
            or payload.emoji.name != "\U0001f44d"
        ):
            return
        member = self.get_member(payload.user_id)
        # 何らかの役職を持っていれば認証処理は行わない
        if len(member.roles) >= 2:
            return
        await member.add_roles(*self.default_roles)
        content = (
            f"ようこそ{member.mention}さん！{member.guild.name}へ！\n"
            f"<#515467585152876544> よければ自己紹介をお願いします！"
        )
        await self.bot.get_channel(main_channel).send(content)