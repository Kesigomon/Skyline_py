import datetime
import re
import asyncio

from discord.ext import commands


class UserSetting:

    def __init__(self):
        pass


class Event:
    __slots__ = ('name', 'description', 'type', 'requirements', 'started_at', 'every_week')
    keys = set(__slots__) - {'started_at'}

    def __init__(self, **kwargs):
        self.name = kwargs['name']
        self.description = kwargs.get('description', '')
        if 'started_at' in kwargs:
            cls = getattr(datetime, kwargs['started_at'].pop('type'))
            self.started_at = cls(**kwargs['started_at'])
        else:
            self.started_at = None
        self.type = kwargs.get('type', '任意参加型')
        self.every_week = kwargs.get('every_week', [])
        self.requirements = kwargs.get('requirements', '')

    def __eq__(self, other):
        return isinstance(other, Event) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def to_dict(self):
        res = {k: getattr(self, k) for k in type(self).keys}
        # 開始時間のクラスを取得 (日のみならdate,時間のみならtime,両方ならdatetime)
        cls = type(self.started_at)
        # クラスの名前を記録
        dic1 = {'type': cls.__name__}
        dic1.update({key: getattr(self.started_at, key) for key in (k[1:] for k in cls.__slots__)})
        res['started_at'] = dic1
        return res


class EventCog(commands.Cog):
    event_keys = ('name', 'description', 'type', 'started_at', 'requirements')
    pattern = re.compile(r'(\d)(?::|：)(.*)')

    def __init__(self, bot):
        self.bot = bot
        self.ready = asyncio.Event(loop=self.bot.loop)
        self.channel_id = 570403341125812230
        self.events = set()

    @property
    def channel(self):
        return self. bot.get_channel(self.channel_id)

    @commands.group()
    async def event(self, ctx):
        pass

    @event.commands()
    async def auto(self, ctx, mes_id: int = None):
        if mes_id is None:
            await ctx.send('メッセージから自動でイベント登録します。\n対象のメッセージIDを入力してください')
            _mes = await self.bot.wait_for(
                'message',
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            try:
                mes_id = int(_mes.content)
            except TypeError:
                await ctx.send('数字以外のものを入力しました。\nもう１度コマンドを打ってやり直してください')
                return
        mes = await self.channel.fetch_message(mes_id)
        kwargs = {self.event_keys[int(match.group(1)) - 1]: match.group(2)
                  for match in self.pattern.finditer(mes.content)}
        if 'name' not in kwargs:
            await ctx.send('名前が設定されていません。')
        else:
            event = Event(**kwargs)
            self.events.add(event)
