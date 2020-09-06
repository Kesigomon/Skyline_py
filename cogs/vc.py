import io
import json

import discord
from discord.ext import commands

from .general import (
    voice_text,
    save_channel
)


class VC(commands.Cog):
    filename = "vc.json"

    def __init__(self, bot, name=None):
        self.bot: commands.Bot = bot
        self.name = name if name is not None else type(self).__name__
        self.cache = {}  # 元々の名前保存用
        self.save_channel = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.save_channel: discord.TextChannel = self.bot.get_channel(save_channel)
        await self.load()

    async def load(self):
        def check(m: discord.Message):
            return (
                    m.author == self.bot.user
                    and m.attachments
                    and m.attachments[0].filename == self.filename
            )

        stream = io.BytesIO()
        async for message in self.save_channel.history(limit=None).filter(check):
            await message.attachments[0].save(stream)
            break
        else:
            return
        data: dict = json.loads(stream.read().decode('UTF-8'))
        self.cache = {
            self.bot.get_channel(int(key)): value
            for key, value in data.items()
        }

    @commands.command()
    async def vc(self, ctx: commands.Context, *, name):
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            channel = None
        if channel is None:
            await ctx.send("VCに参加しないとこのコマンドは使えません")
            return
        try:
            text_channel = self.bot.get_channel(voice_text[channel.id])
        except KeyError:
            await ctx.send("このチャンネルは名前変更に対応してません")
            return
        # 変更前のチャンネルを保存しておく、2回目はしない
        if channel not in self.cache:
            self.cache[channel] = channel.name
        await channel.edit(name=name)
        await text_channel.edit(name=f"{name}txt")
        await ctx.send("変更しました")

    @commands.Cog.listener()
    async def on_save(self):
        data = {str(channel.id): name for channel, name in self.cache.items()}
        stream = io.StringIO(json.dumps(data, indent=4))
        file = discord.File(stream, filename=self.filename)
        await self.save_channel.send(file=file)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if (
            after.channel is not None
            and (before.channel is None or before.channel != after.channel)
        ):
            try:
                text_channel = self.bot.get_channel(voice_text[after.channel.id])
            except KeyError:
                return
            embed = discord.Embed(
                title='ボイスチャンネル入室通知',
                description='{0}が、入室しました。'.format(member.mention),
                colour=0x00af00
            )
            # await text_channel.send(embed=embed, delete_after=180)
        if (
            before.channel is not None
            and (after.channel is None or before.channel != after.channel)
        ):
            try:
                text_channel = self.bot.get_channel(voice_text[before.channel.id])
            except KeyError:
                return
            embed = discord.Embed(
                title='ボイスチャンネル退出通知',
                description='{0}が、退出しました。'.format(member.mention),
                colour=0xaf0000
            )
            # await text_channel.send(embed=embed, delete_after=180)
            if not before.channel.members:
                await text_channel.send("参加者が0人となったので、元々の名前に変更します")
                await before.channel.edit(name=self.cache[before.channel])
                await text_channel.edit(name=self.cache[before.channel] + "txt")
                del self.cache[before.channel]