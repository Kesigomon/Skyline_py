import datetime
import re
import asyncio
import json
import io

import discord
from discord.ext import commands
from .general import board_kwargs

listener = commands.Cog.listener


class DiscussionBoard(commands.Cog):
    pattern = re.compile(r'(channel|category)(\d+)')
    filename = 'dis.json'

    def __init__(self, bot: commands.Bot, name=None):
        self.bot = bot
        self.name = name if name is not None else type(self).__name__
        self.guild_id = board_kwargs['guild_id']
        self.channel_ids = board_kwargs['channel_id']
        self.category_ids = board_kwargs['category_id']
        self.counter = {}
        self.user_limiter = {}
        self.ready = asyncio.Event(loop=bot.loop)
        t = bot.loop.create_task(self.autoclear())

    def __getattr__(self, item):
        match = self.pattern.match(item)
        if match and not item.endswith('_ids'):
            return self.bot.get_channel(
                getattr(self, f'{match.group(1)}_ids')[int(match.group(2)) - 1]
            )
        else:
            raise AttributeError

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(self.guild_id)

    @listener()
    async def on_ready(self):
        print('ready!')

    @listener()
    async def on_save(self):
        await self._save()

    async def _save(self):
        data = {
            'counter': {str(k.id): v for k, v in self.counter.items()
                        if k is not None},
            'user_limiter': {str(k.id): v for k, v in self.user_limiter.items()}
        }
        await self.channel3.send(
            file=discord.File(
                io.StringIO(json.dumps(data, indent=4)),
                filename=self.filename
            )
        )

    async def autoclear(self):
        # 起動完了まで待機
        await self.bot.wait_until_ready()
        # UTCで現在の時刻を取得する（Discordの時刻関連は全部UTCになる）
        now = datetime.datetime.utcnow()
        # 次回再起動タイミング
        dt1 = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if dt1 < now:
            dt1 += datetime.timedelta(days=1)

        def check(m: discord.Message):
            return m.author == self.bot.user

        # 次回再起動前２４時間以内に作られたセーブ
        mes: discord.Message
        async for mes in self.channel3.history(after=dt1 - datetime.timedelta(days=1)).filter(check):
            attach: discord.Attachment
            for attach in mes.attachments:
                if attach.filename == self.filename:
                    # ここからロード処理
                    stream = io.BytesIO()
                    await attach.save(stream)
                    data = json.load(stream)
                    self.counter = {self.bot.get_channel(int(k)): v
                                    for k, v in data['counter'].items()}
                    self.user_limiter = {self.guild.get_member(int(k)): v
                                         for k, v in data['user_limiter'].items()}
                    break
            else:
                # 添付に該当ファイルがなければ次のメッセージに
                continue
            # ロードした場合ここに来る
            break
        else:
            # もし、ロードできなければすぐにキャッシュクリア＆チャンネル処理
            dt1 -= datetime.timedelta(days=1)
        self.ready.set()
        while not self.bot.is_closed():
            now = datetime.datetime.utcnow()
            await asyncio.sleep((dt1 - now).total_seconds())
            channels = (
                # self.category2.text_channels,
                self.category3.text_channels,
            )
            for channel in (x1 for x2 in channels for x1 in x2):
                try:
                    # メッセージがあればそれを
                    mes: discord.Message = await channel.history().next()
                except discord.NoMoreItems:
                    # なければ、作成時間とする
                    dt2 = channel.created_at
                else:
                    # 最後のメッセージの時間
                    dt2 = mes.created_at
                # １週間以上更新がないと遺跡に封印される。
                if datetime.datetime.utcnow() - dt2 >= datetime.timedelta(days=1):
                    await channel.edit(category=self.category4)
            self.user_limiter.clear()
            await self._save()
            dt1 += datetime.timedelta(days=1)

    @listener()
    async def on_message(self, message):
        await self.ready.wait()
        # 自分 or BOT or 指定されたサーバー以外は全て無視
        if message.author == self.bot.user or message.author.bot or message.guild != self.guild:
            return
        channel = message.channel
        # 新規作成用チャンネルならチャンネル作成
        if channel in (
                self.channel1,
               # self.channel2
        ):
            overwrites = {
                self.bot.user:
                    discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none()),
                message.author:
                    discord.PermissionOverwrite.from_pair(discord.Permissions(66448721), discord.Permissions.none()),
                self.guild.default_role:
                    discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all()),
                self.guild.get_role(515467411898761216):
                    discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all()),
                self.guild.get_role(515467425429585941):
                    discord.PermissionOverwrite.from_pair(
                        discord.Permissions(37080128), discord.Permissions(2 ** 53 - 37080129)),
            }
            # category = self.category3 if channel == self.channel1 else self.category1
            category = self.category3
            new_channel = await self.guild.create_text_channel(name=message.content, category=category)
            await channel.send(f'作成しました。\n{new_channel.mention}')
        # 地上 or UNDERGROUND　での発言
        elif channel.category in (
                # self.category2,
                self.category3,):
            # カウンターに存在すればその値 + 1
            # 存在しなければ 1
            count = self.counter.setdefault(channel, 0) + 1
            # 10で割り切れる数字のときの処理
            if count % 10 == 0:
                # 7つのソウル（人間単位）の力で地上へ出れる！
                # 10発言＝1人の人間のソウルって感じ？
                # if count == 70:
                #     await channel.edit(category=self.category2)
                # # 10発言ごとに上に行ける
                # else:
                await channel.edit(position=max(0, channel.position - 1))
            self.counter[message.channel] = count
