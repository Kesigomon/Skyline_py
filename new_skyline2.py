import asyncio
from discord.ext import commands
import cogs


class SKYLINE(commands.Bot):

    def __init__(self, **options):
        super().__init__('sk!', **options)
        cogs.cogs(self)

    async def close(self):
        try:
            futs = [self.on_close]
        except AttributeError:
            futs = []
        futs.extend(self.extra_events.get('on_close', []))
        await asyncio.wait([f() for f in futs])
        await super().close()
