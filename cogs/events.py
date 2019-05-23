import asyncio
import datetime
import re

import aiohttp
import discord
import feedparser
from discord.ext import commands

from .general import ZATSUDAN_FORUM_ID, join_message, voice_text


class Events(commands.Cog):
    __slots__ = ('client', 'name', 'DJ', 'beginner_chat',
                 'Normal_User', 'OverLevel10',
                 'webhook_site', 'webhook_app', 'webhook_runner',
                 'saves', 'new_member', 'tasks', 'mention_counter')

    pattern1 = re.compile(r'discord(?:\.gg|app\.com/invite)/([a-zA-Z0-9]+)')
    pattern2 = re.compile(r'(@everyone|@here|<@.??\d+?>)')

    def __init__(self, client, name=None):
        self.client: commands.Bot = client
        self.name = name if name is not None else type(self).__name__
        self.tasks = [
            self.client.loop.create_task(coro)
            for coro in (self.task_bump(), self.task_skyline_update())
        ]
        self.mention_counter = {}

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild: discord.Guild = self.client.get_guild(ZATSUDAN_FORUM_ID)
        self.DJ = self.guild.get_role(515467441959337984)
        # self.beginner_chat = client.get_channel(524540064995213312)
        self.Normal_User = self.guild.get_role(515467427459629056)
        self.OverLevel10 = self.guild.get_role(515467423101747200)
        self.new_member = self.guild.get_channel(515467586679603202)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild == self.guild:
            if self.pattern1.search(member.display_name):
                await member.ban(reason='招待リンクの名前のため、BAN', delete_message_days=1)
            elif any(i in member.name for i in ('rennsura', 'レンスラ', 'れんすら')):
                await member.ban(reason='レンスラのため、BAN', delete_message_days=1)
            else:
                content = join_message.format(member.mention, member.guild.name)
                await self.new_member.send(content)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        def check(log):
            return (
                log.target.id == member.id
                and abs(now - log.created_at) <= datetime.timedelta(seconds=1)
            )
        now = datetime.datetime.utcnow()
        await asyncio.sleep(0.5)
        audit_logs = await member.guild.audit_logs(action=discord.AuditLogAction.kick).flatten()
        audit_logs.extend(await member.guild.audit_logs(action=discord.AuditLogAction.ban).flatten())
        filtered = list(filter(check, audit_logs))
        if not filtered:
            try:
                await self.client.wait_until_ready()
                zatsudan_forum = member.guild.get_channel(515467559051591681)
            except (StopIteration, IndexError):
                pass
            else:
                name = member.display_name
                embed = discord.Embed(
                    title='{0}さんが退出しました。'.format(name),
                    colour=0x2E2EFE,
                    description='{0}さん、ご利用ありがとうございました。\nこのサーバーの現在の人数は{1}人です'
                    .format(name, member.guild.member_count)
                )
                embed.set_thumbnail(url=member.avatar_url)
                await zatsudan_forum.send(embed=embed)
                content = (
                    '{0}が退出しました。'
                    'ご利用ありがとうございました。'
                ).format(member)
                await self.new_member.send(content)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        voice_text_pair = voice_text
        if (
            after.channel is not None
            and (before.channel is None or before.channel != after.channel)
        ):
            try:
                text_channel = self.client.get_channel(
                    voice_text_pair[after.channel.id])
            except KeyError:
                pass
            else:
                embed = discord.Embed(
                    title='ボイスチャンネル入室通知',
                    description='{0}が、入室しました。'.format(member.mention),
                    colour=0x00af00
                )
                await text_channel.send(embed=embed, delete_after=180)
                if after.channel.id == 515467651691315220:  # 音楽鑑賞VCの場合
                    await member.add_roles(self.DJ)  # DJ役職を付与
        if (
            before.channel is not None
            and (after.channel is None or before.channel != after.channel)
        ):
            try:
                text_channel = self.client.get_channel(
                    voice_text_pair[before.channel.id])
            except KeyError:
                pass
            else:
                embed = discord.Embed(
                    title='ボイスチャンネル退出通知',
                    description='{0}が、退出しました。'.format(member.mention),
                    colour=0xaf0000
                )
                await text_channel.send(embed=embed, delete_after=180)
                if before.channel.id == 515467651691315220:  # 音楽鑑賞VCの場合
                    await member.remove_roles(self.DJ)  # DJ役職を解除

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # メンションカウンターに登録されていないならデフォルト値を設定しておく
        self.mention_counter.setdefault(message.author, 0)
        # メンションのある発言なら、マッチする
        if self.pattern2.search(message.content):
            self.mention_counter[message.author] += 1
            if self.mention_counter[message.author] >= 5:
                ctx: commands.Context = await self.client.get_context(message)
                await ctx.invoke(self.client.get_command('limit'), message.author)
        # メンションのない発言ならカウンターリセット
        else:
            self.mention_counter[message.author] = 0

    @commands.Cog.listener()
    async def on_close(self):
        [t.cancel() for t in self.tasks]

    async def task_skyline_update(self):
        await self.client.wait_until_ready()
        channel = self.client.get_channel(515468115535200256)
        webhooks = await channel.webhooks()
        webhook: discord.Webhook = webhooks[0]
        url = 'https://github.com/Kesigomon/Skyline_py/commits/master.atom'

        def check(m):
            return m.author.id == webhook.id and m.embeds
        async with aiohttp.ClientSession() as session:
            while not self.client.is_closed():
                try:
                    message = await channel.history().filter(check).next()
                except discord.NoMoreItems:
                    message = None
                async with session.get(url) as resp:
                    feed = feedparser.parse(await resp.text())
                for entry in feed.entries:
                    commit_id = entry.link.replace('https://github.com/Kesigomon/Skyline_py/commit/', '')
                    if (message is not None and
                            message.embeds[0].title == commit_id):
                        break
                    embed = discord.Embed(
                        title=commit_id,
                        description=entry.title,
                        timestamp=datetime.datetime(*entry.updated_parsed[0:7]),
                        url=entry.link
                    )
                    embed.set_author(name=entry.author, url=entry.author_detail.href,
                                    icon_url=entry.media_thumbnail[0]['url'])
                    await webhook.send(embed=embed)
                try:
                    await asyncio.wait_for(self.client._closed.wait(), timeout=60)
                except asyncio.TimeoutError:
                    pass

    async def task_bump(self):
        disboard_bot_id = 302050872383242240
        Interval = datetime.timedelta(hours=2)
        mention = '<@&515467430018154507>'

        def check1(m):
            return m.author == disboard_bot and ':thumbsup:' in m.embeds[0].description
        await self.client.wait_until_ready()
        disboard_bot = self.client.get_user(disboard_bot_id)
        channel: discord.TextChannel = self.client.get_channel(515467856239132672)
        while not self.client.is_closed():
            try:
                mes = await channel.history().filter(check1).next()
            except discord.NoMoreItems:
                mes = None
            if mes is not None:
                TD1 = datetime.datetime.utcnow() - mes.created_at
                if TD1 >= Interval:
                    await channel.send(
                        mention
                        + '既に2時間以上経っていますよ\n'
                        + 'SKYLINEは!disboard bumpするといいと思います'
                    )
                else:
                    try:
                        # クライアントクローズか2時間経過するのを待つ
                        await asyncio.wait_for(
                            self.client._closed.wait(),
                            (Interval - TD1).total_seconds()
                        )
                    except asyncio.TimeoutError:
                        # 2時間経過
                        await channel.send(
                            mention
                            + '2時間経ちましたよ\n'
                            + 'SKYLINEは!disboard bumpするといいと思います'
                        )
                    else:
                        # クライアントクローズ
                        pass
            else:
                await channel.send(
                    mention
                    + 'このサーバーで一度もコマンドを実行していませんね\n'
                    + 'SKYLINEは!disboard bumpするといいと思います'
                )
            # メッセージかクライアントクローズ待ち
            await asyncio.wait(
                [self.client.wait_for(event='message', check=check1),
                 self.client._closed.wait()],
                return_when='FIRST_COMPLETED'
            )
