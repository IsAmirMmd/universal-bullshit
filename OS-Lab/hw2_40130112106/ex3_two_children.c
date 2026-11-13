/* تمرین ۳: ایجاد دو Child بدون انتظار بین آن‌ها، سپس انتظار برای هر دو. */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    pid_t pid1, pid2;

    /* Child اول: sleep 5 */
    pid1 = fork();
    if (pid1 < 0) {
        perror("fork");
        return 1;
    }
    if (pid1 == 0) {
        execlp("sleep", "sleep", "5", NULL);
        perror("execlp sleep");
        _exit(1);
    }

    /* Child دوم: date — بلافاصله بعد از Child اول و بدون wait() */
    pid2 = fork();
    if (pid2 < 0) {
        perror("fork");
        waitpid(pid1, NULL, 0);     /* Child اول را رها نمی‌کنیم */
        return 1;
    }
    if (pid2 == 0) {
        execlp("date", "date", NULL);
        perror("execlp date");
        _exit(1);
    }

    printf("Parent (PID=%d): child1 PID=%d (sleep 5), child2 PID=%d (date)\n",
           getpid(), pid1, pid2);

    /* حالا وارد مرحله‌ی انتظار می‌شویم: دو بار wait() برای دو Child */
    for (int i = 0; i < 2; i++) {
        int status;
        pid_t done = wait(&status);

        if (done < 0) {
            perror("wait");
            break;
        }

        const char *name = (done == pid1) ? "sleep 5" : "date";

        if (WIFEXITED(status))
            printf("Parent: child PID %d (%s) finished, exit code %d\n",
                   done, name, WEXITSTATUS(status));
        else if (WIFSIGNALED(status))
            printf("Parent: child PID %d (%s) killed by signal %d\n",
                   done, name, WTERMSIG(status));
    }

    printf("Parent: both children are done.\n");
    return 0;
}
