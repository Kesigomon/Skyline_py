import discord
from discord.ext import commands

import re
from .general import is_staff, rolepanel_channel


class Role_panel(commands.Cog):  # 役職パネルの機能
    __slots__ = ('client', 'channel', 'name')
    pattern = re.compile(r'役職パネル\((.*?)\)')

    def __init__(self, client, name=None,):
        self.client = client
        self.name = name if name is not None else type(self).__name__

    async def cog_check(self, ctx):
        return await is_staff(ctx.author)

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel: discord.TextChannel = self.client.get_channel(rolepanel_channel)
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
        history = await self.channel.history(oldest_first=True)\
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
        async for m in self.channel.history(oldest_first=True)\
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
            m = await self.channel.fetch_message(m.id)
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
        async for message in self.channel.history(oldest_first=True)\
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

    @commands.Cog.listener()
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
                        await message.channel.send(
                            user.mention,
                            embed=discord.Embed(description=description),
                            delete_after=10
                        )
                    else:
                        await user.remove_roles(role)
                        description = '{0}の役職を解除しました'.format(role.mention)
                        await message.channel.send(
                            user.mention,
                            embed=discord.Embed(description=description),
                            delete_after=10
                        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        cache = self.client._connection._messages
        if payload.channel_id != self.channel.id or payload.message_id in (m.id for m in cache):
            return
        user = self.client.get_guild(payload.guild_id).get_member(payload.user_id)
        message = await self.channel.fetch_message(payload.message_id)
        cache.append(message)
        if payload.emoji.is_unicode_emoji():
            reaction = next(r for r in message.reactions if r.emoji == payload.emoji.name)
        else:
            reaction = next(r for r in message.reactions if r.custom_emoji and r.emoji.id == payload.emoji.id)
        await self.on_reaction_add(reaction, user)
