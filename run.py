from new_skiline import client
with open('token.txt') as f:
    client.run(f.read())