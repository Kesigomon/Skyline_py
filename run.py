import asyncio
import datetime
import os

import discord

from new_skyline2 import SKYLINE

token = os.environ['token']
loop = asyncio.get_event_loop()
client = SKYLINE(loop=loop, intents=discord.Intents.all())


async def main():
    now = datetime.datetime.utcnow()
    endtime = now.replace(hour=17, minute=1, second=0, microsecond=0)
    if now >= endtime:
        endtime += datetime.timedelta(days=1)
    await asyncio.wait([client.start(token)], timeout=(endtime - now).total_seconds())
    await client.close()
    all_tasks = [t for t in asyncio.all_tasks(loop=loop) if t != main_task]
    while all_tasks:
        done, pending = await asyncio.wait(all_tasks, timeout=5)
        print(pending)
        [t.cancel() for t in pending]
        if not pending:
            break

main_task = loop.create_task(main())
loop.run_until_complete(main_task)
loop.close()
