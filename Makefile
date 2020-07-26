all: just_call passback

%: %.c
	gcc -Wall -o $@ $^
