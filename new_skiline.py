import asyncio
import os
import random
import re
import datetime
import functools
import yaml
from concurrent.futures import ThreadPoolExecutor

import discord
import feedparser
from discord.ext import commands

client = commands.Bot('sk!')
firstlaunch = True
class 普通のコマンド:
    __slots__ = ('client',)
    def __init__(self,client):
        self.client = client
    async def __local_check(self,ctx):
        return ctx.guild is not None
    #ロールサーチ
    @commands.command()
    async def role_search(self,ctx,*,role:discord.Role):
        embed = discord.Embed(title='ロールサーチの結果',description='{0}\nID:{1}'.format(role.mention,role.id))
        await ctx.send(embed=embed)
    #サーバ情報表示
    @commands.command()
    async def server(self,ctx):
        guild = ctx.guild
        description = '''
        サーバーの名前:{0.name}
        サーバーの人数:{0.member_count}
        サーバーのID:{0.id}
        サーバー作成日:{0.created_at}
        サーバーのオーナー:{0.owner.mention}
        サーバーのチャンネル数:{1}
        '''.format(guild,len(guild.channels))
        embed = discord.Embed(title='サーバー情報',description=description)
        embed.set_thumbnail(url=guild.icon_url)
        await ctx.send(embed=embed)
    #投票機能
    @commands.command()
    async def poll(self,ctx,*args):
        if len(args) == 0:
            pass
        elif len(args) == 1:
            args = (args[0],'ワイトもそう思います','さまよえる亡者はそうは思いません')
        if 1 <= len(args) <= 21:
            answers = args[1:]
            emojis = [chr(0x0001f1e6+i) for i in range(len(answers))]
            embed = discord.Embed(description='\n'.join(e+a for e,a in zip(emojis,answers)))
            m:discord.Message = await ctx.send('**{0}**'.format(args[0]),embed=embed)
            [self.client.loop.create_task(m.add_reaction(e)) for e in emojis]
    @commands.command()
    async def agree(self,ctx):
    #送信する文章指定。
        content = """
{0}さんの
アカウントが登録されました！{1}の
{2}個のチャンネルが利用できます！
まずは<#437110659520528395>で自己紹介をしてみてください！
""".format(ctx.author.mention,ctx.guild.name,len(ctx.guild.channels))
#左から順に、ユーザーのメンション、サーバーの名前、サーバーのチャンネル数に置き換える。
        #役職付与
        await ctx.author.add_roles(ctx.guild.get_role(268352600108171274))
        #メッセージ送信
        await ctx.send(content)
class BOTオーナー用コマンド:
    __slots__ = ('client',)
    def __init__(self,client):
        self.client:commands.Bot = client
    async def __local_check(self,ctx):
        return await self.client.is_owner(ctx.author)
    @commands.command(hidden=True)
    async def stop(self,ctx):
        await ctx.send('停止しまーす')
        await client.close()
    @commands.command(hidden=True)
    async def panel_regenerate(self,ctx):
        await create_role_panel()
        await ctx.send('再生成終了しました。')
