import asyncio
import re
import os 
import random

import discord
from discord.ext import commands
client = commands.Bot('sk!')
async def check1(ctx):
    return ctx.guild is not None

@client.event
async def on_member_join(member):
    name = member.display_name
    des1 = random.choice(join_messages).format(name,member.guild.me.display_name)
    embed = discord.Embed(title='{0}さんが参加しました。'.format(name),description=
    '```\n{3}\n```\nようこそ{0}さん、よろしくお願いします！\nこのサーバーの現在の人数は{1}です。\n{2}に作られたアカウントです。'
    .format(name,member.guild.member_count,member.created_at,des1))
    await client.get_channel(412501473164001290).send(embed=embed)  
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
    await client.get_channel(447751512064655370).send(content)
@client.event
async def on_member_remove(member):
    name = member.display_name
    embed = discord.Embed(title='{0}さんが退出しました。'.format(name)
    ,description='{0}さん、ご利用ありがとうございました。\nこのサーバーの現在の人数は{1}人です'.format(name,member.guild.member_count))
    await client.get_channel(412501473164001290).send(embed=embed) 
    content = """
{0}が退出しました。
ご利用ありがとうございました。
""".format(member)
    await client.get_channel(447751512064655370).send(content)
    

@client.command()
@commands.check(check1)
async def dainspc(ctx):
    await ctx.send('<@328505715532759043>')

@client.command()
@commands.check(check1)
async def agree(ctx):
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
@client.listen('on_ready')
async def on_ready():
    global rolelist,join_messages
    guild = client.get_guild(235718949625397251)
    with open(os.path.dirname(__file__)+os.sep+'ids.txt',encoding='utf-8') as f:
        role_ids = f.read().splitlines()
    with open(os.path.dirname(__file__)+os.sep+'join_message.txt',encoding='utf-8') as f:
        join_messages = f.read().splitlines()
    rolelist = [guild.get_role(int(i)) for i in role_ids] 
    await create_role_panel()
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
async def create_role_panel():
    global Lock
    #ループ変更するからこんな回りくどい手を取らないといけなかったりする。
    try:
        Lock
    except NameError:
        Lock = asyncio.Lock(loop=client.loop)
    async with Lock:
        channel = client.get_channel(449185870684356608)
        await channel.purge(limit=None,check=lambda m:m.embeds and m.author == client.user and '役職パネル' in m.embeds[0].title) 
        for x in range(len(rolelist)//20 + 1):            
            roles = rolelist[x*20:(x+1)*20]
            content = '\n'.join('{0}:{1}'.format(chr(i+0x0001f1e6),r.mention) for i,r in enumerate(roles))
            embed = discord.Embed(title='役職パネル({0}ページ目)'.format(x+1),description=content)
            m = await channel.send(embed=embed)
            [client.loop.create_task(m.add_reaction(chr(0x0001f1e6+i))) for i in range(len(roles))]