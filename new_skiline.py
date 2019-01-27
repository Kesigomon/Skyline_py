import asyncio
import os
import random
import re
import datetime
import functools
import yaml
import inspect
import itertools
import io
import json
from concurrent.futures import ThreadPoolExecutor

import aiohttp
import aiohttp.web
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
            return cog + ':' if cog is not None else '\u200bカテゴリなし:'

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


async def zatsudan_forum_check(ctx):
    return ctx.guild is not None and ctx.guild.id == 515467348581416970


async def member_join(member: discord.Member):
    try:
        zatsudan_forum = member.guild.get_channel(515467559051591681)
    except IndexError:
        pass
    else:
        join_messages = data['join_messages']
        name = member.display_name
        des1 = random.choice(join_messages)\
            .format(name, member.guild.me.display_name)
        embed = discord.Embed(
            title='{0}さんが参加しました。'.format(name),
            colour=0x2E2EFE,
            description=(
                '```\n{3}\n```\n'
                'ようこそ{0}さん、よろしくお願いします！\n'
                'このサーバーの現在の人数は{1}です。\n'
                '{2}に作られたアカウントです。'
            ).format(name, member.guild.member_count, member.created_at, des1)
        )
        embed.set_thumbnail(url=member.avatar_url)

        await zatsudan_forum.send(embed=embed)


class Normal_Command:
    __slots__ = ('client', 'name', 'data', 'categories')

    def __init__(self, client, data, name=None):
        self.client: commands.Bot = client
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

    @commands.command()
    async def member(self, ctx, member=None):
        if member is None:
            member = ctx.author
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, member)
            except commands.CommandError:
                try:
                    member = await commands.UserConverter().convert(ctx, member)
                except commands.CommandError:
                    await ctx.send('ユーザーが見つかりませんでした')
                    return
        icon_url = member.avatar_url_as(format='png', size=1024)
        embed = discord.Embed(description=member.mention)
        embed.set_author(name=str(member), icon_url=icon_url)
        embed.set_image(url=icon_url)
        args = {
            'ID': member.id,
            'アカウントが作られた日': member.created_at,
        }
        if isinstance(member, discord.Member):
            args.update({'このサーバーに入った日': member.joined_at})
        [embed.add_field(name=key, value=value)
         for key, value in args.items()]
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

    @commands.command(check=[zatsudan_forum_check])
    async def agree(self, ctx):
        roles = [ctx.guild.get_role(i) for i in (515467427459629056, 515467425429585941)]
        if roles[0] not in ctx.author.roles:
            # 送信する文章指定。
            content = (
                '{0}さんの\n'
                'アカウントが登録されました！{1}の\n'
                '{2}個のチャンネルが利用できます！\n'
                'まずは<#515467585152876544>で自己紹介をしてみてください！\n'
                '旧サーバーから移動してきた方は、<#531284969025437696>を参照してください。'
            ).format(ctx.author.mention, ctx.guild.name, len(ctx.guild.channels))
            # 左から順に、ユーザーのメンション、サーバーの名前、サーバーのチャンネル数に置き換える。
            # 役職付与
            await ctx.author.add_roles(*roles)
            # メッセージ送信
            await ctx.send(content)
            member = ctx.author
            await member_join(member)
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
        if 515467423101747200 in (r.id for r in ctx.author.roles) or True:  # 一時的に全員使用可能(or True)
            if category_n is None:
                category_n = 1
                while len(self.categories[category_n].channels) >= 50:  # チャンネル数50以上のカテゴリがあれば次のカテゴリへ
                    category_n += 1
            else:
                category_n = int(category_n)
            category = self.categories[category_n]
            guild = category.guild
            overwrites = {
                self.client.user:
                    discord.PermissionOverwrite.from_pair(discord.Permissions.all(), discord.Permissions.none()),
                ctx.author:
                    discord.PermissionOverwrite.from_pair(discord.Permissions(66448721), discord.Permissions.none()),
                guild.default_role:
                    discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all()),
                guild.get_role(515467411898761216):
                    discord.PermissionOverwrite.from_pair(discord.Permissions.none(), discord.Permissions.all()),
                guild.get_role(515467425429585941):
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
        await self.client.close()

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
        return (
            any(x in role_ids for x in
                (515467407381364738, 515467410174902272, 515467421323100160)
                )
            or await self.client.is_owner(ctx.author)
        )

    async def on_ready(self):
        self.limit_role: discord.Role = self.client.get_guild(
            515467348581416970).get_role(515467411898761216)

    @commands.command(brief='制限付きユーザーを付けます', check=[zatsudan_forum_check])
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
        self.index_index = self.client.get_channel(515467529167044608)

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
                await index_channel.purge(check=lambda m: m.author == self.client.user and m.embeds)
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

    @commands.command(brief='インデックスインデックスを再生成します', check=[zatsudan_forum_check])
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
                and not message.content.startswith(self.client.command_prefix + 'target'):
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

    async def on_message(self, message):
        if message.author == self.client.user:
            return
        if message.content == '\\せやな':
            await message.channel.send('わかる（天下無双）')


