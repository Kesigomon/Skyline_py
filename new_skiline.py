import asyncio
import os
import random
import re
import datetime
import functools
import yaml
import inspect
import itertools
from concurrent.futures import ThreadPoolExecutor

import discord
import feedparser
from discord.ext import commands


class MyFormatter(commands.HelpFormatter):
    async def format(self):
        """Handles the actual behaviour involved with formatting.

        To change the behaviour, this method should be overridden.

        Returns
        --------
        list
            A paginated output of the help command.
        """
        self._paginator = commands.Paginator()

        # we need a padding of ~80 or so

        description = self.command.description if not self.is_cog(
        ) else inspect.getdoc(self.command)

        if description:
            # <description> portion
            self._paginator.add_line(description, empty=True)

        if isinstance(self.command, commands.Command):
            # <signature portion>
            signature = self.get_command_signature()
            self._paginator.add_line(signature, empty=True)

            # <long doc> section
            if self.command.help:
                self._paginator.add_line(self.command.help, empty=True)

            # end it here if it's just a regular command
            if not self.has_subcommands():
                self._paginator.close_page()
                return self._paginator.pages

        max_width = self.max_name_size

        def category(tup):
            instance = tup[1].instance
            cog = instance.name if instance is not None else None
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + ':' if cog is not None else '\u200bNo Category:'

        filtered = await self.filter_command_list()
        if self.is_bot():
            _data = sorted(filtered, key=category)
            for category, _commands in itertools.groupby(_data, key=category):
                # there simply is no prettier way of doing this.
                _commands = sorted(_commands)
                if len(_commands) > 0:
                    self._paginator.add_line(category)

                self._add_subcommands_to_page(max_width, _commands)
        else:
            filtered = sorted(filtered)
            if filtered:
                self._paginator.add_line('Commands:')
                self._add_subcommands_to_page(max_width, filtered)

        # add the ending note
        self._paginator.add_line()
        ending_note = self.get_ending_note()
        self._paginator.add_line(ending_note)
        return self._paginator.pages

    def get_ending_note(self):
        command_name = self.context.invoked_with
        return "「{0}{1} (コマンド名)」 または「{0}{1} （カテゴリ名）」とタイプすると詳しい説明が見られます。" \
            .format(self.clean_prefix, command_name)


client = commands.Bot('sk!', formatter=MyFormatter())
firstlaunch = True


