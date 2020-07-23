#include <unistd.h>

int main(int argc, char **argv) {
    for (int i=0; i < argc-1; i++){
        argv[i] = argv[i+1];
    }
    argv[argc-1] = NULL;
    execvp(argv[0], argv);
}
