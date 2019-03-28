import os
from new_skyline2 import SKYLINE
token = os.environ['token']
client = SKYLINE()
client.run(token)