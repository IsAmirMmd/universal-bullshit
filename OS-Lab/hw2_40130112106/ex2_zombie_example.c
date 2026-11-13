#include <stdio.h>
#include <unistd.h>

int main() {
    pid_t pid = fork();

    if (pid == 0) {
        printf("Child: I'm done.\n");
    }
    else {
        printf("Parent: Sleeping 10 seconds...\n");
        sleep(10);
        printf("Parent: Exiting without wait.\n");
    }

    return 0;
}
