import discord
from discord.ext import commands
from .general import is_zatudanfolum, agree_messages
import random


class Normal_Command(commands.Cog):
    __slots__ = ('client', 'name', 'categories')

    def __init__(self, client, name=None):
        self.client: commands.Bot = client
        self.name = name if name is not None else type(self).__name__

    async def cog_check(self, ctx):
        return ctx.guild is not None

    # ロールサーチ
    @commands.command()
    async def role_search(self, ctx, *, role: discord.Role):
        embed = discord.Embed(
            title='ロールサーチの結果', description='{0}\nID:{1}'.format(role.mention, role.id))
        await ctx.send(embed=embed)

    @commands.command(aliases=['tw'])
    async def tweet(self, ctx: commands.Context):
        await ctx.message.delete()
        if ctx.channel.id != 515467568652484608:
            await ctx.send('このチャンネルでは実行できません。')
        else:
            mes1 = await ctx.send('ツイートを送信してください。')
            mes2 = await self.client.wait_for(
                event='message',
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            await mes1.delete()
            [await mes2.add_reaction(i)
             for i in ('\u2764', '\U0001f501')]

    # サーバ情報表示
    @commands.command()
    async def server(self, ctx):
        guild: discord.Guild = ctx.guild
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

    @commands.command(check=[is_zatudanfolum])
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
            name = member.display_name
            des1 = random.choice(agree_messages).format(name, member.guild.me.display_name)
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

            await self.client.get_channel(515467559051591681).send(embed=embed)
        else:
            await ctx.send('登録終わってますやんか')
