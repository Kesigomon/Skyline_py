# スタッフ専用コマンドはここに書く
import discord
from discord.ext import commands

from .general import ZATSUDAN_FORUM_ID, is_staff


class Staff_Command(commands.Cog):
    __slots__ = ('client', 'limit_role', 'name', 'guild')

    def __init__(self, client: commands.Bot, name=None):
        self.client = client
        self.name = name if name is not None else type(self).__name__

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(ZATSUDAN_FORUM_ID)
        self.limit_role: discord.Role = self.guild.get_role(515467411898761216)

    async def cog_check(self, ctx):
        return await is_staff(ctx.author)

    @commands.command(brief='制限付きユーザーを付けます')
    async def limit(self, ctx, member: discord.Member):
        await member.edit(roles=[self.limit_role])
