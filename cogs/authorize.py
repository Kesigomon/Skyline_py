import random

import discord
from discord.ext import commands

from .general import (
    ZATSUDAN_FORUM_ID,
    authorize_message,
    authorize_message_channel,
    default_roles_id,
    agree_messages,
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
        name = member.display_name
        des1 = random.choice(agree_messages).format(name, member.guild.me.display_name)
        embed = discord.Embed(
            title='{0}さんが参加しました。'.format(name),
            colour=0x2E2EFE,
            description=(
                '```\n{3}\n```\n'
                'ようこそ{0}さん、よろしくお願いします！\n'
                'このサーバーの現在の人数は{1}です。\n'
                '{2}に作られたアカウントです。'
            ).format(name, member.guild.member_count, member.created_at, des1)
        )
        embed.set_thumbnail(url=member.avatar_url)

        await self.bot.get_channel(main_channel).send(embed=embed)