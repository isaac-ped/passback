#include <unistd.h>
#include <stdio.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <sys/wait.h>

char SECRET[7];

int main(int argc, char **argv) {
    snprintf(SECRET, 7, "LOL\b\b\b");
    int secretlen = 6;
    for (int i=0; i < argc-1; i++){
        argv[i] = argv[i+1];
    }
    argv[argc-1] = NULL;

    int channel[2];
    if (pipe(channel)) {
        perror("pipe");
        return 1;
    }

    pid_t child = fork();
    if (child == 0) { // child process
        dup2(channel[1], fileno(stdout));
        // Execute what was passed in
        execvp(argv[0], argv);
    }
    pid_t monitor_child = fork();
    if (monitor_child != 0) {
        int wstatus;
        if (waitpid(child, &wstatus, 0)) {
            kill(monitor_child, SIGINT);
            exit(WEXITSTATUS(wstatus));
        }
    }

    char bigbuff[16384];

    int fd = channel[0];
    int start_flags = fcntl(fd, F_GETFL, 0);
    int nb_flags = start_flags | O_NONBLOCK;

    FILE *log = fopen("test.txt", "w");
    fprintf(log, "starting\n");
    fflush(log);

    while (1) {
        fcntl(fd, F_SETFL, start_flags);
        ssize_t n = read(fd, bigbuff, sizeof(bigbuff));
        int secret_end = 0;
        if ( n >= secretlen ) {
            int maxstart = n - secretlen;
            for (int i=0; i <= maxstart; i++) {
                if (memcmp(&bigbuff[i], SECRET, secretlen) == 0) {
                    secret_end = i + secretlen;
                    break;
                }
            }
        }
        fprintf(log, "something\n");
        fflush(log);

        if (secret_end > 0) {
            fprintf(log, "sshshhhh\n");
            int secret_size = 0;
            int size_end = secret_end;
            for (; size_end < (secret_end + 3) && size_end < n; size_end++) {
                char c = bigbuff[size_end];
                fprintf(log, "sizechar: %c\n", c);
                if ( c <= '9' && c >= '0' ) {
                    secret_size *= 10;
                    secret_size += (int)(c - '0');
                } else {
                    size_end+=1;
                    break;
                }
                fprintf(log, "yep\n");
            }
            fprintf(log, "Size: %d\n", secret_size);
            if (secret_size > 1000) {
                printf("Nope too big: %d\n", secret_size);
                exit(1);
            }

            int end_idx = size_end + secret_size;
            int buffidx = size_end;
            while (end_idx > n) {
                fprintf(log, "%.*s", (int)(n - buffidx), &bigbuff[buffidx]);
                int new_n = read(fd, bigbuff, sizeof(bigbuff));
                if (new_n <= 0) {
                    printf("Ugh...\n");
                    exit(1);
                }
                end_idx = (end_idx - n);
                buffidx = 0;
                n = new_n;
            }
            fprintf(log, "%.*s\n", end_idx - buffidx, &bigbuff[buffidx]);
            fflush(log);
            secret_end = end_idx;
            fprintf(log, "remaining: %zd %.*s\n", n - secret_end, (int)(n - secret_end), &bigbuff[secret_end]);
        }
        if (n < 0) {
            printf("Exiting monitor\n");
            exit(1);
        }
        write(fileno(stdout), &bigbuff[secret_end], n - secret_end);
        fcntl(fd, F_SETFL, nb_flags);
        while (1) {
            ssize_t n = read(fd, bigbuff, sizeof(bigbuff));
            if (n == -1) {
                if (errno == EAGAIN) {
                    break;
                } else {
                    perror("Read nonblock");
                    exit(1);
                }
            }
            write(fileno(stdout), bigbuff, n);
        }
        fcntl(fd, F_SETFL, start_flags);

    }
}
