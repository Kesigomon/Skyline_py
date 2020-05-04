import asyncio
import datetime
import io
import json
import re
import typing

import discord
from discord.ext import commands

from .general import board_kwargs

listener = commands.Cog.listener


class DiscussionBoard(commands.Cog):
    pattern = re.compile(r'(channel|category)(\d+)')
    filename = 'dis.json'

    def __init__(self, bot: commands.Bot, name=None):
        self.bot = bot
        self.closed = asyncio.Event(loop=bot.loop)
        self.name = name if name is not None else type(self).__name__
        self.guild_id = board_kwargs['guild_id']
        self.channel_ids = board_kwargs['channel_id']
        self.category_ids = board_kwargs['category_id']
        self.counter = {}
        self.user_limiter = {}
        self.creater = {}
        self.ready = asyncio.Event(loop=bot.loop)
        bot.loop.create_task(self.autoclear())

    @property
    def channel_create(self):
        return self.bot.get_channel(self.channel_ids[0])

    @property
    def channel_save(self) -> discord.TextChannel:
        return self.bot.get_channel(self.channel_ids[1])

    @property
    def category_underground(self) -> typing.List[discord.CategoryChannel]:
        return [self.bot.get_channel(i) for i in self.category_ids[1:3]]

    @property
    def category_ruins(self):
        return self.bot.get_channel(self.category_ids[3])

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(self.guild_id)

    @listener()
    async def on_ready(self):
        print('ready!')

    @listener()
    async def on_save(self):
        await self._save()

    @listener()
    async def on_close(self):
        self.closed.set()

    async def cog_before_invoke(self, ctx):
        await self.ready.wait()

    def load(self, stream: io.BytesIO):
        data: dict = json.load(stream)
        self.counter = {self.bot.get_channel(int(k)): v
                        for k, v in data['counter'].items()}
        self.user_limiter = {self.guild.get_member(int(k)): v
                             for k, v in data['user_limiter'].items()}
        self.creater = {self.bot.get_channel(int(k)): self.guild.get_member(v)
                        for k, v in data.get('creater', {}).items()}

    async def _save(self):
        data = {
            'counter': {str(k.id): v for k, v in self.counter.items()
                        if k is not None},
            'user_limiter': {str(k.id): v for k, v in self.user_limiter.items()},
            'creater': {str(k.id): v.id for k, v in self.creater.items()
                        if k is not None and v is not None}
        }
        await self.channel_save.send(
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
        history = self.channel_save.history(after=dt1 - datetime.timedelta(days=1), oldest_first=False)
        async for mes in history.filter(check):
            attach: discord.Attachment
            for attach in mes.attachments:
                if attach.filename == self.filename:
                    # ここからロード処理
                    stream = io.BytesIO()
                    await attach.save(stream)
                    self.load(stream)
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
        while not self.closed.is_set():
            now = datetime.datetime.utcnow()
            try:
                await asyncio.wait_for(self.closed.wait(), (dt1 - now).total_seconds())
            except asyncio.TimeoutError:
                pass
            else:
                break
            channels = (
                # 雑談板
                *(sorted(c.channels, key=lambda c: c.position)[1:] for c in self.category_underground),
                self.category_ruins.channels
            )
            channel: discord.TextChannel
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
                # チャンネル作成者取得の処理
                try:
                    creater = self.creater[channel]
                except KeyError:
                    creater = None
                if creater is not None:
                    mention = creater.mention + "\n"
                else:
                    mention = ''
                # UNDERGROUNDなら7日で遺跡に
                if channel.category in self.category_underground:
                    td1 = datetime.timedelta(days=7)
                    category = self.category_ruins
                    content = mention + '＊このチャンネルは発言がないので、過去ログスレッド倉庫に移動した。'
                # 過去ログスレッドなら14日で消す
                elif channel.category == self.category_ruins:
                    td1 = datetime.timedelta(days=14)
                    content = None
                else:
                    continue
                # ここで条件を満たしていればチャンネルを対象カテゴリに移動
                if datetime.datetime.utcnow() - dt2 >= td1:
                    if content is not None:
                        await channel.edit(category=category, sync_permissions=True)
                        await channel.send(content)
                    else:
                        await channel.delete(reason='過去ログスレッド倉庫にて更新がないチャンネルのため、削除')
                        if creater is not None:
                            try:
                                await creater.send(
                                    f'あなたのチャンネル「{channel.name}」は更新がないため、削除されました。')
                            except discord.Forbidden:
                                pass
            self.user_limiter.clear()
            await self._save()
            dt1 += datetime.timedelta(days=1)

    @listener()
    async def on_message(self, message):
        await self.ready.wait()
        # 自分 or BOT or 指定されたサーバー以外は全て無視
        if message.author == self.bot.user or message.author.bot or message.guild != self.guild:
            return
        channel: discord.TextChannel = message.channel
        # 新規作成用チャンネルならチャンネル作成
        if channel == self.channel_create:
            if self.user_limiter.setdefault(message.author, 0) >= 1:
                await channel.send('＊あなたは今日はもうチャンネルを作れない。')
            else:
                self.user_limiter[message.author] += 1
                overwrites = {
                    self.bot.user:  # bot自身
                        discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none()),
                    message.author:  # 作成者
                        discord.PermissionOverwrite.from_pair(
                            discord.Permissions(66448721), discord.Permissions.none()),
                    self.guild.default_role:  # @everyone
                        discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all()),
                    self.guild.get_role(515467411898761216):  # 制限付きユーザー
                        discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all()),
                    self.guild.get_role(575319592533229598):  # 掲示板カテゴリ閲覧
                        discord.PermissionOverwrite.from_pair(
                            discord.Permissions(37080128), discord.Permissions(2 ** 53 - 37080129)),
                }
                for category in self.category_underground:
                    if len(category.channels) >= 49:
                        continue
                    new_channel = await self.guild.create_text_channel(
                        name=message.content, category=category, overwrites=overwrites)
                    self.creater[new_channel] = message.author
                    await channel.send(f'＊作成完了。\n{new_channel.mention}')
                    await message.author.add_roles(self.guild.get_role(573506143985467392))
                    break
                else:
                    await channel.send('＊カテゴリがいっぱいでこれ以上作成できない。')
        # UNDERGROUND　での発言
        elif channel.category in self.category_underground:
            # カウンターに存在すればその値 + 1
            # 存在しなければ 1
            count = self.counter.setdefault(channel, 0) + 1
            # 10で割り切れる数字のときの処理
            if count % 10 == 0:
                # 10発言ごとに上に行ける
                channels = sorted(channel.category.channels, key=lambda c: c.position)
                index = channels.index(channel)
                # # インデックスチャンネルは動かない
                # if index == 0:
                #     return
                top_channel = channels[1]
                if channel == top_channel:
                    index = self.category_underground.index(channel.category)
                    if index != 0:
                        while True:
                            category2 = self.category_underground[index - 1]  # 一個上のカテゴリ
                            if len(category2.channels) < 49:  # チャンネル数オーバーなら入れ替えを行う
                                break
                            channels2 = category2.text_channels
                            channels2.sort(key=lambda c: c.position)
                            await channels2[-1].edit(category=channel.category, position=channel.position)
                        await channel.edit(category=category2, position=len(channel.guild.text_channels) - 1)
                else:
                    upper_channel = channels[index - 1]
                    # 一つ上のチャンネルと同じポジションを指定することで
                    # チャンネルを上げることができる
                    await channel.edit(
                        position=upper_channel.position
                    )

    @listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        # 雑談板保存版 or 雑談板でなければスルー
        if not channel.category in self.category_underground:
            return
        # 念押しでスリープ
        await asyncio.sleep(2)
        # もし作成チャンネルで作ってなければ消す！
        if channel not in self.creater:
            await channel.delete()

    @commands.command()
    async def reborn(self, ctx, channel: typing.Union[discord.TextChannel, discord.VoiceChannel] = None):
        if channel is None:
            channel = ctx.channel
        if channel.category == self.category_ruins:
            for category in self.category_underground:
                if len(category.channels) >= 49:
                    continue
                await channel.edit(
                    sync_permissions=True,
                    category=category,
                    position=len(channel.guild.text_channels) - 1
                )
                await channel.send('＊いやだ。けされるもんか。')
                break
            else:
                await ctx.send('＊カテゴリがいっぱいで復活できない。')
        else:
            await ctx.send('＊そのチャンネルは復活できない。')

    @commands.command()
    async def board_load(self, ctx: commands.Context):
        if not await self.bot.is_owner(ctx.author):
            await ctx.send("あなたはこのコマンドを使えません")
            return
        await ctx.send("データをロードします。ファイルを送信してください")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        while True:
            mes1: discord.Message = await self.bot.wait_for("message", check=check)
            if mes1.content == "キャンセル":
                await ctx.send("キャンセルしました")
                return
            if not mes1.attachments:
                await ctx.send("データがありません。もう１度送信してください")
                continue
            for att in mes1.attachments:  # type: discord.Attachment
                stream = io.BytesIO()
                await att.save(stream)
                try:
                    self.load(stream)
                except:
                    pass
                else:
                    await ctx.send("ロード完了しました")
                    return
            else:
                await ctx.send("ロードできませんでした。もう１度送信してください")
