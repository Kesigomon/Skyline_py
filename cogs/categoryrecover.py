import discord
from discord.ext import commands


import asyncio

from .general import is_subowner


class Category_recover(commands.Cog):  # 言わずと知れたカテゴリリカバリ機能
    __slots__ = ('client', 'category_cache', 'name', 'exclusion')

    def __init__(self, client, name=None):
        self.client: discord.Client = client
        self.name = name if name is not None else type(self).__name__
        self.exclusion = []

    @commands.command()
    async def category_delete(self, ctx, category:discord.CategoryChannel):
        if not is_subowner(ctx.author):
            await ctx.send("あなたはこのコマンドを実行できません。")
            return
        mes: discord.Message = await ctx.send(f"カテゴリー「{category.name}」を削除してもよろしいですか？")
        [await mes.add_reaction(i) for i in ("\u2705", "\u274c")]
        def check(react: discord.Reaction, usr):
            return(
                usr == ctx.author
                and react.message.id == mes.id
                and react.message.channel == mes.channel
                and react.me
            )
        reaction, user = await self.client.wait_for("reaction_add", check=check)
        if reaction.emoji == "\u2705":
            self.exclusion.append(category)
            await category.delete()
            await ctx.send("削除しました")
        else:
            await ctx.send("中止しました")

    @commands.Cog.listener()
    async def on_ready(self):
        self.category_cache \
            = {c.id: c.name for c in self.client.get_all_channels()
                if isinstance(c, discord.CategoryChannel)}

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if isinstance(channel, discord.CategoryChannel):
            self.category_cache[channel.id] = channel.name

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if isinstance(channel, discord.CategoryChannel) and channel not in self.exclusion:
            if channel.name not in (c.name for c in channel.guild.categories):
                await channel.guild.create_category(
                    name=channel.name,
                    overwrites=channel.overwrites
                )

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.category_id is not None and after.category_id is None:
            name = self.category_cache[before.category_id]
            guild = after.guild
            while before.category_id in (c.id for c in after.guild.categories):
                try:
                    await self.client.wait_for(
                        'guild_channel_delete',
                        check=lambda c: c == before.category,
                        timeout=1)
                except asyncio.TimeoutError:
                    continue
                else:
                    break
            a = True
            while name not in (c.name for c in guild.categories):
                try:
                    new_category = await self.client.wait_for(
                        'guild_channel_create',
                        check=lambda c: c.guild == guild and name == c.name,
                        timeout=1)
                except asyncio.TimeoutError:
                    continue
                else:
                    a = False
                    break
            if a:
                new_category = next(c for c in guild.categories if c.name == name)
            await after.edit(category=new_category)
