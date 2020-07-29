# Use:
Currently a two-stage process:

From host:
```shell
python -m flask run --port 4242
```

When sshing:
```shell
local$ ssh -R 1138:localhost:4242 my-server-name
# it actually sshes here
# Now, get the appropriate aliases:
remote$ source <(curl localhost:1138)
```
