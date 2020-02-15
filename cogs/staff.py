# スタッフ専用コマンドはここに書く
import discord
from discord.ext import commands

from .general import ZATSUDAN_FORUM_ID, is_subowner, event_channel


class Staff_Command(commands.Cog):
    __slots__ = ('client', 'limit_role', 'name', 'guild')

    def __init__(self, client: commands.Bot, name=None):
        self.client = client
        self.name = name if name is not None else type(self).__name__

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(ZATSUDAN_FORUM_ID)
        self.normal_user: discord.Role = self.guild.get_role(515467427459629056)
        self.limit_role: discord.Role = self.guild.get_role(515467411898761216)

    async def cog_check(self, ctx):
        return await is_subowner(ctx.author)

    @commands.command(brief='制限付きユーザーを付けます')
    async def limit(self, ctx, member: discord.Member):
        await member.edit(roles=[self.limit_role])

    @commands.command()
    async def ban(self, ctx, member_id: int, reason=None):
        embed = discord.Embed(description="<@!member_id>をBANしますか？")
        mes = await ctx.send(embed=embed)
        [self.client.loop.create_task(mes.add_reaction(i))
         for i in ("\u2705", "\u274c")]

        def check(react, usr):
            return (
                react.message.channel == mes.channel
                and usr == ctx.author
                and react.message.id == mes.id
                and react.me
            )

        reaction, user = await self.client.wait_for('reaction_add', check=check)
        if reaction.emoji == '\u2705':
            await ctx.guild.ban(discord.Object(member_id), reason=reason)
            await ctx.send("BANしました")
        else:
            await ctx.send("キャンセルしました")

    @commands.command()
    async def event_toggle(self, ctx: commands.Context):
        for _id in event_channel:
            channel: discord.abc.GuildChannel = self.client.get_channel(_id)
            if channel is None:
                continue
            overwrite = channel.overwrites_for(self.normal_user)
            overwrite.update(read_messages=not overwrite.read_messages)
            await channel.set_permissions(self.normal_user, )