class Normal_Command:
    __slots__ = ('client', 'name', 'data', 'categories')

    def __init__(self, client, data, name=None):
        self.client = client
        self.name = name if name is not None else type(self).__name__
        self.data = data

    async def __local_check(self, ctx):
        return ctx.guild is not None

    async def on_ready(self):
        self.categories = [self.client.get_channel(i) for i in self.data['free_categories']]

    # ロールサーチ
    @commands.command()
    async def role_search(self, ctx, *, role: discord.Role):
        embed = discord.Embed(
            title='ロールサーチの結果', description='{0}\nID:{1}'.format(role.mention, role.id))
        await ctx.send(embed=embed)

    # サーバ情報表示
    @commands.command()
    async def server(self, ctx):
        guild = ctx.guild
        description = '''
        サーバーの名前:{0.name}
        サーバーの人数:{0.member_count}
        サーバーのID:{0.id}
        サーバー作成日:{0.created_at}
        サーバーのオーナー:{0.owner.mention}
        サーバーのチャンネル数:{1}
        '''.format(guild, len(guild.channels))
        embed = discord.Embed(title='サーバー情報', description=description)
        embed.set_thumbnail(url=guild.icon_url)
        await ctx.send(embed=embed)
    # 投票機能

    @commands.command()
    async def poll(self, ctx, *args):
        if len(args) == 0:
            pass
        elif len(args) == 1:
            args = (args[0], 'ワイトもそう思います', 'さまよえる亡者はそうは思いません')
        if 1 <= len(args) <= 21:
            answers = args[1:]
            emojis = [chr(0x0001f1e6 + i) for i in range(len(answers))]
            embed = discord.Embed(description='\n'.join(
                e + a for e, a in zip(emojis, answers)))
            m: discord.Message = await ctx.send('**{0}**'.format(args[0]), embed=embed)
            [self.client.loop.create_task(m.add_reaction(e)) for e in emojis]

    @commands.command()
    async def agree(self, ctx):
        normal_user = ctx.guild.get_role(268352600108171274)
        if normal_user not in ctx.author.roles:
            # 送信する文章指定。
            content = """
{0}さんの
アカウントが登録されました！{1}の
{2}個のチャンネルが利用できます！
まずは<#437110659520528395>で自己紹介をしてみてください！
""".format(ctx.author.mention, ctx.guild.name, len(ctx.guild.channels))
            # 左から順に、ユーザーのメンション、サーバーの名前、サーバーのチャンネル数に置き換える。
            # 役職付与
            await ctx.author.add_roles(normal_user)
            # メッセージ送信
            await ctx.send(content)
        else:
            await ctx.send('登録終わってますやんか')

    @commands.command(name='ftcc')
    async def free_text_channel_create(self, ctx, name, category_n=None):
        channel = await self._free_channel_create(ctx, name, category_n, VC=False)
        if channel is not None:
            await ctx.send('作成しました。\n{0}'.format(channel.mention))

    @commands.command(name='fvcc')
    async def free_voice_channel_create(self, ctx, name, category_n=None):
        channel = await self._free_channel_create(ctx, name, category_n, VC=True)
        if channel is not None:
            await ctx.send('作成しました。')

    async def _free_channel_create(self, ctx, name, category_n=None, VC=False):
        if 448842082187214864 in (r.id for r in ctx.author.roles):
            if category_n is None:
                category_n = 1
                while len(self.categories[category_n - 1].channels) >= 50:  # チャンネル数50以上のカテゴリがあれば次のカテゴリへ
                    category_n += 1
            else:
                category_n = int(category_n)
            category = self.categories[category_n - 1]
            guild = category.guild
            overwrites = {
                self.client.user:
                    discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none()),
                ctx.author:
                    discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none()),
                guild.default_role:
                    discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all()),
                guild.get_role(412567728067575809):
                    discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all()),
                guild.get_role(499886891563483147):
                    discord.PermissionOverwrite.from_pair(discord.Permissions(37080128), discord.Permissions(2 ** 53 - 37080129)),
            }
            if VC:
                return await guild.create_voice_channel(name, overwrites=overwrites, category=category)
            else:
                return await guild.create_text_channel(name, overwrites=overwrites, category=category)
        else:
            await ctx.send('あなたはまだチャンネルを作成できません')
            return None


class Bot_Owner_Command:
    __slots__ = ('client', 'name',)

    def __init__(self, client, name=None):
        self.client = client
        self.name = name if name is not None else type(self).__name__

    async def __local_check(self, ctx):
        return await self.client.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def stop(self, ctx):
        await ctx.send('停止しまーす')
        await client.close()

    @commands.command(hidden=True)
    async def say(self, ctx, *, arg):
        await ctx.send(arg)

    @commands.command(hidden=True)
    async def said(self, ctx, *, arg):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(arg)


class Staff_Command:
    __slots__ = ('client', 'limit_role', 'name')

    def __init__(self, client, name=None):
        self.client = client
        self.name = name if name is not None else type(self).__name__

    async def __local_check(self, ctx):
        role_ids = [r.id for r in ctx.author.roles]
        return (any(x in role_ids for x in (429281099672322056, 268352165175623680,)))

    async def on_ready(self):
        self.limit_role: discord.Role = client.get_guild(
            235718949625397251).get_role(412567728067575809)

    @commands.command(brief='制限付きユーザーを付けます')
    async def limit(self, ctx, member: discord.Member):
        Tasks = [self.client.loop.create_task(member.remove_roles(r)) for r in member.roles
                 if r != self.limit_role]
        await asyncio.wait(Tasks)
        await member.add_roles(self.limit_role)