class Categor_recover():  # 言わずと知れたカテゴリリカバリ機能
    __slots__ = ('client', 'category_cache', 'name')

    def __init__(self, client, name=None):
        self.client: discord.Client = client
        self.name = name if name is not None else type(self).__name__

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


class Role_panel():  # 役職パネルの機能
    __slots__ = ('client', 'channel', 'pattern', 'channel_id', 'name')

    def __init__(self, client, channel_id, name=None,):
        self.client = client
        self.channel_id = channel_id
        self.name = name if name is not None else type(self).__name__
        self.pattern = re.compile(r'役職パネル\((.*?)\)')

    async def __local_check(self, ctx):
        role_ids = [r.id for r in ctx.author.roles]
        return (
            await zatsudan_forum_check(ctx)
            and (any(x in role_ids for x in (515467407381364738, 515467410174902272, 515467421323100160))
                 or await self.client.is_owner(ctx.author))  # マネージメント、サブオーナー、オーナーズが使える感じ
        )

    async def on_ready(self):
        self.channel: discord.TextChannel = self.client.get_channel(self.channel_id)
        async for message in self.channel.history().filter(lambda m: m.author == self.client.user):
            for reaction in message.reactions:
                async for user in reaction.users().filter(lambda u: u != self.client.user):
                    self.client.loop.create_task(message.remove_reaction(reaction, user))
            self.client._connection._messages.append(message)

    async def _rolepanel_add(self, ctx, role: discord.Role, tag):
        def check(m):
            return (
                m.author == self.client.user and m.embeds
                and tag in m.embeds[0].title
            )
        break1 = False
        history = await self.channel.history(reverse=True)\
            .filter(check).flatten()
        for m in history:
            embed = m.embeds[0]
            description = embed.description
            lines = description.splitlines()
            for i in range(20):
                character = chr(0x0001f1e6 + i)
                if character not in description:
                    new_lines = '\n'.join(
                        lines[0:i]
                        + ['{0}:{1}'.format(character, role.mention)]
                        + lines[i:len(lines) + 1]
                    )
                    embed.description = new_lines
                    await m.edit(embed=embed)
                    await m.add_reaction(character)
                    break1 = True
                    break
            if break1:
                break
        else:
            embed = discord.Embed(
                title='役職パネル({1})({0}ページ目)'.format(len(history) + 1, tag),
                description='\U0001f1e6:{0}'.format(role.mention)
            )
            m = await self.channel.send(embed=embed)
            await m.add_reaction('\U0001f1e6')

    @commands.command()
    async def rolepanel_add(self, ctx, role: discord.Role, tag='ノーマル'):
        await self._rolepanel_add(ctx, role, tag=tag)

    @commands.command()
    async def rolepanel_remove(self, ctx, role: discord.Role, tag=None):
        break1 = False
        async for m in self.channel.history(reverse=True)\
                .filter(lambda m: m.author == self.client.user and m.embeds):
            embed = m.embeds[0]
            description = embed.description
            if tag is not None and tag not in embed.title:
                continue
            lines = description.splitlines(keepends=True)
            for line in lines[:]:
                if role.mention in line:
                    embed.description = description.replace(line, '')
                    await m.edit(embed=embed)
                    await m.remove_reaction(line[0], self.client.user)
                    break1 = True
                    break
            m = await self.channel.get_message(m.id)
            if not m.reactions:
                await m.delete()
            if break1:
                break

    @commands.command()
    async def rolepanel_regenerate(self, ctx):

        def filter_func(m: discord.Message):
            return (
                m.author == self.client.user
                and m.embeds
            )
        prog = re.compile(r'<@&(\d*)>')
        roles = {}
        guild: discord.Guild = self.channel.guild
        async for message in self.channel.history(reverse=True)\
                .filter(filter_func):
            message: discord.Message
            tag = self.pattern.search(message.embeds[0].title).group(1)
            if tag not in roles:
                roles.update({tag: set()})
            for line in message.embeds[0].description.splitlines():
                match = prog.search(line)
                if match:
                    role_id = int(match.group(1))
                    roles[tag].add(guild.get_role(role_id))
            await message.delete()
        for tag, value in roles.items():
            value.discard(None)
            rolelist = list(value)
            for x in range(len(rolelist) // 20 + 1):
                roles = rolelist[x * 20:(x + 1) * 20]
                content = '\n'.join('{0}:{1}'.format(
                    chr(i + 0x0001f1e6), r.mention) for i, r in enumerate(roles))
                embed = discord.Embed(
                    title='役職パネル({1})({0}ページ目)'.format(x + 1, tag),
                    description=content
                )
                m = await self.channel.send(embed=embed)
                [self.client.loop.create_task(m.add_reaction(chr(0x0001f1e6 + i)))
                 for i in range(len(roles))]

    async def on_reaction_add(self, reaction, user):
        if user == self.client.user:
            return
        message = reaction.message
        if message.channel == self.channel and message.author == self.client.user:
            await message.remove_reaction(reaction, user)
            if '役職パネル' in message.embeds[0].title:
                match2 = re.search(reaction.emoji + r':<@&(\d*)>', message.embeds[0].description)
                if match2:
                    role = message.guild.get_role(int(match2.group(1)))
                    if role not in user.roles:
                        await user.add_roles(role)
                        description = '{0}の役職を付与しました。'.format(role.mention)
                        await message.channel.send(user.mention, embed=discord.Embed(description=description), delete_after=10)
                    else:
                        await user.remove_roles(role)
                        description = '{0}の役職を解除しました'.format(role.mention)
                        await message.channel.send(user.mention, embed=discord.Embed(description=description), delete_after=10)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        cache = self.client._connection._messages
        if payload.channel_id != self.channel.id or payload.message_id in (m.id for m in cache):
            return
        user = self.client.get_guild(payload.guild_id).get_member(payload.user_id)
        message = await self.client.get_channel(payload.channel_id).get_message(payload.message_id)
        cache.append(message)
        if payload.emoji.is_unicode_emoji():
            reaction = next(r for r in message.reactions if r.emoji == payload.emoji.name)
        else:
            reaction = next(r for r in message.reactions if r.custom_emoji and r.emoji.id == payload.emoji.id)
        await self.on_reaction_add(reaction, user)


class Manage_channel():
    __slots__ = ('client', 'name', 'staff')
    permissions_jp = {
        'create_instant_invite': '招待を作成',
        'manage_channels': 'チャンネルの管理',
        'manage_roles': '権限の管理',
    }
    permissions_jp_text = {
        'read_messages': 'メッセージを読む',
        'send_messages': 'メッセージを送信',
        'manage_messages': 'メッセージの管理',
        'embed_links': '埋め込みリンク',
        'attach_files': 'ファイルを添付',
        'read_message_history': 'メッセージ履歴を読む',
        'external_emojis': '外部の絵文字の使用',
        'add_reactions': 'リアクションの追加',
    }
    permissions_jp_voice = {
        'read_messages': 'チャンネルを見る',
        'connect': '接続',
        'speak': '発言',
        'mute_members': 'メンバーをミュート',
        'deafen_members': 'メンバーのスピーカーをミュート',
        'move_members': 'メンバーを移動',
        'use_voice_activation': '音声検出を使用',
        'priority_speaker': 'プライオリティスピーカー'
    }

    def __init__(self, client, name=None,):
        self.client: commands.Bot = client
        self.name = name if name is not None else type(self).__name__

    async def on_command(self, ctx):
        if self is ctx.cog:
            ctx

    def on_ready(self):
        self.staff = [self.client.get_guild(515467348581416970).get_guild(i)
                      for i in (515467410174902272, 515467421323100160)]

    @commands.command()
    async def cedit(self, ctx, *args):
        EMOJI_K = 0x1f1e6  # 絵文字定数(これを足したり引いたりするとリアクション的にうまくいく)
        EMBED_TITLE = 'チャンネル権限編集'
        if args:
            try:
                channel = await commands.TextChannelConverter().convert(ctx, args[0])
            except commands.BadArgument:
                try:
                    channel = await commands.VoiceChannelConverter().convert(ctx, args[0])
                except commands.BadArgument:
                    await ctx.send('チャンネルが見つかりませんでした。')
                    return
        else:
            channel = ctx.channel
        if (
            ctx.author in [i[0] for i in channel.overwrites]
            and channel.overwrites_for(ctx.author).manage_roles is not False
        ) \
                or await self.client.is_owner(ctx.author)\
                or any(r in ctx.author.roles for r in self.staff):
            all_commands = (
                '新規に役職を追加設定',
                '新規にユーザーを追加設定',
                '現在設定されている追加設定の変更',
                '現在設定されている追加設定の削除'
            )
            emojis = [chr(i + EMOJI_K) for i in range(len(all_commands))]
            embed = discord.Embed(
                title=EMBED_TITLE,
                description='\n'.join(
                    '{0}:{1}'.format(i, e)
                    for i, e in zip(emojis, all_commands)
                )
            )
            embed.set_footer(text='対象チャンネル:{0.name}\nチャンネルID:{0.id}'.format(channel))
            message = await ctx.send(embed=embed)
            [await message.add_reaction(e)
             for e in emojis]

            def check(reaction, user):
                return (
                    reaction.me and ctx.author == user
                    and reaction.message.id == message.id
                    and reaction.message.channel == message.channel
                )
            reaction, _ = \
                await self.client.wait_for('reaction_add', check=check)
            await message.delete()
            num_command = ord(reaction.emoji) - EMOJI_K
            if 0 <= num_command <= 1:
                if num_command == 0:
                    target_type = '役職'
                else:
                    target_type = 'ユーザー'
                description = ('チャンネルの追加設定に{0}を追加します。\n'
                               '追加したい{0}を入力してください').format(target_type)
                message = await ctx.send(description)

                def check1(message):
                    return (
                        message.channel == ctx.channel
                        and message.author == ctx.author
                    )
                message2 = await self.client.wait_for('message', check=check1)
                await message.delete()
                if num_command == 0:
                    converter = commands.RoleConverter()
                else:
                    converter = commands.MemberConverter()
                try:
                    target = await converter.convert(ctx, message2.content)
                except commands.BadArgument:
                    await ctx.send(
                        '指定した{0}が見つかりませんでした'.format(target_type)
                        + 'もう一度やり直して下さい。'
                    )
                    return
            elif 2 <= num_command <= 3:
                action = '変更' if num_command == 2 else '削除'
                description = (
                    '追加設定を{0}します\n'
                    '{0}したい役職、またはユーザーを選んでください'
                ).format(action)
                embed = discord.Embed(title=EMBED_TITLE, description=description)
                overwrites = channel.overwrites

                def func2(page=0):
                    end = (page + 1) * 17
                    if len(overwrites) < end:
                        end = len(overwrites)
                    start = page * 17
                    targets = [i[0] for i in overwrites[start:end]]
                    description = '\n'.join(
                        '{0}:{1}'.format(chr(i + EMOJI_K), t.mention)
                        for i, t in enumerate(targets)
                    )
                    return targets, description
                page = 0
                targets, description = func2(page)
                embed.add_field(name='役職・ユーザー一覧', value=description)
                message = await ctx.send(embed=embed)
                [await message.add_reaction(chr(i + EMOJI_K))
                 for i in range(len(targets))]
                await message.add_reaction('\U0001f519')
                await message.add_reaction('\U0001f51c')
                await message.add_reaction('\u274c')

                def check3(reaction, user):
                    return (
                        user == ctx.author
                        and reaction.me
                        and reaction.message.channel == message.channel
                        and reaction.message.id == message.id
                    )

                while True:
                    new_page = page
                    reaction, user = \
                        await self.client.wait_for('reaction_add', check=check3)
                    await message.remove_reaction(reaction, user)
                    if reaction.emoji == '\U0001f519':
                        new_page = page - 1
                    elif reaction.emoji == '\U0001f51c':
                        new_page = page + 1
                    elif reaction.emoji == '\u274c':
                        await message.delete()
                        await ctx.send('中止しました。')
                        return
                    else:
                        break
                    if new_page != page:
                        new_targets, description = func2(page=new_page)
                        if description != '':
                            embed.set_field_at(
                                0, name='役職・ユーザー一覧', value=description
                            )
                            await message.edit(embed=embed)
                            page = new_page
                            targets = new_targets
                await message.delete()
                target = targets[ord(reaction.emoji) - EMOJI_K]
            if num_command <= 2:
                perms_jp = self.permissions_jp.copy()
                perms_jp.update(
                    self.permissions_jp_text
                    if isinstance(channel, discord.TextChannel)
                    else self.permissions_jp_voice
                )
                perms = tuple(perms_jp.keys())

                def func1(overwrite):
                    description = ''
                    n = 0
                    for en, jp in perms_jp.items():
                        try:
                            value = getattr(overwrite, en)
                        except AttributeError:
                            continue
                        else:
                            description += '{0}'.format(chr(n + EMOJI_K))
                            description += jp
                        if value:
                            description += ':\u2705\n'
                        elif value is None:
                            description += ':\u2b1c\n'
                        else:
                            description += ':\u274c\n'
                        n += 1
                    return description
                overwrite: discord.PermissionOverwrite = channel.overwrites_for(target)
                embed = discord.Embed(
                    title=EMBED_TITLE,
                    description='{0}の権限設定を変更します'.format(target.mention)
                )
                embed.add_field(name='権限一覧', value=func1(overwrite))
                message3 = await ctx.send(embed=embed)
                [await message3.add_reaction(chr(i + EMOJI_K))
                 for i in range(len(perms))]
                await message3.add_reaction('\u2705')
                await message3.add_reaction('\u274c')

                def check2(reaction, user):
                    return (
                        user == ctx.author
                        and reaction.me
                        and reaction.message.channel == message3.channel
                        and reaction.message.id == message3.id
                    )

                loop = True
                while loop:
                    reaction, user = await self.client.wait_for('reaction_add', check=check2)
                    if reaction.emoji == '\u2705':
                        loop = False
                        continue
                    elif reaction.emoji == '\u274c':
                        await message3.delete()
                        await ctx.send('中止しました。')
                        break
                    await message3.remove_reaction(reaction, user)
                    perm = perms[ord(reaction.emoji) - EMOJI_K]
                    value = getattr(overwrite, perm)
                    if value:
                        value = False
                    elif value is None:
                        value = True
                    else:
                        value = None
                    if perm == 'manage_roles' and value:
                        value = False
                    overwrite.update(**{perm: value})
                    embed.set_field_at(0, name='権限一覧', value=func1(overwrite))
                    await message3.edit(embed=embed)
                else:
                    await message3.delete()
                    await channel.set_permissions(target, overwrite=overwrite)
                    await ctx.send('権限を変更しました。')
            elif num_command == 3:
                await channel.set_permissions(target, overwrite=None)
                await ctx.send('権限を削除しました。')
        else:
            await ctx.send('あなたはそれをする権限がありません。')


class Emergency_call():
    __slots__ = ('client', 'name', 'data', 'url')

    def __init__(self, client, name=None):
        self.client: commands.Bot = client
        self.name = name if name is not None else type(self).__name__
        self.url = os.environ.get('emergency_call_url', '')

    async def __local_check(self, ctx):
        role_ids = [r.id for r in ctx.author.roles]
        return (any(x in role_ids for x in (515467407381364738, 515467410174902272, 515467421323100160, 515467419364491266)))

    async def on_command_error(self, ctx, error):
        if ctx.cog is self:
            if isinstance(error, commands.CheckFailure):
                await ctx.send('あなたはこのコマンドを実行する権限がありません。')

    @commands.command(hidden=True)
    async def emergency_call(self, ctx):
        message = await ctx.send('エマージェンシーコールを発動しますか？')

        def check1(reaction, user):
            return reaction.message.id == message.id and reaction.message.channel == message.channel \
                and user == ctx.author
        [self.client.loop.create_task(message.add_reaction(i))
         for i in ('\u2705', '\u274c')]
        reaction, _ = await self.client.wait_for('reaction_add', check=check1)
        await message.delete()
        if reaction.emoji == '\u2705':
            Data = {'value1': str(ctx.author), 'value2': ctx.channel.name, 'value3': ctx.guild.name}
            session = self.client.http._session
            async with session.post(self.url, data=Data):
                pass
            await ctx.send('エマージェンシーコールを発動しました')
        else:
            await ctx.send('キャンセルしました')


class Kouron():
    __slots__ = ('client', 'role_dict', 'guild', 'ready', 'name')

    def __init__(self, client, name=None):
        self.client: commands.Bot = client
        self.ready = asyncio.Event(loop=client.loop)
        self.name = name if name is not None else type(self).__name__

    async def __local_check(self, ctx):
        await self.ready.wait()
        return ctx.guild == self.guild

    async def on_ready(self):
        """
        Dic1は役職のIDとレベルの対応リスト。
        self.role_dict は　役職とレベルの対応リスト。

        別なサーバーで使いたい場合は
        Dic1を対応するロールIDに変更しておいて
        get_guildの部分を、対応するサーバーIDに変更。
        """
        Dic1 = {
            482009530373505044: 50,
            482009178940899328: 40,
            450625941455110144: 30,
            448843313139679233: 20,
            448842082187214864: 10,
            448840831655215104: 5,
            268352600108171274: 1,
        }
        self.guild = self.client.get_guild(235718949625397251)
        self.role_dict = {self.guild.get_role(key): value
                          for key, value in Dic1.items()}
        self.ready.set()

    @commands.command()
    async def kouron(self, ctx: commands.context.Context, *members: discord.Member):
        if 450625941455110144 not in (r.id for r in ctx.author.roles):
            await ctx.send('あなたはまだこのコマンドを使えません。')
            return
        if len(members) <= 1:
            await ctx.send('2人以上のメンバーを指定してください。')
            return
        mentions = '\n'.join(m.mention for m in members)
        embed = discord.Embed(title='口論コマンドのテスト', description=mentions)
        embed.add_field(name='レベル合計', value='0')
        embed.set_footer(text='\u2705でこの口論に賛成します。\n\U0001f504でリロード。')
        message: discord.Message = await ctx.send(embed=embed)
        [await message.add_reaction(i)
         for i in ('\u2705', '\U0001f504')]

        def check_func1(_reaction, _user):
            return (
                _user != self.client.user
                and _reaction.me
                and _reaction.message.channel == message.channel
                and _reaction.message.id == message.id
            )

        def filter_func(_user):
            return (
                _user not in ([self.client.user, ctx.author] + list(members))
                and isinstance(_user, discord.Member)
            )
        while True:
            reaction, user = (await self.client.wait_for('reaction_add', check=check_func1))
            message = reaction.message
            if reaction.emoji == '\U0001f504':
                await message.remove_reaction('\U0001f504', user)
            reaction = next(i for i in message.reactions if i.emoji == '\u2705')
            users = await reaction.users()\
                .filter(filter_func)\
                .flatten()
            level_sum = sum(self._level_caculate(i) for i in users) if users else 0
            embed.set_field_at(0, name='レベル合計', value=str(level_sum))
            await message.edit(embed=embed)
            if level_sum >= 70:
                await ctx.send('{0}\n口論と認められました。\n速やかに別なチャンネルへの移動をお願いします。'.format(mentions))
                break

    def _level_caculate(self, member: discord.Member):
        for role, value in self.role_dict.items():
            if role in member.roles:
                return value
        return 0


class Events():
    __slots__ = ('client', 'name', 'data', 'DJ', 'beginner_chat',
                 'Normal_User', 'OverLevel10',
                 'webhook_site', 'webhook_app', 'webhook_runner',
                 'saves')

    def __init__(self, client, data: dict, name=None, saves=None):
        self.client: commands.Bot = client
        self.name = name if name is not None else type(self).__name__
        self.data = data
        self.saves = saves if saves is not None else []

    async def on_ready(self):
        loop = self.client.loop
        guild: discord.Guild = self.client.get_guild(515467348581416970)
        self.DJ = guild.get_role(515467441959337984)
        # self.beginner_chat = client.get_channel(524540064995213312)
        self.Normal_User = guild.get_role(515467427459629056)
        self.OverLevel10 = guild.get_role(515467423101747200)

        #  Webhookの受信準備
        self.webhook_app = aiohttp.web.Application()
        members = inspect.getmembers(self, inspect.iscoroutinefunction)
        for name, member in members:
            try:
                splited = name.split('_')
                if splited[0] == 'webhook':
                    self.webhook_app.router.add_route(
                        method=splited[1],
                        path='/'.join([''] + splited[2:]),
                        handler=member
                    )
            except IndexError:
                pass
        self.webhook_runner = aiohttp.web.AppRunner(self.webhook_app)
        await self.webhook_runner.setup()
        port = int(os.environ.get('PORT', 52524))
        self.webhook_site = aiohttp.web.TCPSite(self.webhook_runner, port=port, reuse_address=True, reuse_port=True)
        await self.webhook_site.start()
        print(self.webhook_site.name)

    async def on_member_join(self, member):
        if 'discord.gg' in member.display_name:
            await member.ban(reason='招待リンクの名前のため、BAN', delete_message_days=1)
        else:
            try:
                new_member = next(c for c in member.guild.channels if c.name == 'ニューメンバー')
            except StopIteration:
                pass
            else:
                content = self.data['join_message'].format(member.mention, member.guild.name)
                await new_member.send(content)

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
                zatsudan_forum = member.guild.get_channel(515467559051591681)
                new_member = next(c for c in member.guild.channels if c.name == 'ニューメンバー')
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
                try:
                    await zatsudan_forum.send(embed=embed)
                except discord.Forbidden:
                    pass
                content = (
                    '{0}が退出しました。'
                    'ご利用ありがとうございました。'
                ).format(member)
                await new_member.send(content)

    async def on_voice_state_update(self, member, before, after):
        voice_text_pair = self.data['voice_text']
        if (
            after.channel is not None
            and (before.channel is None
                 or before.channel != after.channel)
            and str(after.channel.id) in voice_text_pair
        ):
            text_channel = client.get_channel(
                voice_text_pair[str(after.channel.id)])
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
            and (after.channel is None
                 or before.channel != after.channel)
            and str(before.channel.id) in voice_text_pair
        ):
            text_channel = client.get_channel(
                voice_text_pair[str(before.channel.id)])
            embed = discord.Embed(
                title='ボイスチャンネル退出通知',
                description='{0}が、退出しました。'.format(member.mention),
                colour=0xaf0000
            )
            await text_channel.send(embed=embed, delete_after=180)
            if before.channel.id == 515467651691315220:  # 音楽鑑賞VCの場合
                await member.remove_roles(self.DJ)  # DJ役職を解除

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # if before.roles != after.roles:
        #     if (
        #         self.Normal_User in after.roles
        #         and self.OverLevel10 not in after.roles
        #     ):
        #         await self.beginner_chat.set_permissions(
        #             after,
        #             overwrite=discord.PermissionOverwrite.from_pair(
        #                 discord.Permissions(37080128),
        #                 discord.Permissions(2 ** 53 - 37080129)
        #             )
        #         )
        #     else:
        #         await self.beginner_chat.set_permissions(
        #             after,
        #             overwrite=None
        #         )
        pass

    async def save_all(self):
        for func in self.saves:
            try:
                await func()
            except Exception:
                pass

    async def webhook_post_github(self, request: aiohttp.web.Request):
        data = await request.json()
        stream = io.StringIO(json.dumps(data, indent=4))
        file = discord.File(stream, 'github.json')
        await self.client.get_channel(531377173869625345).send(file=file)
        await self.save_all()
        return aiohttp.web.StreamResponse()


