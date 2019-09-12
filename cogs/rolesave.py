import json
import io

import discord
from discord.ext import commands


class Role_save(commands.Cog):

    __slots__ = ('client', 'channel', 'guild', 'cache', 'message')

    def __init__(self, client, name=None):
        self.client = client
        self.name = name if name is not None else type(self).__name__
        self.cache = dict()

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel: discord.TextChannel \
            = self.client.get_channel(531377173869625345)
        self.guild: discord.Guild = self.channel.guild

        def func1(m: discord.Message):
            return(
                m.author == self.client.user
                and m.attachments
                and m.attachments[0].filename == 'role.json'
            )

        data = io.BytesIO()
        async for message in self.channel.history().filter(func1):
            await message.attachments[0].save(data)
            self.message = message
            break
        try:
            self.cache: dict = json.loads(data.read().decode('UTF-8'))
        except Exception:
            self.cache = {}
        self.cache.update(
            {str(m.id): [r.id for r in m.roles if not r.is_default()]
            for m in self.guild.members}
        )
        await self._save()
        print('{0}:role_save起動しました'.format(self.client.user))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles != after.roles:
            self.cache[str(after.id)] = [r.id for r in after.roles if not r.is_default()]

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._save()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if str(member.id) in self.cache:
            role_ids = self.cache[str(member.id)]
            [self.client.loop.create_task(member.add_roles(role))
             for role in [self.guild.get_role(i) for i in role_ids]
             if role is not None]

    async def _save(self):
        Data = discord.File(io.StringIO(json.dumps(self.cache, indent=4, sort_keys=True)), filename='role.json')
        self.message = await self.channel.send(file=Data)

    @property
    def converted_cache(self):
        return {self.client.get_user(int(key)): [self.guild.get_role(i) for i in value]
                for key, value in self.cache.items()}
