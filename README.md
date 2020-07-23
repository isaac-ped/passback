#Usage

```shell
$ ./call_and_monitor bash
$ printf '\x42h2s2o\x4210 abcdefghijklmno'
jklmno
$ printf '\x42h2s2o\x4210 abcdefghi'
$
$ printf 'ABC\x42h2s2o\x424 HI!DEF'
ABCDEF
```

In other window:
```shell
$ tail -f test.txt
starting
SSHHHH
Size: 10
 abcdefghi
SSHHHH
Size: 10
 abcdefghi
Size: 4
 HI!
```
