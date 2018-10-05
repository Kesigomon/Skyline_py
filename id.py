import discord
from discord.ext import commands

client = discord.Client()

@client.event
async def on_ready():
    guild = client.get_guild(235718949625397251)