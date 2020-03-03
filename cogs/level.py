import asyncio
import datetime
import io
import itertools
import json
import random
import re
import textwrap
import traceback

import discord
from discord.ext import commands

from .general import is_staff, spam


class Level_counter:
    __slots__ = ('exp', 'count', 'limit', 'rank', 'bot_count')

    def __init__(self, **kwargs):
        """
        Level_counter
        レベルカウンターです。
        exp:経験値
        count:発言回数（Botコマンド以外）
        bot_count：botのコマンド（と思われる）の使用回数
        """
        self.exp = kwargs.get('exp', 0)
        self.count = kwargs.get('count', 0)
        self.limit = False
        self.rank = kwargs.get('rank', 0)
        self.bot_count = kwargs.get('bot_count', 0)

    @staticmethod
    def func1(n):
        return 5 * n * (2 * n ** 2 + 33 * n + 151) / 6

    @property
    def next_exp(self):
        return self.func1(self.level + 1) - self.exp

    @property
    def max_exp(self):
        return self.func1(self.level + 1) - self.func1(self.level)

    @property
    def level(self):
        return next(
            n for n in itertools.count()
            if self.func1(n) <= self.exp < self.func1(n + 1)
        )

    def unlimit(self):
        self.limit = False

    async def message(self):
        loop = asyncio.get_running_loop()
        self.count += 1
        if not self.limit:
            self.limit = True
            loop.call_later(60, self.unlimit)
            self.exp += random.randint(20, 40)
        else:
            self.exp += 1


