import discord
from discord.ext import commands
import datetime
import asyncio
from .general import ZATSUDAN_FORUM_ID, join_message, voice_text


class Events(commands.Cog):
    __slots__ = ('client', 'name', 'DJ', 'beginner_chat',
                 'Normal_User', 'OverLevel10',
                 'webhook_site', 'webhook_app', 'webhook_runner',
                 'saves', 'new_member')

    def __init__(self, client, name=None):
        self.client: commands.Bot = client
        self.name = name if name is not None else type(self).__name__

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild: discord.Guild = self.client.get_guild(ZATSUDAN_FORUM_ID)
        self.DJ = self.guild.get_role(515467441959337984)
        # self.beginner_chat = client.get_channel(524540064995213312)
        self.Normal_User = self.guild.get_role(515467427459629056)
        self.OverLevel10 = self.guild.get_role(515467423101747200)
        self.new_member = self.guild.get_channel(515467586679603202)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild == self.guild:
            if 'discord.gg' in member.display_name:
                await member.ban(reason='招待リンクの名前のため、BAN', delete_message_days=1)
            else:
                content = join_message.format(member.mention, member.guild.name)
                await self.new_member.send(content)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        def check(log):
            return (
                log.target.id == member.id
                and abs(now - log.created_at) <= datetime.timedelta(seconds=1)
            )
        now = datetime.datetime.utcnow()
        await asyncio.sleep(0.5)
        audit_logs = await member.guild.audit_logs(action=discord.AuditLogAction.kick).flatten()
        audit_logs.extend(await member.guild.audit_logs(action=discord.AuditLogAction.ban).flatten())
        filtered = list(filter(check, audit_logs))
        if not filtered:
            try:
                zatsudan_forum = member.guild.get_channel(515467559051591681)
            except (StopIteration, IndexError):
                pass
            else:
                name = member.display_name
                embed = discord.Embed(
                    title='{0}さんが退出しました。'.format(name),
                    colour=0x2E2EFE,
                    description='{0}さん、ご利用ありがとうございました。\nこのサーバーの現在の人数は{1}人です'
                    .format(name, member.guild.member_count)
                )
                embed.set_thumbnail(url=member.avatar_url)
                await zatsudan_forum.send(embed=embed)
                content = (
                    '{0}が退出しました。'
                    'ご利用ありがとうございました。'
                ).format(member)
                await self.new_member.send(content)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        voice_text_pair = voice_text
        if (
            after.channel is not None
            and (before.channel is None
                 or before.channel != after.channel)
            and str(after.channel.id) in voice_text_pair
        ):
            text_channel = self.client.get_channel(
                voice_text_pair[str(after.channel.id)])
            embed = discord.Embed(
                title='ボイスチャンネル入室通知',
                description='{0}が、入室しました。'.format(member.mention),
                colour=0x00af00
            )
            await text_channel.send(embed=embed, delete_after=180)
            if after.channel.id == 515467651691315220:  # 音楽鑑賞VCの場合
                await member.add_roles(self.DJ)  # DJ役職を付与
        if (
            before.channel is not None
            and (after.channel is None
                 or before.channel != after.channel)
            and str(before.channel.id) in voice_text_pair
        ):
            text_channel = self.client.get_channel(
                voice_text_pair[str(before.channel.id)])
            embed = discord.Embed(
                title='ボイスチャンネル退出通知',
                description='{0}が、退出しました。'.format(member.mention),
                colour=0xaf0000
            )
            await text_channel.send(embed=embed, delete_after=180)
            if before.channel.id == 515467651691315220:  # 音楽鑑賞VCの場合
                await member.remove_roles(self.DJ)  # DJ役職を解除
