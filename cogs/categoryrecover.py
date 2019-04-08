import discord
from discord.ext import commands

import asyncio


class Category_recover(commands.Cog):  # 言わずと知れたカテゴリリカバリ機能
    __slots__ = ('client', 'category_cache', 'name')

    def __init__(self, client, name=None):
        self.client: discord.Client = client
        self.name = name if name is not None else type(self).__name__

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
        if isinstance(channel, discord.CategoryChannel):
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