class Owners_Command:
    __slots__ = ('client', 'index_index', 'name', 'id_match')

    def __init__(self, client, name=None):
        self.client: commands.Bot = client
        self.id_match = re.compile(r'ID:(\d*)')
        self.name = name if name is not None else type(self).__name__

    async def __local_check(self, ctx):
        return ctx.guild is not None and (await self.client.is_owner(ctx.author) or ctx.author == ctx.guild.owner)

    async def on_ready(self):
        self.index_index = client.get_channel(500274844253028353)

    # インデックスチャンネルをサーチ。なければNone
    def _create_category_find_index_channel(self, category) -> discord.TextChannel:
        try:
            index_channel: discord.TextChannel = next(
                c for c in category.channels if c.name == 'category-index')
        except StopIteration:
            return None
        else:
            return index_channel

    # インデックスの上のメンションのやつを作る方。
    async def _create_category_index1(self, category):
        index_channel = self._create_category_find_index_channel(category)
        if index_channel is not None:
            async for message in (index_channel.history(reverse=True)
                                  .filter(lambda m: m.author == self.client.user and not m.embeds)):
                break
            channels = sorted((c for c in category.channels if isinstance(
                c, discord.TextChannel) and c != index_channel), key=lambda c: c.position)
            content = '\n'.join(('-' * 10, self.index_index.mention, '-' * 10, '')) \
                + '\n'.join(map(lambda c: c.mention,
                                sorted(channels, key=lambda c: c.position)))
            try:
                await message.edit(content=content)
            except UnboundLocalError:
                await index_channel.send(content=content)
            return 1

    async def _create_category_index2(self, channel):  # インデックスの下のEmbedを作る方。
        index_channel = self._create_category_find_index_channel(
            channel.category)
        if index_channel is not None:
            async for message in (index_channel.history(reverse=True)
                                  .filter(lambda m: m.author == self.client.user and m.embeds)):
                match = self.id_match.search(message.embeds[0].description)
                if match and channel.id == int(match.group(1)):
                    break
            else:
                try:
                    del message
                except UnboundLocalError:
                    pass
            description = channel.topic if channel.topic else 'トピックはないと思います'
            embed = discord.Embed(title=channel.name,
                                  description='ID:{0}'.format(channel.id))
            embed.add_field(name='チャンネルトピック', value=description)
            try:
                await message.edit(embed=embed)
            except UnboundLocalError:
                await index_channel.send(embed=embed)
            return 1

    async def on_guild_channel_create(self, channel):
        if (isinstance(channel, discord.TextChannel)
                and channel.category is not None):
            await self._create_category_index1(channel.category)
            await self._create_category_index2(channel)

    async def on_guild_channel_delete(self, channel):
        if (isinstance(channel, discord.TextChannel)
                and channel.category is not None):
            await self._create_category_index1(channel.category)
            index_channel = self._create_category_find_index_channel(
                channel.category)
            async for message in (index_channel.history(reverse=True)
                                  .filter(lambda m: m.author == self.client.user and m.embeds)):
                match = self.id_match.search(message.embeds[0].description)
                if match and channel.id == int(match.group(1)):
                    await message.delete()
                    break

    async def on_guild_channel_update(self, before, after):
        if isinstance(after, discord.TextChannel) and after.name != 'category-index':
            if before.category is not None and (after.category is None or before.category != after.category):
                await self.on_guild_channel_delete(before)
            if (before.name != after.name
                    or bool(before.topic) is not bool(after.topic)
                    or before.topic != after.topic):
                await self.on_guild_channel_create(after)

    @commands.command(brief='カテゴリインデックスを作ります')
    async def create_category_index(self, ctx, *args):
        async def _create_category_index(category, ctx=None):
            index_channel: discord.TextChannel = self._create_category_find_index_channel(
                category)
            if index_channel is None:
                if ctx is not None:
                    await ctx.send('インデックスチャンネルが見つかりませんでした。')
            else:
                await index_channel.purge(check=lambda m: m.author == client.user and m.embeds)
                await self._create_category_index1(category)
                tasks = [self.client.loop.create_task(self._create_category_index2(channel)) for channel in
                         sorted((c for c in category.channels if isinstance(c, discord.TextChannel) and c != index_channel), key=lambda c:c.position)]
                await asyncio.wait(tasks)
        if not args:
            category = ctx.channel.category
            await _create_category_index(category, ctx)
        elif args[0] == 'all':
            tasks = [self.client.loop.create_task(_create_category_index(category,)) for category in
                     ctx.guild.categories]
            await asyncio.wait(tasks)
        else:
            category = await commands.converter.CategoryChannelConverter().convert(ctx, args[0])
            await _create_category_index(category, ctx)

    @commands.command(brief='役職パネルを再生成します')
    async def panel_regenerate(self, ctx):
        await create_role_panel()
        await ctx.send('再生成終了しました。')

    @commands.command(brief='インデックスインデックスを再生成します')
    async def create_index_index(self, ctx):
        content = str()
        for category in ctx.guild.categories:
            try:
                index_channel: discord.TextChannel = next(
                    c for c in category.channels if c.name == 'category-index')
            except StopIteration:
                pass
            else:
                content += '{0}:{1}\n'.format(category.name,
                                              index_channel.mention)
        else:
            await self.index_index.purge(limit=None, check=lambda m: m.author == self.client.user)
            await self.index_index.send(content)


