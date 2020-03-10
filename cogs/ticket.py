import datetime
import asyncio

import discord
from discord.ext import commands

from .general import ticket_category, is_subowner
from textwrap import dedent


class Ticket(commands.Cog):

    def __init__(self, bot, name=None):
        self.bot: commands.Bot = bot
        self.name = name if name is not None else type(self).__name__
        self.ready = asyncio.Event()
        self.overwrite_default = discord.PermissionOverwrite.from_pair(
            discord.Permissions(379968),
            discord.Permissions(2 ** 53 + ~379968)
        )
        self.overwrite_owner = discord.PermissionOverwrite.from_pair(
            discord.Permissions(388160),
            discord.Permissions(2 ** 53 + ~388160)
        )

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
        self.ready.set()

    def is_own(self, member, channel):
        if self.category != channel.category:
            return False
        try:
            return int(channel.topic.splitlines()[0]) == member.id
        except TypeError:
            return False

    def get_channel(self, member):
        return next((
            channel for channel in self.category.text_channels
            if self.is_own(member, channel)
        ), None)

    async def cog_before_invoke(self, ctx):
        await self.ready.wait()

    @commands.group(invoke_without_command=True)
    async def ticket(self, ctx: commands.Context, members: commands.Greedy[discord.Member]):
        member = ctx.author
        if self.get_channel(member) is not None and not is_subowner(member):
            await ctx.send("あなたはすでにチャンネルを作っています")
            return
        overwrites = {
            ctx.guild.default_role:
                discord.PermissionOverwrite.from_pair(
                    discord.Permissions.none(),
                    discord.Permissions.all()
                ),
            member: self.overwrite_owner

        }
        topic = dedent(f"""
            {member.id}
            # トピックは、作成者の情報を保存するのに利用しています。
            # 絶対に__**変えないで**__ください。
        """)
        channel = await self.category.create_text_channel(str(ctx.author), overwrites=overwrites, topic=topic)
        await ctx.send(f"作成しました {channel.mention}")
        await asyncio.gather(*(self.add_member(channel, member) for member in members))

    @ticket.command()
    async def invite(self, ctx, members: commands.Greedy[discord.Member]):
        channel = self.get_channel(ctx.author)
        if channel is None:
            await ctx.send("あなたはまだチャンネルを作っていません\n"
                           "まずはsk!ticketでチャンネルを作ってください")
            return
        await asyncio.gather(*(self.add_member(channel, member) for member in members))
        await ctx.send("追加しました")

    async def add_member(self, channel: discord.TextChannel, member: discord.Member):
        await channel.set_permissions(member, overwrite=self.overwrite_default)

    @ticket.command()
    async def leave(self, ctx: commands.Context):
        channel = ctx.channel
        if channel.category != self.category:
            await ctx.send("ここでは使えません")
            return
        if self.is_own(ctx.author, channel):
            emojis = ('\u2705', '\u274c')
            message = await channel.send("本当に削除して良い？")

            def check1(reaction: discord.Reaction, user):
                return (
                    reaction.message.id == message.id
                    and reaction.message.channel == message.channel
                    and user == ctx.author
                )

            [self.bot.loop.create_task(message.add_reaction(i))
             for i in emojis]
            reaction, _ = await self.bot.wait_for('reaction_add', check=check1)
            if reaction.emoji == '\u2705':
                await channel.delete()
            else:
                await ctx.send("キャンセルしました")
        else:
            await channel.set_permissions(ctx.author, overwrite=None)
