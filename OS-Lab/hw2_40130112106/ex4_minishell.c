#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

#define MAX_CMD  256
#define MAX_ARGS 64

static void reap_background(void) {
    int status;
    pid_t pid;

    while ((pid = waitpid(-1, &status, WNOHANG)) > 0)
        printf("[done] background PID %d\n", pid);
}

int main(void) {
    char input[MAX_CMD];
    char *args[MAX_ARGS];

    while (1) {
        reap_background();

        printf("mysh> ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) {
            printf("\nExiting.\n");
            break;
        }
        input[strcspn(input, "\n")] = '\0';

        int argc = 0;
        char *token = strtok(input, " \t");
        while (token != NULL && argc < MAX_ARGS - 1) {
            args[argc++] = token;
            token = strtok(NULL, " \t");
        }
        args[argc] = NULL;

        if (argc == 0)
            continue;

        int background = 0;
        if (strcmp(args[argc - 1], "&") == 0) {
            background = 1;
            args[--argc] = NULL;
        } else {
            size_t len = strlen(args[argc - 1]);
            if (len > 1 && args[argc - 1][len - 1] == '&') {
                background = 1;
                args[argc - 1][len - 1] = '\0';
            }
        }

        if (argc == 0)
            continue;

        if (strcmp(args[0], "exit") == 0)
            break;

        if (strcmp(args[0], "cd") == 0) {
            const char *dir = args[1] ? args[1] : getenv("HOME");
            if (dir == NULL)
                dir = "/";
            if (chdir(dir) != 0)
                perror("cd");
            continue;
        }

        pid_t pid = fork();

        if (pid < 0) {
            perror("fork");
            continue;
        }
        else if (pid == 0) {
            execvp(args[0], args);
            perror("execvp");
            _exit(127);
        }
        else if (background) {
            printf("[bg] started PID %d\n", pid);
        }
        else {
            if (waitpid(pid, NULL, 0) < 0)
                perror("waitpid");
        }
    }

    return 0;
}
