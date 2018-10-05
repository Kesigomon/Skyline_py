import discord
from discord.ext import commands
client = commands.Bot('sk!')

async def check1(ctx):
    return ctx.guild is not None

@client.command
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