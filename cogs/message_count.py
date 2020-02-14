import asyncio
import re

import discord
from discord.ext import commands


class Message_count(commands.Cog):
    __slots__ = ('bot', 'count', 'channel_id', 'channel', 'guild', 'event', 'firstlaunch', 'name')
    pattern1 = re.compile(r'(\d+)')

    @staticmethod
    def not_bot(message):
        return not message.author.bot

    def __init__(self, bot, name=None):
        self.bot: commands.Bot = bot
        self.name = name if name is not None else type(self).__name__
        self.count = 0
        self.event = asyncio.Event(loop=self.bot.loop)
        self.closed = asyncio.Event(loop=self.bot.loop)
        self.channel_id = 543794237515497472
        self.firstlaunch = True

    @commands.Cog.listener()
    async def on_ready(self):
        if self.firstlaunch:
            self.firstlaunch = False
            self.channel: discord.TextChannel = self.bot.get_channel(self.channel_id)
            self.guild: discord.Guild = self.channel.guild

            match = self.pattern1.search(self.channel.name)
            asyncio.ensure_future(self._update_task(), loop=self.bot.loop)
            if match:
                self.count = int(match.group(1))
            else:
                async def _task(channel):
                    while True:
                        try:
                            self.count += len(await channel.history(limit=None).filter(self.not_bot).flatten())
                        except discord.HTTPException:
                            await asyncio.sleep(1)
                        else:
                            return

                await asyncio.gather(*(_task(channel) for channel in self.guild.text_channels))

    async def _update_task(self):
        while not self.closed.is_set():
            await self.channel.edit(name=f'発言数:{self.count}')
            try:
                await asyncio.wait_for(self.closed.wait(), timeout=10)
            except asyncio.TimeoutError:
                await asyncio.wait([self.event.wait(), self.closed.wait()])
                self.event.clear()
            else:
                break

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.not_bot(message):
            self.count += 1
            self.event.set()

    @commands.Cog.listener()
    async def on_close(self):
        await self.channel.edit(name=f'発言数:{self.count}')
        self.closed.set()
