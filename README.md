# Usage

Monitors stdout of any process (including ssh!) and sends back to a monitoring program.

Think: get your terminal on your local machine to open a new window
and ssh to the same directory as you are in on your remote machine!

Or: Copy a file to your local machine from the remote machine

```shell
$ printf '
> Hey there... There is a hidden message on the next line
> \xDE\xAD o.O \xBE\xEF 60 It has exactly 60 characters in it but can contain anything
> This line is back to normal
> '

Hey there... There is a hidden message on the next line
This line is back to normal

The program ./monitor_trigger got the following stdin:
 It has exactly 60 characters in it but can contain anything
$
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
$ ./monitor_dispatch --aliases                                                                                                                                                    [master]

_sendlocal() {
    printf "\xDE\xAD\xBE\xEF ${#1} %s" "$1";
}

function lpbcopy() { contents="$(cat)"; _sendlocal "lpbcopy,contents,${#contents},${contents}"; }
function nwhere() { directory="$(pwd)"; shell="${SHELL}"; host="${SSHNAME:-$HOSTNAME}"; _sendlocal "nwhere,directory,${#directory},${directory},shell,${#shell},${shell},host,${#host},${host}"; }
function nvshere() { directory="$(pwd)"; shell="${SHELL}"; host="${SSHNAME:-$HOSTNAME}"; _sendlocal "nvshere,directory,${#directory},${directory},shell,${#shell},${shell},host,${#host},${host}"; }
```

Once launched, instantiate the aliases and you can use them!
```shell
$ ./call_and_monitor bash
$ source (./monitor_dispatch --aliases)
$ echo "This goes to my local clipboard even from a remote machine. YAYY" | lpbcopy
```
