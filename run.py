import asyncio
import os
from new_skyline2 import SKYLINE
token = os.environ['token']
while True:
    loop = asyncio.new_event_loop()
    client = SKYLINE(loop=loop)


    async def main():
        await client.start(token)
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