class DM_Command:
    __slots__ = ('client', 'users', 'name')

    def __init__(self, client, name=None):
        self.client = client
        self.name = name if name is not None else type(self).__name__
        self.users = dict()

    async def __local_check(self, ctx):
        return isinstance(ctx.channel, discord.DMChannel)

    async def on_message(self, message: discord.Message):
        if isinstance(message.channel, discord.DMChannel) and message.author in self.users\
                and not message.content.startswith(client.command_prefix + 'target'):
            await self.users[message.author].send(message.content)

    @commands.command()
    async def target(self, ctx, channel: discord.TextChannel):
        self.users.update({ctx.author: channel})
        await ctx.send('ターゲットを{0}にしました。'.format(channel.mention))


class Joke_Command:
    __slots__ = ('client', 'users', 'name', 'data')

    def __init__(self, client, data, name=None):
        self.client = client
        self.data = data
        self.name = name if name is not None else type(self).__name__

    @commands.command(name='くいな')
    async def kuina(self, ctx):
        await ctx.send(random.choice(self.data['kuina']))

    @commands.command(name='氷河')
    async def hyouga(self, ctx):
        await ctx.send(random.choice(self.data['hyouga']))


class Categor_recover():  # 言わずと知れたカテゴリリカバリ機能
    __slots__ = ('client', 'category_cache')

    def __init__(self, client):
        self.client: discord.Client = client

    async def on_ready(self):
        self.category_cache \
            = {c.id: c.name for c in self.client.get_all_channels()
                if isinstance(c, discord.CategoryChannel)}

    async def on_guild_channel_create(self, channel):
        if isinstance(channel, discord.CategoryChannel):
            self.category_cache[channel.id] = channel.name

    async def on_guild_channel_delete(self, channel):
        if isinstance(channel, discord.CategoryChannel):
            if channel.name not in (c.name for c in channel.guild.categories):
                await channel.guild.create_category(
                    name=channel.name,
                    overwrites=dict(channel.overwrites)
                )

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
            A = True
            while name not in (c.name for c in guild.categories):
                try:
                    new_category = await self.client.wait_for(
                        'guild_channel_create',
                        check=lambda c: c.guild == guild and name == c.name,
                        timeout=1)
                except asyncio.TimeoutError:
                    continue
                else:
                    A = False
                    break
            if A:
                new_category = next(c for c in guild.categories if c.name == name)
            await after.edit(category=new_category)


