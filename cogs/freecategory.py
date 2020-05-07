import typing

import discord
from discord.ext import commands

from .general import is_staff, free_category, free_category_create


class FreeCategory(commands.Cog):
    __slots__ = ('client', 'name', 'staff',)
    permissions_jp = {
        # 'create_instant_invite': '招待を作成',
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

    @property
    def category(self):
        return self.client.get_channel(free_category)

    @property
    def create_channel(self):
        return self.client.get_channel(free_category_create)

    @commands.command(name='ftcc')
    async def free_text_channel_create(self, ctx, *, name):
        channel = await self._free_channel_create(ctx, name)
        if channel is not None:
            await ctx.send(
                '作成しました。\n{0}\nあと{1}チャンネル作成可能。'
                .format(channel.mention, 50 - len(channel.category.channels))
            )

    async def _free_channel_create(self, ctx, name):
        category = self.category
        if len(category.channels) >= 50:
            await ctx.send(
                "チャンネルが一杯で作成できません。\n"
                "運営に連絡してください。"
            )
            return
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
                discord.PermissionOverwrite.from_pair(
                    discord.Permissions(37080128), discord.Permissions(2 ** 53 - 37080129)),
        }
        return await guild.create_text_channel(name, overwrites=overwrites, category=category)

    @commands.command()
    async def cedit(self, ctx,
                    channel: typing.Union[discord.TextChannel, discord.VoiceChannel] = None):
        EMOJI = 0x1f1e6  # 絵文字定数(これを足したり引いたりするとリアクション的にうまくいく)
        EMBED_TITLE = 'チャンネル権限編集'
        if channel is None:
            channel = ctx.channel
        if (
            (
                ctx.author in channel.overwrites
                and channel.overwrites_for(ctx.author).manage_roles is not False
            )  # メンバーの追加設定があり、かつ「権限の管理」がNone
            or await self.client.is_owner(ctx.author)  # オーナー
            or await is_staff(ctx.author)  # スタッフチーム
        ):
            all_commands = (
                '新規に役職を追加設定',
                '新規にユーザーを追加設定',
                '現在設定されている追加設定の変更',
                '現在設定されている追加設定の削除'
            )
            emojis = [chr(i + EMOJI) for i in range(len(all_commands))]
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

            def check(r, u):
                return (
                        r.me and ctx.author == u
                        and r.message.id == message.id
                        and r.message.channel == message.channel
                )
            reaction, _ = \
                await self.client.wait_for('reaction_add', check=check)
            await message.delete()
            num_command = ord(reaction.emoji) - EMOJI
            if 0 <= num_command <= 1:
                # ユーザーまたは役職の追加
                if num_command == 0:
                    target_type = '役職'
                else:
                    target_type = 'ユーザー'
                description1 = ('チャンネルの追加設定に{0}を追加します。\n'
                               '追加したい{0}を入力してください').format(target_type)
                message = await ctx.send(description1)

                def check1(m):
                    return (
                            m.channel == ctx.channel
                            and m.author == ctx.author
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
                description1 = (
                    '追加設定を{0}します\n'
                    '{0}したい役職、またはユーザーを選んでください'
                ).format(action)
                embed = discord.Embed(title=EMBED_TITLE, description=description1)
                overwrites = channel.overwrites

                def func2(_page=0):
                    end = (_page + 1) * 17
                    if len(overwrites) < end:
                        end = len(overwrites)
                    start = _page * 17
                    tg = [i for i in overwrites.keys()][start:end]
                    try:
                        tg.remove(self.client.user)
                    except ValueError:
                        pass
                    desc = '\n'.join(
                        '{0}:{1}'.format(chr(i + EMOJI), t.mention)
                        for i, t in enumerate(tg)
                    )
                    return tg, desc
                page = 0
                targets, description1 = func2(page)
                embed.add_field(name='役職・ユーザー一覧', value=description1)
                message = await ctx.send(embed=embed)
                [await message.add_reaction(chr(i + EMOJI))
                 for i in range(len(targets))]
                await message.add_reaction('\U0001f519')
                await message.add_reaction('\U0001f51c')
                await message.add_reaction('\u274c')

                def check3(r, u):
                    return (
                            u == ctx.author
                            and r.me
                            and r.message.channel == message.channel
                            and r.message.id == message.id
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
                        new_targets, description1 = func2(_page=new_page)
                        if description1 != '':
                            embed.set_field_at(
                                0, name='役職・ユーザー一覧', value=description1
                            )
                            await message.edit(embed=embed)
                            page = new_page
                            targets = new_targets
                await message.delete()
                target = targets[ord(reaction.emoji) - EMOJI]
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
                            description += '{0}'.format(chr(n + EMOJI))
                            description += jp
                        if value:
                            description += ':\u2705\n'
                        elif value is None:
                            description += ':\u2b1c\n'
                        else:
                            description += ':\u274c\n'
                        n += 1
                    return description
                overwrite1: discord.PermissionOverwrite = channel.overwrites_for(target)
                embed = discord.Embed(
                    title=EMBED_TITLE,
                    description='{0}の権限設定を変更します'.format(target.mention)
                )
                embed.add_field(name='権限一覧', value=func1(overwrite1))
                message3 = await ctx.send(embed=embed)
                [await message3.add_reaction(chr(i + EMOJI))
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
                    perm = perms[ord(reaction.emoji) - EMOJI]
                    value = getattr(overwrite1, perm)
                    if value:
                        value = False
                    elif value is None:
                        value = True
                    else:
                        value = None
                    if perm == 'manage_roles' and value:
                        value = False
                    overwrite1.update(**{perm: value})
                    embed.set_field_at(0, name='権限一覧', value=func1(overwrite1))
                    await message3.edit(embed=embed)
                else:
                    await message3.delete()
                    await channel.set_permissions(target, overwrite=overwrite1)
                    await ctx.send('権限を変更しました。')
            elif num_command == 3:
                await channel.set_permissions(target, overwrite=None)
                await ctx.send('権限を削除しました。')
        else:
            await ctx.send('あなたはそれをする権限がありません。')
