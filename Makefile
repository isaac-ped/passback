all: just_call call_and_monitor

%: %.c
	gcc -Wall -o $@ $^
