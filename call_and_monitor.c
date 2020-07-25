#include <unistd.h>
#include <stdio.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <signal.h>

#define SECRET "\x42h2s2o\x42"
#define CALLEE "./monitor_trigger"

// Like strnstr but removing the null-termination requirement
char *strsearch(char *haystack, ssize_t hay_len, char *needle, size_t needle_len) {
    if (hay_len < needle_len) {
        return NULL;
    }
    int max_start = hay_len - needle_len;
    for (int i=0; i <= max_start; i++) {
        if (memcmp(&haystack[i], needle, needle_len) == 0) {
            return haystack + i;
        }
    }
    return NULL;
}

/**
 * Put an integer of at most 'str_len' characters into *out from str
 * (assuming it is followed by a space)
 * Return the post-space charachter pointer
 */
char *intsearch(char *str, size_t str_len, int *out) {
    int size = 0;
    for (; str < (str + str_len); str++) {
        char c = *str;
        if (c == ' ') {
            *out = size;
            return str+1;
        }
        if (c <= '9' && c >= '0') {
            size *= 10;
            size += (int)(c - '0');
        } else {
            fprintf(stderr, "Bad character %c in size string\n", c);
            return NULL;
        }
    }
    return NULL;
}


/**
 * Return a buffer containing `msg_len` characters from `msg` and (if necessary)
 * read from `fd` to get enough characters
 */
char *msgsearch(char *str, size_t str_len, int fd, size_t msg_len, char *buff, size_t buff_len) {
    if (msg_len >= buff_len) {
        fprintf(stderr, "Something went wrong! %zu is too big of a message\n", msg_len);
        return NULL;
    }
    if (str_len >= msg_len) {
        return str;
    }
    memcpy(buff, str, str_len);
    char *buff_end = str + str_len;
    size_t n_left = msg_len - str_len;
    while ( n_left > 0) {
        ssize_t rtn = read(fd, buff_end, n_left);
        if (rtn <= 0) {
            perror("Couldn't read!");
            return NULL;
        }
        n_left -= rtn;
        buff_end += rtn;
    }
    return buff;
}

int start_callee(char *message, size_t msg_len) {
    int channel[2];
    if (pipe(channel)) {
        perror("callee pipe creation");
        return 1;
    }
    pid_t child = fork();
    if (child == 0) {
        // Child process: write everything from parent to stdin
        dup2(channel[0], fileno(stdin));
        // Have to close the write end in the child process
        // (This got me my last job)
        close(channel[1]);
        char *argv[] = {CALLEE, NULL};
        execv(CALLEE, argv);
        perror("Execvp");
        /// REALLLY shouldn't get here...
        exit(1);
    }

    while (msg_len > 0) {
        ssize_t rtn = write(channel[1], message, msg_len);
        if (rtn < 0) {
            perror("Writing to callee pipe");
            return 1;
        }
        msg_len -= rtn;
    }
    close(channel[1]);
    return 0;
}

// I don't want to think about if this is big enough so I just made it too big
static char msg_buff[16384];

ssize_t search_and_send_message(char *buff, size_t buff_len, int fd) {
    int msg_size = -1;
    char *size_end = intsearch(buff, 4, &msg_size);
    if (size_end == NULL) {
        fprintf(stderr, "Could not read size from message\n");
        return -1;
    }

    size_t remaining_len = buff_len - (size_end - buff);
    char *message = msgsearch(size_end, remaining_len, fd, msg_size, msg_buff, sizeof(msg_buff));
    if (!message) {
        fprintf(stderr, "Error reading message itself\n");
        return -1;
    }

    int rtn = start_callee(message, msg_size);
    if (rtn < 0) {
        fprintf(stderr, "Error starting subprocess\n");
        return -1;
    }

    // If the message is in a new buffer, there is no original buffer left
    if (message == msg_buff) {
        return 0;
    }

    // Otherwise, return the number of unused bytes
    char *msg_end = message + msg_size;
    size_t total_size = msg_end - buff;
    return buff_len - total_size;
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
    close(channel[1]);

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

        // Read the first 1024 characters that can be read in one go
        // (if the secret isn't in the first kb, it will be missed. Oh well)
        ssize_t n = read(fd, buff, 1024);
        char *buff_end = buff + n;

        // The '-4' is to ensure there is space for the length after
        char *secret_start = strsearch(buff, n - 4, secret, secret_len);
        if (secret_start) {
            fprintf(log, "Got secret string\n");
            char *secret_end = secret_start + secret_len;
            // Find the message and send it to subprocess
            ssize_t remaining = search_and_send_message(secret_end, (buff_end - secret_end), fd);

            if (remaining < 0) {
                fprintf(stderr, "Error in search & send\n");
                continue;
            }

            char *msg_end = buff_end - remaining;
            size_t prefix_size = secret_start - buff;
            fprintf(log, "%zd bytes remaining, %zu size prefix \n", remaining, prefix_size);
            if (remaining > 0 && prefix_size > 0) {
                // In this case, we copy the prefix to right before the remaining bytes
                memmove(msg_end - prefix_size, buff, prefix_size);
                buff = msg_end - prefix_size;
                n = remaining + prefix_size;
            } else if (remaining > 0) {
                // In this case there is no prefix, just point the buffer to the remaining bytes
                buff = msg_end;
                n = remaining;
            } else if (prefix_size > 0) {
                // In this case, there was a prefix but no remainder
                // Just change the length to write
                n = prefix_size;
            } else {
                // Nothing else!
                n = 0;
            }
        }
        if (n < 0) {
            printf("Exiting monitor\n");
            exit(1);
        }

        // Read anything else in the buffer until nothing is left
        write(fileno(stdout), buff, n);
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