# 参加メッセージ
@client.event
async def on_member_join(member):
    if 'discord.gg' in member.display_name:
        await member.ban(reason='招待リンクの名前のため、BAN', delete_message_days=1)
    else:
        try:
            zatsudan_forum = next(c for c in member.guild.channels if c.name == '雑談フォーラム')
            new_member = next(c for c in member.guild.channels if c.name == 'ニューメンバー')
        except StopIteration:
            pass
        else:
            join_messages = data['join_messages']
            name = member.display_name
            des1 = random.choice(join_messages).format(
                name, member.guild.me.display_name)
            embed = discord.Embed(
                title='{0}さんが参加しました。'.format(name),
                colour=0x2E2EFE,
                description='```\n{3}\n```\nようこそ{0}さん、よろしくお願いします！\nこのサーバーの現在の人数は{1}です。\n{2}に作られたアカウントです。'
                           .format(name, member.guild.member_count, member.created_at, des1)
            )
            embed.set_thumbnail(url=member.avatar_url)

            try:
                await zatsudan_forum.send(embed=embed)
            except discord.Forbidden:
                pass
            content = data['join_message'].format(member.mention, member.guild.name)
            await new_member.send(content)


# 退出メッセージ
@client.event
async def on_member_remove(member):
    def check(log):
        return (
            log.target.id == member.id
            and abs(now - log.created_at) <= datetime.timedelta(seconds=1)
        )
    now = datetime.datetime.utcnow()
    await asyncio.sleep(0.5)
    audit_logs = await member.guild.audit_logs(action=discord.AuditLogAction.kick).flatten()
    audit_logs.expand(await member.guild.audit_logs(action=discord.AuditLogAction.ban).flatten())
    filtered = list(filter(check, audit_logs))
    if not filtered:
        try:
            zatsudan_forum = next(c for c in member.guild.channels if c.name == '雑談フォーラム')
            new_member = next(c for c in member.guild.channels if c.name == 'ニューメンバー')
        except StopIteration:
            pass
        else:
            name = member.display_name
            embed = discord.Embed(title='{0}さんが退出しました。'.format(
                name), colour=0x2E2EFE, description='{0}さん、ご利用ありがとうございました。\nこのサーバーの現在の人数は{1}人です'.format(name, member.guild.member_count))
            embed.set_thumbnail(url=member.avatar_url)
            try:
                await zatsudan_forum.send(embed=embed)
            except discord.Forbidden:
                pass
            content = """
{0}が退出しました。
ご利用ありがとうございました。
""".format(member)
            await new_member.send(content)

# だいんさん呼ぶ用コマンド
# @client.command()
# @commands.check(check1)
# async def dainspc(ctx):
#     await ctx.send('<@328505715532759043>')


@client.listen('on_ready')
async def on_ready():
    global rolelist, firstlaunch
    if firstlaunch:
        firstlaunch = False
        client.loop.create_task(skyline_update())
    guild = client.get_guild(235718949625397251)
    role_ids = data['roles']
    rolelist = [guild.get_role(int(i)) for i in role_ids]
    [rolelist.remove(None) for i in rolelist[:] if i is None]
    await create_role_panel()
    print(client.user.name, client.user.id, '起動しました。', sep=':')


@client.listen('on_message')
async def on_message(message):
    if message.author == client.user:
        return
    if message.content == 'せやな':
        await message.channel.send('わかる（天下無双）')