class オーナーズ用コマンド:
    __slots__ = ('client','index_index')
    def __init__(self,client):
        self.client:commands.Bot = client
    async def __local_check(self,ctx):
        return ctx.guild is not None and (await self.client.is_owner(ctx.author) or ctx.author == ctx.guild.owner)
    async def on_ready(self):
        self.index_index = client.get_channel(500274844253028353)
    @commands.command()
    async def create_category_index(self,ctx,*args):
        if args:
            category = await commands.converter.CategoryChannelConverter().convert(ctx,args[0])
        else:
            category = ctx.channel.category
        try:
            index_channel:discord.TextChannel = next(c for c in category.channels if c.name == 'category-index')
        except StopIteration:
            await ctx.send('index用チャンネルが見つかりませんでした。')
        else:
            channels = sorted((c for c in category.channels if isinstance(c,discord.TextChannel) and c != index_channel)
            ,key=lambda c:c.position)
            await index_channel.purge(limit=None,check=lambda m:m.author == self.client.user)
            await index_channel.send('\n'.join(('-'*10,self.index_index.mention,'-'*10,'')) 
            +'\n'.join(map(lambda c:c.mention,channels)))
            for channel in channels:
                description = channel.topic if channel.topic else 'トピックはないと思います'
                embed = discord.Embed(title=channel.name,description='ID:{0}'.format(channel.id))
                embed.add_field(name='チャンネルトピック',value=description)
                await index_channel.send(embed=embed)
    @commands.command()
    async def create_index_index(self,ctx):
        content = str()
        for category in ctx.guild.categories:
            try:
                index_channel:discord.TextChannel = next(c for c in category.channels if c.name == 'category-index')
            except StopIteration:
                pass
            else:
                content += '{0}:{1}\n'.format(category.name,index_channel.mention)
        else:
            await self.index_index.purge(limit=None)
            await self.index_index.send(content)
#参加メッセージ
@client.event
async def on_member_join(member):
    name = member.display_name
    des1 = random.choice(join_messages).format(name,member.guild.me.display_name)
    embed = discord.Embed(title='{0}さんが参加しました。'.format(name),colour=0x2E2EFE,description=
    '```\n{3}\n```\nようこそ{0}さん、よろしくお願いします！\nこのサーバーの現在の人数は{1}です。\n{2}に作られたアカウントです。'
    .format(name,member.guild.member_count,member.created_at,des1))
    embed.set_thumbnail(url=member.avatar_url)
    channel = next(c for c in member.guild.channels if c.name == '雑談フォーラム')
    try:
        await channel.send(embed=embed)  
    except discord.Forbidden:
        pass
    content = """
    ───────────────────────
{0}さん、
ようこそ{1}へ！:tada: :hugging: 
雑談フォーラムは雑談に特化したDiscordサーバー。
しかし、現状はほとんどのチャンネルが
利用できないようになっています。
<#449813164171853825> をよく読み、
「アカウント登録」を
済ませてからご参加ください！

<#447747221975334912> を読むと楽しく利用できます。

当サーバーに関する情報はこちらをご覧ください：
https://chat-forum-dcc.jimdo.com/
──────────────────────
""".format(member.mention,member.guild.name)
    channel = next(c for c in member.guild.channels if c.name == 'ニューメンバー')
    await channel.send(content)
    # await ctx.author.send(content2)
#退出メッセージ
@client.event
async def on_member_remove(member):
    name = member.display_name
    embed = discord.Embed(title='{0}さんが退出しました。'.format(name),colour=0x2E2EFE
    ,description='{0}さん、ご利用ありがとうございました。\nこのサーバーの現在の人数は{1}人です'.format(name,member.guild.member_count))
    embed.set_thumbnail(url=member.avatar_url)
    channel = next(c for c in member.guild.channels if c.name == '雑談フォーラム')
    try:
        await channel.send(embed=embed) 
    except discord.Forbidden:
        pass
    content = """
{0}が退出しました。
ご利用ありがとうございました。
""".format(member)
    channel = next(c for c in member.guild.channels if c.name == 'ニューメンバー')
    await channel.send(content)
    
#だいんさん呼ぶ用コマンド
# @client.command()
# @commands.check(check1)
# async def dainspc(ctx):
#     await ctx.send('<@328505715532759043>')
@client.listen('on_ready')
async def on_ready():
    global rolelist,join_messages,firstlaunch,voice_text_pair
    if firstlaunch:
        firstlaunch = False
        client.loop.create_task(skyline_update())
    guild = client.get_guild(235718949625397251)
    with open(os.path.dirname(__file__)+os.sep+'config.yaml',encoding='utf-8') as f:
        data = yaml.load(f)
    role_ids = data['roles']
    join_messages = data['join_message']
    voice_text_pair = data['voice_text']
    rolelist = [guild.get_role(int(i)) for i in role_ids]
    [rolelist.remove(None) for i in rolelist[:] if i is None] 
    await create_role_panel()
    print(client.user.name,client.user.id,'起動しました。',sep=':')