class Level_counter():
    __slots__ = ('exp', 'count', 'limit')

    def __init__(self, exp=0, count=0):
        self.exp = exp
        self.count = count
        self.limit = False

    @staticmethod
    def func1(n):
        return 5 * n * (2 * n**2 + 33 * n + 151) / 6

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
            self.exp += random.randint(10, 40)
        else:
            self.exp += random.randint(1, 5)


class Level():  # レベルシステム（仮運用）
    __slots__ = ('client', 'save_channel', 'name', 'data', 'firstlaunch', 'ranking_limiter',
                 'cache_messages', 'ranking_channel')
    filename = 'Level.json'

    def __init__(self, client, name=None,):
        self.client = client
        self.name = name if name is not None else type(self).__name__
        self.data = {}
        self.firstlaunch = True
        self.ranking_limiter = False
        self.cache_messages = []

    async def on_ready(self):
        loop = self.client.loop
        self.save_channel: discord.TextChannel \
            = self.client.get_channel(531377173869625345)
        self.ranking_channel: discord.TextChannel \
            = self.client.get_channel(533636280593154048)

        def func3(m: discord.Message):
            return(
                m.author == self.client.user
                and m.embeds
            )

        self.cache_messages = await self.ranking_channel.history(limit=None)\
            .filter(func3).flatten()
        self.cache_messages.sort(key=lambda m: m.created_at)
        if self.firstlaunch:

            def func1(m: discord.Message):
                return(
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
            loop.create_task(self.autosave_task())

    async def on_message(self, message):
        if message.author.bot or self.client.user == message.author:
            return
        member = message.author
        member_id = str(member.id)
        if member_id not in self.data:
            self.data.update({member_id: Level_counter()})
        sub_data: Level_counter = self.data[member_id]
        old_level = sub_data.level
        await sub_data.message()
        new_level = sub_data.level
        self.client.loop.create_task(self.update_ranking())
        if new_level != old_level:
            content = (
                '＊{0}のレベルが{1}になった。\n'
                '＊次のレベルまで{2}EXP。'
            ).format(message.author.mention, new_level, sub_data.max_exp)
            await message.channel.send(content)

    @commands.command()
    async def rank(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        member_id = str(member.id)
        try:
            data: Level_counter = self.data[member_id]
        except KeyError:
            await ctx.send('＊あなたのデータはまだできていない。\n＊発言をすると、データが作られる。')
        else:
            content = (
                '＊　{0}　ー　LV　{1}　EXP　{2}\n'
                '＊次のレベルまで{3}EXP。'
            ).format(member.display_name, data.level, data.exp, data.next_exp)
            await ctx.send(content)

    async def _save(self):
        data_dict = {
            key: {'exp': value.exp, 'count': value.count}
            for key, value in self.data.items()
        }
        text = json.dumps(data_dict, indent=4)
        stream = io.BytesIO(text.encode('utf-8'))
        file = discord.File(stream, filename=self.filename)
        await self.save_channel.send(file=file)

    async def autosave_task(self):
        while not self.client.is_closed():
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
            await asyncio.sleep(second)
            await self._save()

    @commands.command()
    async def save_level(self, ctx):
        if await self.client.is_owner(ctx.author):
            await ctx.send('＊（コマンドを打っていたら、ケツイがみなぎった。）')
            try:
                await self._save()
            except Exception as e:
                await ctx.send('＊セーブに失敗したようだ。（ログを確認してね）')
                raise e
            else:
                await ctx.send('セーブしました。')
        else:
            await ctx.send('＊ケツイがまだ足りないようだ。')

    async def update_ranking(self):
        if not self.ranking_limiter:
            self.ranking_limiter = True
            try:
                guild = self.ranking_channel.guild
                subdata = [(key, value) for key, value in self.data.items()
                           if guild.get_member(int(key)) is not None]
                subdata.sort(key=lambda i: i[1].exp, reverse=True)
                for page in itertools.count():
                    sub_subdata = subdata[page * 25:(page + 1) * 25]
                    if not sub_subdata:
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
                for message in self.cache_messages[page:]:
                    await message.delete()
                del self.cache_messages[page:]
            finally:
                await asyncio.sleep(5)
                self.ranking_limiter = False


@client.listen('on_ready')
async def on_ready():
    global firstlaunch
    if firstlaunch:
        firstlaunch = False
        client.loop.create_task(skyline_update())
        client.loop.create_task(
            task_bump(client, client.get_channel(515467856239132672))
        )
    print(client.user.name, client.user.id, '起動しました。', sep=':')


async def skyline_update():
    channel = client.get_channel(515468115535200256)
    webhooks = await channel.webhooks()
    webhook: discord.Webhook = webhooks[0]
    while not client.is_closed():
        async for message in channel.history().filter(lambda m: m.author.id == webhook.id):
            break
        with ThreadPoolExecutor(max_workers=1) as t:
            partial1 = functools.partial(
                feedparser.parse,
                'https://github.com/Kesigomon/Skyline_py/commits/master.atom'
            )
            feed = await client.loop.run_in_executor(t, partial1)
        entry = feed.entries[0]
        try:
            flag = entry.link != message.embeds[0].url
        except UnboundLocalError:
            flag = True
        if flag:
            embed = discord.Embed(
                title=entry.link.replace('https://github.com/Kesigomon/Skyline_py/commit/', ''),
                description=entry.title,
                timestamp=datetime.datetime(*entry.updated_parsed[0:7]),
                url=entry.link
            )
            embed.set_author(name=entry.author, url=entry.author_detail.href,
                             icon_url=entry.media_thumbnail[0]['url'])
            await webhook.send(embed=embed)
        await asyncio.sleep(60)


async def task_bump(client, channel):
    disboard_bot_id = 302050872383242240
    Interval = datetime.timedelta(hours=2)
    disboard_bot = await client.get_user_info(disboard_bot_id)
    mention = '<@&515467430018154507>'

    def check1(m):
        return m.author == disboard_bot and ':thumbsup:' in m.embeds[0].description

    while not client.is_closed():
        async for x in channel.history():
            if check1(x):
                break
        else:
            del x
        try:
            TD1 = datetime.datetime.utcnow() - x.created_at
            if TD1 >= Interval:
                await channel.send(
                    mention
                    + '既に2時間以上経っていますよ\n'
                    + 'SKYLINEは!disboard bumpするといいと思います'
                )
            else:
                await asyncio.sleep((Interval - TD1).total_seconds())
                await channel.send(
                    mention
                    + '2時間経ちましたよ\n'
                    + 'SKYLINEは!disboard bumpするといいと思います'
                )
        except NameError:
            await channel.send(
                mention
                + 'このサーバーで一度もコマンドを実行していませんね\n'
                + 'SKYLINEは!disboard bumpするといいと思います'
            )
        await client.wait_for(event='message', check=check1)


@client.event
async def on_command(ctx):
    print('{0.author.name}は{0.command.name}を{0.channel.name}で使用しました'.format(ctx))
level = Level(client, name='レベルシステム')
saves = [level._save]
with open(os.path.dirname(__file__) + os.sep + 'config.yaml', encoding='utf-8') as f:
    data = yaml.load(f)
client.add_cog(Normal_Command(client, data, '普通のコマンド'))
client.add_cog(Bot_Owner_Command(client, 'BOTオーナー用コマンド'))
client.add_cog(Owners_Command(client, 'オーナーズ用コマンド'))
client.add_cog(Staff_Command(client, 'スタッフ用コマンド'))
client.add_cog(DM_Command(client, 'DM用コマンド'))
client.add_cog(Joke_Command(client, data, 'ネタコマンド'))
client.add_cog(Role_panel(client, 515467531176116224, '役職パネル'))
client.add_cog(Manage_channel(client, '自由チャンネル編集コマンド'))
client.add_cog(Emergency_call(client, '緊急呼び出しコマンド'))
client.add_cog(Categor_recover(client, 'カテゴリーリカバリー'))
# client.add_cog(Kouron(client, '口論コマンド'))
client.add_cog(Events(client, data, '参加・退出通知、VC通知', saves=saves))
client.add_cog(level)
if __name__ == '__main__':
    token = ''
    client.run(token)
