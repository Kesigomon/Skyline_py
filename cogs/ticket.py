import datetime

import discord
from discord.ext import commands

from .general import ticket_category


class Ticket(commands.Cog):

    def __init__(self, bot, name=None):
        self.bot: commands.Bot = bot
        self.name = name if name is not None else type(self).__name__
        self.limiter = []

    @commands.Cog.listener()
    async def on_ready(self):
        self.category: discord.CategoryChannel = self.bot.get_channel(ticket_category)
        for channel in self.category.text_channels:  # type: discord.TextChannel
            try:
                # 最後のメッセージを取得しようとする
                last = await channel.history().next()
            except discord.NoMoreItems:
                # もしメッセージがなければ、チャンネルの作成時間
                dt = channel.created_at
            else:
                # メッセージがあれば、最後の発言の時間
                dt = last.created_at
            # 先で取得した時間から7日以上経っていたら、チャンネルを消す
            if (datetime.datetime.utcnow() - dt) >= datetime.timedelta(days=7):
                await channel.delete()

    @commands.command()
    async def ticket(self, ctx: commands.Context):
        if ctx.author in self.limiter:
            await ctx.send("あなたはチャンネルを作成できません。")
            return
        self.limiter.append(ctx.author)
        overwrites = {
            ctx.guild.default_role:
                discord.PermissionOverwrite.from_pair(
                    discord.Permissions.none(),
                    discord.Permissions.all()
                ),
            ctx.author:
                discord.PermissionOverwrite.from_pair(
                    discord.Permissions(388176),
                    discord.Permissions(2 ** 53 + ~388176)
                )
        }
        channel = await self.category.create_text_channel(str(ctx.author), overwrites=overwrites)
        await ctx.send(f"作成しました {channel.mention}")