@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return
    message = reaction.message
    if message.channel.id == 449185870684356608 and message.author == client.user:
        await message.remove_reaction(reaction, user)
        match = re.search(r'役職パネル\((\d)ページ目\)', message.embeds[0].title)
        if match:
            role = rolelist[ord(reaction.emoji)
                            + int(match.expand(r'\1')) * 20 - 0x1F1FA]
            if role not in user.roles:
                await user.add_roles(role)
                description = '{0}の役職を付与しました。'.format(role.mention)
                await message.channel.send(user.mention, embed=discord.Embed(description=description), delete_after=10)
            else:
                await user.remove_roles(role)
                description = '{0}の役職を解除しました'.format(role.mention)
                await message.channel.send(user.mention, embed=discord.Embed(description=description), delete_after=10)


@client.listen('on_voice_state_update')
async def on_voice_state_update(member, before, after):
    voice_text_pair = data['voice_text']
    if after.channel is not None and (before.channel is None or before.channel != after.channel) and str(after.channel.id) in voice_text_pair:
        text_channel = client.get_channel(
            voice_text_pair[str(after.channel.id)])
        embed = discord.Embed(title='ボイスチャンネル入室通知', description='{0}が、入室しました。'.format(
            member.mention), colour=0x00af00)
        await text_channel.send(embed=embed, delete_after=180)
    if before.channel is not None and (after.channel is None or before.channel != after.channel) and str(before.channel.id) in voice_text_pair:
        text_channel = client.get_channel(
            voice_text_pair[str(before.channel.id)])
        embed = discord.Embed(title='ボイスチャンネル退出通知', description='{0}が、退出しました。'.format(
            member.mention), colour=0xaf0000)
        await text_channel.send(embed=embed, delete_after=180)


async def create_role_panel():
    channel = client.get_channel(449185870684356608)
    await channel.purge(limit=None, check=lambda m: m.embeds and m.author == client.user and '役職パネル' in m.embeds[0].title)
    for x in range(len(rolelist) // 20 + 1):
        roles = rolelist[x * 20:(x + 1) * 20]
        content = '\n'.join('{0}:{1}'.format(
            chr(i + 0x0001f1e6), r.mention) for i, r in enumerate(roles))
        embed = discord.Embed(
            title='役職パネル({0}ページ目)'.format(x + 1), description=content)
        m = await channel.send(embed=embed)
        [client.loop.create_task(m.add_reaction(chr(0x0001f1e6 + i)))
         for i in range(len(roles))]


async def skyline_update():
    channel = client.get_channel(498275174123307028)
    webhooks = await channel.webhooks()
    webhook: discord.Webhook = webhooks[0]
    while not client.is_closed():
        async for message in channel.history().filter(lambda m: m.author.id == 498275277269499904):
            break
        with ThreadPoolExecutor(max_workers=1) as t:
            feed = await client.loop.run_in_executor(t, functools.partial(feedparser.parse, 'https://github.com/Kesigomon/Skyline_py/commits/master.atom'))
        entry = feed.entries[0]
        if entry.link != message.embeds[0].url:
            embed = discord.Embed(title=entry.link.replace('https://github.com/Kesigomon/Skyline_py/commit/', ''),
                                  description=entry.title, timestamp=datetime.datetime(*entry.updated_parsed[0:7]), url=entry.link)
            embed.set_author(name=entry.author, url=entry.author_detail.href,
                             icon_url=entry.media_thumbnail[0]['url'])
            await webhook.send(embed=embed)
        await asyncio.sleep(60)


with open(os.path.dirname(__file__) + os.sep + 'config.yaml', encoding='utf-8') as f:
    data = yaml.load(f)
client.add_cog(Normal_Command(client, data, '普通のコマンド'))
client.add_cog(Bot_Owner_Command(client, 'BOTオーナー用コマンド'))
client.add_cog(Owners_Command(client, 'オーナーズ用コマンド'))
client.add_cog(Staff_Command(client, 'スタッフ用コマンド'))
client.add_cog(DM_Command(client, 'DM用コマンド'))
client.add_cog(Joke_Command(client, data, 'ネタコマンド'))
client.add_cog(Categor_recover(client))
if __name__ == '__main__':
    token = ''
    client.run(token)
