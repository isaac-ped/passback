#include <unistd.h>
#include <stdio.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <signal.h>

#define SECRET "\x42h2s2o\x42"

// Remove the secret if present, point buff_out to new start of string (shifted due to removal)
// Return pointer to post-secret (or null if it wasn't there)
char *extract_secret(char *buff_in, size_t buff_len, char *secret, size_t secret_len, char **buff_out) {
    if (buff_len < secret_len) {
        return NULL;
    }
    int max_start = buff_len - secret_len;
    char *secret_start = NULL;
    for (int i=0; i <= max_start; i++) {
        if (memcmp(&buff_in[i], SECRET, secret_len) == 0) {
            secret_start = &buff_in[i];
            break;
        }
    }
    // Nothing found
    if (!secret_start) {
        return NULL;
    }
    // Shift everything in the buffer pre-secret over by the secret length
    memmove(buff_in + secret_len, buff_in, (secret_start - buff_in));
    *buff_out = (secret_start + secret_len);
    return (buff_in + secret_len);
}

int main(int argc, char **argv) {

    char secret[strlen(SECRET)+1];
    int secret_len = sprintf(secret, SECRET);

    // Shift the arguments for passing through to exec
    for (int i=0; i < argc-1; i++){
        argv[i] = argv[i+1];
    }
    argv[argc-1] = NULL;

    // Create a pipe through which stdout will be monitored
    int channel[2];
    if (pipe(channel)) {
        perror("pipe");
        return 1;
    }

    pid_t child = fork();
    if (child == 0) {
        // child process if here
        // the fd at the write end of the pipe replaces stdout in this process
        dup2(channel[1], fileno(stdout));
        // Execute what was passed in
        execvp(argv[0], argv);
    }

    pid_t monitor_child = fork();
    if (monitor_child != 0) {
        // Second parent if here

        // I struggle with timeouts.
        // This monitors the first child process,
        // and kills the second one when the first exits
        int wstatus;
        if (waitpid(child, &wstatus, 0)) {
            kill(monitor_child, SIGINT);
            exit(WEXITSTATUS(wstatus));
        }
    }

    // Buffer stdout into this. Bigger might mean better? Idk.
    char bigbuff[16384];

    // Reading from this fd (pipe read end)
    int fd = channel[0];

    // Get a set of flags so it can be shifted to nonblocking easily
    int blocking_flags = fcntl(fd, F_GETFL, 0);
    int nonblock_flags = blocking_flags | O_NONBLOCK;

    // Log to this file (For now)
    FILE *log = fopen("test.txt", "w");
    fprintf(log, "starting\n");
    fflush(log);

    while (1) {
        fflush(log);
        // Set the fd to blocking
        fcntl(fd, F_SETFL, blocking_flags);

        char *buff = bigbuff;
        // Read the first 1024 characters that can be read on the next write
        ssize_t n = read(fd, buff, 1024);
        char *buff_end = buff + n;

        char *secret_end = extract_secret(buff, n, secret, secret_len, &buff);
        if (secret_end) {
            fprintf(log, "SSHHHH\n");
            int msg_size = 0;
            char *size_end = secret_end;
            // No more than 999 length msg
            // TOOO: if it's not, this breaks probably
            for (; size_end < (secret_end + 3) && size_end < buff_end; size_end++) {
                char c = *size_end;
                if (c == ' ') {
                    break;
                }
                if (c <= '9' && c >= '0') {
                    msg_size *= 10;
                    msg_size += (int)(c-'0');
                } else {
                    fprintf(log, ":(. Exiting because of %c...", c);
                }
            }
            fprintf(log, "Size: %d\n", msg_size);

            char *msg_end = size_end + msg_size;
            if (msg_end > buff_end) {
                // TODO: Give up I guess...
                exit(1);
            }
            /*
            while (end_idx > (buff_end - buff)) {
                fprintf(log, "%.*s", (int)(n - buffidx), &buff[buffidx]);
                int new_n = read(fd, bigbuff, sizeof(bigbuff));
                if (new_n <= 0) {
                    printf("Ugh...\n");
                    exit(1);
                }
                end_idx = (end_idx - n);
                buffidx = 0;
                n = new_n;
            }
            */
            fprintf(log, "%.*s\n", msg_size, size_end);
            fflush(log);

            if (secret_end - buff) {
                // If there was a prefix
                // Remove the message from the buffer
                int shiftlen = (secret_end - buff);
                memmove(msg_end - shiftlen, buff, msg_end - buff);
                buff = msg_end - shiftlen;
            } else {
                buff = msg_end;
            }
        }
        if (n < 0) {
            printf("Exiting monitor\n");
            exit(1);
        }
        write(fileno(stdout), buff, (int)(buff_end - buff));
        fcntl(fd, F_SETFL, nonblock_flags);
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
    }
}
