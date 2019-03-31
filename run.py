import asyncio
import os
from new_skyline2 import SKYLINE
token = os.environ['token']
loop = asyncio.get_event_loop()
client = SKYLINE(loop=loop)


async def main():
    await client.start(token)
    await client.close()
    all_tasks = asyncio.all_tasks(loop=loop)
    while True:
        done, pending = await asyncio.wait(list(all_tasks), timeout=5)
        [t.cancel() for t in pending]
        if not pending:
            break

main_task = loop.create_task(main())
loop.run_until_complete(main_task)
loop.close()
