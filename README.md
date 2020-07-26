# Usage

Monitors stdout of any process (including ssh!) and sends back to a monitoring program.

Think: get your terminal on your local machine to open a new window
and ssh to the same directory as you are in on your remote machine!

Or: Copy a file to your local machine from the remote machine

```shell
$ printf '
> Hey there... There is a hidden message on the next line
> \xDE\xAD\xBE\xEF 60 It has exactly 60 characters in it but can contain anything
> This line is back to normal
> '

Hey there... There is a hidden message on the next line
This line is back to normal

# Meanwhile, the hidden string is passed to `monitor_dispatch`
```


# New stuff:

Define your library of functions in python:
```python
import os
from iterm2_local_commands import new_window, new_split
from monitorlib import resolve

@resolve(contents='$(cat)')
def lpbcopy(contents):
    os.system(f"echo '{contents}' | pbcopy")
```

Generate the aliases from the function definitions:
```shell
$ ./monitor_dispatch --aliases

function lpbcopy() { rm -f /tmp/${USER}_pb; echo -n "lpbcopy," > /tmp/${USER}_pb; cat > /tmp/${USER}_pbvar <<< $(cat); echo -n "contents,$(wc -c < /tmp/${USER}_pbvar| awk '{$1=$1};1')," >> /tmp/${USER}_pb; cat /tmp/${USER}_pbvar >> /tmp/${USER}_pb; printf '\xDE\xAD\xBE\xEF %d ' $(wc -c < /tmp/${USER}_pb) && cat /tmp/${USER}_pb; }

function nwhere() { rm -f /tmp/${USER}_pb; echo -n "nwhere," > /tmp/${USER}_pb; cat > /tmp/${USER}_pbvar <<< $(pwd); echo -n "directory,$(wc -c < /tmp/${USER}_pbvar| awk '{$1=$1};1')," >> /tmp/${USER}_pb; cat /tmp/${USER}_pbvar >> /tmp/${USER}_pb; cat > /tmp/${USER}_pbvar <<< ${SHELL}; echo -n "shell,$(wc -c < /tmp/${USER}_pbvar| awk '{$1=$1};1')," >> /tmp/${USER}_pb; cat /tmp/${USER}_pbvar >> /tmp/${USER}_pb; cat > /tmp/${USER}_pbvar <<< ${SSHNAME:-$HOSTNAME}; echo -n "host,$(wc -c < /tmp/${USER}_pbvar| awk '{$1=$1};1')," >> /tmp/${USER}_pb; cat /tmp/${USER}_pbvar >> /tmp/${USER}_pb; printf '\xDE\xAD\xBE\xEF %d ' $(wc -c < /tmp/${USER}_pb) && cat /tmp/${USER}_pb; }

function nvshere() { rm -f /tmp/${USER}_pb; echo -n "nvshere," > /tmp/${USER}_pb; cat > /tmp/${USER}_pbvar <<< $(pwd); echo -n "directory,$(wc -c < /tmp/${USER}_pbvar| awk '{$1=$1};1')," >> /tmp/${USER}_pb; cat /tmp/${USER}_pbvar >> /tmp/${USER}_pb; cat > /tmp/${USER}_pbvar <<< ${SHELL}; echo -n "shell,$(wc -c < /tmp/${USER}_pbvar| awk '{$1=$1};1')," >> /tmp/${USER}_pb; cat /tmp/${USER}_pbvar >> /tmp/${USER}_pb; cat > /tmp/${USER}_pbvar <<< ${SSHNAME:-$HOSTNAME}; echo -n "host,$(wc -c < /tmp/${USER}_pbvar| awk '{$1=$1};1')," >> /tmp/${USER}_pb; cat /tmp/${USER}_pbvar >> /tmp/${USER}_pb; printf '\xDE\xAD\xBE\xEF %d ' $(wc -c < /tmp/${USER}_pb) && cat /tmp/${USER}_pb; }
```

Once launched, instantiate the aliases and you can use them!
```shell
$ ./call_and_monitor bash
$ source (./monitor_dispatch --aliases)
$ echo "This goes to my local clipboard even from a remote machine. YAYY" | lpbcopy
```


# FIXME

Somewhere newlines are changing format from \n -> \r\n. I don't know when it's happening!

It's throwing off charachter counts :(