class Level(commands.Cog):  # レベルシステム（仮運用）
    __slots__ = ('client', 'save_channel', 'name', 'data', 'firstlaunch', 'ranking_limiter',
                 'cache_messages', 'ranking_channel', 'role_dict', 'save_message', 'guild', 'ready')
    filename = 'Level.json'
    pattern1 = re.compile(r'^\w*?(!|::)', re.ASCII)

    def __init__(self, client, name=None, ):
        self.client: commands.Bot = client
        self.name = name if name is not None else type(self).__name__
        self.data = {}
        self.firstlaunch = True
        self.ranking_limiter = False
        self.cache_messages = []
        self.ready = asyncio.Event(loop=self.client.loop)
        self.closed = asyncio.Event(loop=self.client.loop)

    @commands.Cog.listener()
    async def on_ready(self):
        loop = self.client.loop
        self.save_channel: discord.TextChannel \
            = self.client.get_channel(531377173869625345)
        self.ranking_channel: discord.TextChannel \
            = self.client.get_channel(533636280593154048)
        self.save_message: discord.Message = \
            await self.client.get_channel(561912707310157839).fetch_message(561913325538246670)
        guild: discord.Guild = self.ranking_channel.guild
        self.guild = guild
        self.role_dict = {
            i[0]: guild.get_role(i[1])
            for i in (
                (60, 668960966972801037),
                (50, 532121179457060876),
                (40, 532120974942797835),
                (30, 532119101309452289),
                (20, 532118646877585409),
                (10, 532118282950672384),
                (5, 532118079958679552),
            )
        }

        def func3(m: discord.Message):
            return (
                    m.author == self.client.user
                    and m.embeds
            )

        self.cache_messages = await self.ranking_channel.history(limit=None) \
            .filter(func3).flatten()
        self.cache_messages.sort(key=lambda m: m.created_at)
        if self.firstlaunch:
            self.firstlaunch = False

            def func1(m: discord.Message):
                return (
                        m.author == self.client.user
                        and m.attachments
                        and m.attachments[0].filename == self.filename
                )

            data = io.BytesIO()
            async for message in self.save_channel.history(limit=None).filter(func1):
                await message.attachments[0].save(data)
                break
            sub_data: dict = json.loads(data.read().decode('UTF-8'))
            self.data = {
                key: Level_counter(**value)
                for key, value in sub_data.items()
            }
            loop.create_task(self.autosave())
            self.ready.set()

    def get_data(self, member: discord.Member) -> Level_counter:
        return self.data.setdefault(str(member.id), Level_counter())

    @commands.Cog.listener()
    async def on_message(self, message):
        if (
            message.author.bot
            or self.client.user == message.author
        ):
            return
        await self.ready.wait()
        member = message.author
        sub_data: Level_counter = self.get_data(member)
        if not self.pattern1.search(message.content):  # BOTコマンドでなければNoneが返る
            if message.channel.id not in spam:  # スパムチャンネル以外で
                old_level = sub_data.level
                await sub_data.message()
                new_level = sub_data.level
                self.client.loop.create_task(self.update_ranking())
                if new_level != old_level:
                    content = (
                        '＊{0}のLVが{1}になった。\n'
                        '＊次のLVまで{2}EXP。'
                    ).format(member.mention, new_level, sub_data.max_exp)
                    await message.channel.send(content)
                    await self.update_level(member, new_level)
            else:  # スパムちゃんねるなら以下
                sub_data.count += 1
        else:  # BOTコマンドならこちら
            sub_data.bot_count += 1

    @commands.command()
    async def rank(self, ctx, content_index: int = 0, member: discord.Member = None):
        if member is None:
            member = ctx.author
        content_list = (
            '＊次のLVまで{1.next_exp}EXP。',
            '＊カウント開始してから{1.count}発言。',
            '＊このサーバーでは{1.rank}位のようだ。',
            '＊BOTのコマンド（と思われるもの）を{1.bot_count}回使ったようだ。',
            '＊引数に数字を指定することで、メッセージを固定できる。'
        )
        no_message = '＊その番号のメッセージは用意されていない。'
        if content_index == 0:
            content2 = random.choice(content_list)
        elif content_index >= 1:
            try:
                content2 = content_list[content_index - 1]
            except IndexError:
                content2 = no_message
        else:
            content2 = no_message
        data: Level_counter = self.get_data(member)
        content = (
                '＊　{0}　ー　LV　{1.level}　EXP　{1.exp}\n'
                + content2
        ).format(member.display_name, data)
        await ctx.send(content)
        await self.update_level(member, data.level)

    async def _save(self, member, wait=False):
        # self.client.loopと書くとめっちゃ長い
        loop = self.client.loop
        # 全セーブイベント実行開始
        events_task = [loop.create_task(f()) for f in
                       self.client.extra_events.get('on_save', [])]
        data_dict = {
            key: {k1: getattr(value, k1) for k1 in ('exp', 'count', 'rank', 'bot_count',)}
            for key, value in self.data.items()
        }
        stream = io.StringIO(json.dumps(data_dict, indent=4))
        file = discord.File(stream, filename=self.filename)
        await self.save_channel.send(file=file)
        if events_task:
            await asyncio.wait(events_task)
        task = loop.create_task(self._change_message(member, self.save_message))
        if wait:
            await task

    async def _change_message(self, member, mes):
        if mes.id == self.save_message.id:
            guildname = self.guild.name
        else:
            guildname = '偽物のセーブデータ'
        delta = datetime.datetime.utcnow() - member.joined_at
        q, r = divmod(delta, datetime.timedelta(seconds=60))
        nick = member.display_name[:6]
        nick += ' ' * 2 * (6 - len(nick))
        title = textwrap.dedent(
            f"""
            {nick}          LV{self.get_data(member).level}       {q}:{r.seconds}
            {guildname}

            """
        )
        embed1 = discord.Embed(title=title + '  セーブ完了', color=0xffff00)
        embed2 = discord.Embed(title=title + ':hearts: セーブ            戻る', color=0xffffff)
        await mes.edit(embed=embed1)
        await asyncio.sleep(2)
        await mes.edit(embed=embed2)

    async def autosave(self):
        member = self.guild.me
        while not self.closed.is_set():
            now = datetime.datetime.now()
            nexttime = now.replace(minute=58, second=0, microsecond=0)
            if now.minute == 58:
                nexttime += datetime.timedelta(hours=1)
            second = (nexttime - now).total_seconds()
            content = (
                '現在の時刻は{0}、次の自動SAVEは{1}'
                '自動セーブまであと{2}'
            ).format(now, nexttime, second)
            self.client.loop.create_task(self.save_channel.send(content=content))
            try:
                await asyncio.wait_for(self.closed.wait(), timeout=second)
            except asyncio.TimeoutError:
                pass
            else:
                continue
            await self._save(member)

    @commands.command()
    async def adjust_exp(self, ctx, member: discord.Member, delta_exp: int):
        role_ids = [r.id for r in ctx.author.roles]
        if (
                any(x in role_ids for x in
                    (515467407381364738, 515467410174902272, 515467421323100160)
                    )
                or await self.client.is_owner(ctx.author)
        ):
            data: Level_counter = self.get_data(member)
            old_level = data.level
            data.exp += delta_exp
            new_level = data.level
            description = (
                '＊{0.mention}のEXPを{2}\n'
                '＊現在のEXPは{1.exp}だ。\n'
            ).format(member, data, (str(delta_exp) + '上げた' if delta_exp >= 0 else str(-delta_exp) + '下げた'))
            if old_level > new_level:
                description += '＊LVが{0}下がり、{1}になった。'.format(old_level - new_level, new_level)
            elif old_level < new_level:
                description += '＊LVが{0}上がり、{1}になった。'.format(new_level - old_level, new_level)
            else:
                description += '＊LVは{0}のままのようだ。'.format(new_level)
            embed = discord.Embed(description=description)
            await ctx.send(embed=embed)
        else:
            await ctx.send('＊そのコマンドを使うだけのケツイが足りないようだ。')

    @commands.command()
    async def save_level(self, ctx):
        if await self.client.is_owner(ctx.author):
            await ctx.send('＊（コマンドを打っていたら、ケツイがみなぎった。）')
            try:
                await self._save(ctx.author)
            except Exception:
                await ctx.send('＊セーブに失敗したようだ。（ログを確認してね）')
                traceback.print_exc()
            else:
                await ctx.send('セーブしました。')
        else:
            await ctx.send('＊ケツイがまだ足りないようだ。')

    async def update_level(self, member, level):
        for key, value in self.role_dict.items():
            if level >= key:
                await member.add_roles(value)

    async def update_ranking(self):
        await self.ready.wait()
        if not self.ranking_limiter:
            self.ranking_limiter = True
            try:
                guild = self.ranking_channel.guild
                subdata = [(key, value) for key, value in self.data.items()
                           if guild.get_member(int(key)) is not None]
                subdata.sort(key=lambda i: i[1].exp)
                [setattr(d[1], 'rank', i) for i, d in enumerate(subdata, 1)]
                for page in itertools.count():
                    sub_subdata = subdata[page * 25:(page + 1) * 25]
                    # データがもうない or BOT停止で終了
                    if not sub_subdata or self.closed.is_set():
                        break
                    embed = discord.Embed(title='ランキング')
                    [
                        embed.add_field(
                            name='{0}位 (LV{1.level} {1.exp}EXP)'.format(count, value),
                            value='<@{0}>'.format(key),
                            inline=False
                        )
                        for count, (key, value) in enumerate(sub_subdata, page * 25 + 1)
                    ]
                    try:
                        message = self.cache_messages[page]
                    except IndexError:
                        message = await self.ranking_channel.send(embed=embed)
                        self.cache_messages.append(message)
                    else:
                        await message.edit(embed=embed)
                if not self.closed.is_set():
                    for message in self.cache_messages[page:]:
                        await message.delete()
                    del self.cache_messages[page:]
            finally:
                try:
                    await asyncio.wait_for(self.closed.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.ranking_limiter = False

    @commands.Cog.listener()
    async def on_close(self):
        self.closed.set()
        await self._save(self.guild.me, wait=True)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.client.user.id:
            return
        if self.save_message.channel.id == payload.channel_id:
            save = self.save_message.id == payload.message_id
            if not save:
                mes = await self.save_message.channel.fetch_message(payload.message_id)
            else:
                mes = self.save_message
            if mes is None or mes.author != self.client.user:
                return
            user = self.guild.get_member(payload.user_id)
            await mes.remove_reaction(payload.emoji, user)
            if save and await is_staff(user):
                await self._save(user)
            if not save or await is_staff(user):
                await self._change_message(user, mes)

