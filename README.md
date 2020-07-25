#Usage

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