@client.listen('on_message')
async def on_message(message):
    if message.author == client.user:
        return
    if message.content == 'せやな':
        await message.channel.send('わかる（天下無双）')
@client.event
async def on_reaction_add(reaction,user):
    if user == client.user:
        return
    message = reaction.message
    if message.channel.id == 449185870684356608 and message.author == client.user:
        await message.remove_reaction(reaction,user)
        match = re.search(r'役職パネル\((\d)ページ目\)', message.embeds[0].title)
        if match:
            role = rolelist[ord(reaction.emoji) + int(match.expand(r'\1'))*20 - 0x1F1FA ]
            if role not in user.roles:
                await user.add_roles(role)
                description = '{0}の役職を付与しました。'.format(role.mention)
                await message.channel.send(user.mention,embed=discord.Embed(description=description),delete_after=10)
            else:
                await user.remove_roles(role)
                description = '{0}の役職を解除しました'.format(role.mention)
                await message.channel.send(user.mention,embed=discord.Embed(description=description),delete_after=10)
@client.listen('on_voice_state_update')
async def on_voice_state_update(member, before, after):
    if after.channel is not None and (before.channel is None or before.channel != after.channel) and str(after.channel.id) in voice_text_pair:
        text_channel = client.get_channel(voice_text_pair[str(after.channel.id)])
        embed = discord.Embed(title='ボイスチャンネル入室通知',description='{0}が、入室しました。'.format(member.mention),colour=0x00af00)
        await text_channel.send(embed=embed)
    if before.channel is not None and (after.channel is None or before.channel != after.channel) and str(before.channel.id) in voice_text_pair:
        text_channel = client.get_channel(voice_text_pair[str(before.channel.id)])
        embed = discord.Embed(title='ボイスチャンネル退出通知',description='{0}が、退出しました。'.format(member.mention),colour=0xaf0000)
        await text_channel.send(embed=embed)
async def create_role_panel():
    channel = client.get_channel(449185870684356608)
    await channel.purge(limit=None,check=lambda m:m.embeds and m.author == client.user and '役職パネル' in m.embeds[0].title) 
    for x in range(len(rolelist)//20 + 1):            
        roles = rolelist[x*20:(x+1)*20]
        content = '\n'.join('{0}:{1}'.format(chr(i+0x0001f1e6),r.mention) for i,r in enumerate(roles))
        embed = discord.Embed(title='役職パネル({0}ページ目)'.format(x+1),description=content)
        m = await channel.send(embed=embed)
        [client.loop.create_task(m.add_reaction(chr(0x0001f1e6+i))) for i in range(len(roles))]
async def skyline_update():
    channel =client.get_channel(498275174123307028)
    webhooks = await channel.webhooks()
    webhook:discord.Webhook = webhooks[0]
    while not client.is_closed():
        async for message in channel.history().filter(lambda m:m.author.id == 498275277269499904):
            break
        with ThreadPoolExecutor(max_workers=1) as t:
            feed = await client.loop.run_in_executor(t,functools.partial(feedparser.parse,'https://github.com/Kesigomon/Skyline_py/commits/master.atom'))
        entry = feed.entries[0]
        if entry.link != message.embeds[0].url:
            embed = discord.Embed(title=entry.link.replace('https://github.com/Kesigomon/Skyline_py/commit/',''),description=entry.title,timestamp=datetime.datetime(*entry.updated_parsed[0:7]),url=entry.link)
            embed.set_author(name=entry.author,url=entry.author_detail.href,icon_url=entry.media_thumbnail[0]['url'])
            await webhook.send(embed=embed)
        await asyncio.sleep(60)
client.add_cog(普通のコマンド(client))
client.add_cog(BOTオーナー用コマンド(client))
client.add_cog(オーナーズ用コマンド(client))
if __name__ == '__main__':
    token = ''
    client.run(token)