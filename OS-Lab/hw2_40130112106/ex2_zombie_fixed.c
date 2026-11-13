/* نسخه‌ی اصلاح‌شده‌ی تمرین ۲: Parent پایان Child را با waitpid() جمع‌آوری می‌کند. */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    pid_t pid = fork();

    if (pid < 0) {
        perror("fork");
        return 1;
    }
    else if (pid == 0) {
        printf("Child (PID=%d): I'm done.\n", getpid());
        exit(0);
    }
    else {
        int status;
        pid_t done = waitpid(pid, &status, 0);   /* همان wait(&status) برای یک Child مشخص */

        if (done < 0) {
            perror("waitpid");
            return 1;
        }
        if (WIFEXITED(status))
            printf("Parent: Collected child %d (exit code %d).\n",
                   done, WEXITSTATUS(status));

        printf("Parent: Sleeping 10 seconds...\n");
        sleep(10);
        printf("Parent: Exiting after wait.\n");
    }

    return 0;
}
