# آزمایشگاه سیستم‌عامل، جلسه‌ی دوم: فراخوانی‌های سیستمی مدیریت فرآیند

**شماره‌ی دانشجویی:** `40130112106`

**موضوع:** `fork()` • `exec()` • `wait()` / `waitpid()` • Zombie / Orphan

> کد کامل هر تمرین کنار همین فایل هم هست (`ex1_hello.c` تا `ex4_minishell.c`).
> خروجی‌ها نمونه‌ی اجرا روی Linux هستند؛ مقدار PIDها و تاریخ در هر اجرا فرق می‌کند.
>
> در این گزارش «فرآیند» معادل Process، «والد» معادل Parent و «فرزند» معادل Child به کار رفته است.

--------

=سوال ۱=

**تمرین ۱: محاسبه تعداد Processها**

در قطعه کد زیر چند بار عبارت `Hello` چاپ می‌شود؟ پاسخ خود را با رسم درخت Processها یا توضیح مرحله‌به‌مرحله استدلال کنید.

```c
#include <stdio.h>
#include <unistd.h>

int main() {
    fork();
    fork();
    printf("Hello\n");
    return 0;
}
```

=پاسخ ۱=

عبارت `Hello` **چهار بار** چاپ می‌شود.

#### استدلال

در شروع فقط یک فرآیند داریم که آن را `P` می‌نامیم. فراخوانی اول `fork()` از `P` یک فرزند به نام `C1` می‌سازد. از این لحظه دو فرآیند داریم و هر دو از خط بعد از `fork()` اول، یعنی از `fork()` دوم، ادامه می‌دهند.

هر کدام از این دو فرآیند `fork()` دوم را جداگانه اجرا می‌کنند: فرآیند `P` فرزند `C2` را می‌سازد و فرآیند `C1` هم فرزند `C3` را (که نوه‌ی `P` است). حالا چهار فرآیند داریم و هر چهار تا به `printf("Hello\n")` می‌رسند.

#### درخت فرآیندها

```
P  (والد اصلی)
├── C1   ← ساخته‌شده با fork() اول
│   └── C3   ← ساخته‌شده توسط C1 با fork() دوم
└── C2   ← ساخته‌شده توسط P با fork() دوم

هر ۴ فرآیند (P, C1, C2, C3) → printf("Hello\n")
```

| مرحله | تعداد فرآیند قبل | تعداد فرآیند بعد |
| --- | --- | --- |
| شروع برنامه | — | ۱ |
| فراخوانی اول `fork()` | ۱ | ۲ |
| فراخوانی دوم `fork()` | ۲ | ۴ |

هر `fork()` که همه‌ی فرآیندهای موجود به آن برسند، تعداد فرآیندها را دو برابر می‌کند. پس `n` فراخوانی پشت سر هم و بدون شرط، `2^n` فرآیند می‌سازد؛ اینجا `2^2 = 4`.

#### نمونه خروجی

```
$ gcc -Wall -g ex1_hello.c -o ex1_hello
$ ./ex1_hello
Hello
Hello
Hello
Hello
```

ترتیب اجرای فرآیندها بعد از `fork()` تضمین‌شده نیست. اینجا چون هر چهار خط یکسان‌اند فقط تعدادشان دیده می‌شود. گاهی prompt ترمینال وسط خروجی ظاهر می‌شود، چون `P` ممکن است زودتر از فرزندانش تمام شود و Shell فقط منتظر `P` می‌ماند.

--------

=سوال ۲=

**تمرین ۲: تشخیص و رفع Zombie**

کد زیر را اجرا کنید و در ۱۰ ثانیه‌ای که Parent در `sleep` است، در Terminal دیگری وضعیت Processها را بررسی کنید. سپس کد را طوری اصلاح کنید که Parent با `wait()` پایان Child را جمع‌آوری کند.

```c
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
```

```bash
gcc -Wall -g zombie_example.c -o zombie_example
./zombie_example

# در Terminal دیگر، هنگام اجرای برنامه:
ps aux | grep Z
```

=پاسخ ۲=

#### الف) مشاهده‌ی Zombie

خروجی ترمینال اول:

```
$ gcc -Wall -g ex2_zombie_example.c -o zombie_example
$ ./zombie_example
Parent: Sleeping 10 seconds...
Child: I'm done.
Parent: Exiting without wait.        ← بعد از ۱۰ ثانیه
```

خروجی ترمینال دوم، در همان ۱۰ ثانیه:

```
$ ps aux | grep Z
amir   4823  0.0  0.0     0    0 pts/0  Z+   21:10 0:00 [zombie_example] <defunct>
amir   4830  0.0  0.0  6480 2280 pts/1  S+   21:10 0:00 grep --color=auto Z
```

برای دیدن رابطه‌ی والد و فرزند، ستون‌های مشخصی را از `ps` خواستم:

```
$ ps -o pid,ppid,stat,cmd -C zombie_example
  PID  PPID STAT CMD
 4822  4790 S+   ./zombie_example
 4823  4822 Z+   [zombie_example] <defunct>
```

فرآیند ۴۸۲۳ همان فرزند است، چون `PPID` آن برابر شناسه‌ی والد (۴۸۲۲) است. ستون `STAT` برای آن مقدار `Z` دارد و کنار نامش `<defunct>` آمده. مقدار `VSZ` و `RSS` صفر است، یعنی فرزند تمام شده و حافظه‌ای ندارد، ولی ردیف آن در Process Table هنوز باقی است.

علت این است که فرزند زود تمام می‌شود ولی والد در `sleep(10)` است و هیچ‌وقت `wait()` یا `waitpid()` را صدا نمی‌زند. هسته‌ی سیستم‌عامل باید `exit status` فرزند را نگه دارد تا والد آن را بخواند، و تا آن موقع فرزند در حالت Zombie می‌ماند.

خط دوم خروجی `ps aux | grep Z` خود دستور `grep` است، نه یک Zombie، چون حرف `Z` در آرگومان آن هست.

وقتی والد تمام شد، فرزند Zombie به فرآیند شماره‌ی ۱ (`init` یا `systemd`) سپرده می‌شود و آن فرآیند، Zombie را جمع‌آوری می‌کند. برای همین بعد از ۱۰ ثانیه دیگر در `ps` دیده نمی‌شود. در برنامه‌ای که والدش تمام نمی‌شود، مثل یک سرور، Zombieها روی هم جمع می‌شوند و جدول فرآیندها و شناسه‌های PID را پر می‌کنند.

#### ب) نسخه‌ی اصلاح‌شده با `wait`

در این نسخه والد قبل از `sleep` با `waitpid()` منتظر پایان فرزند می‌ماند و `exit status` آن را می‌خواند. فراخوانی `waitpid()` برای یک فرزند مشخص همان کار `wait()` را می‌کند. با این کار ردیف فرزند از Process Table پاک می‌شود و Zombie ساخته نمی‌شود.

```c
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
```

اگر بخواهیم دقیقاً از `wait()` استفاده کنیم، کافی است خط `waitpid` را با `pid_t done = wait(&status);` عوض کنیم. والد فقط یک فرزند دارد، پس نتیجه فرقی نمی‌کند.

نمونه خروجی نسخه‌ی اصلاح‌شده:

```
$ gcc -Wall -g ex2_zombie_fixed.c -o zombie_fixed
$ ./zombie_fixed
Child (PID=4901): I'm done.
Parent: Collected child 4901 (exit code 0).
Parent: Sleeping 10 seconds...
Parent: Exiting after wait.
```

و در ترمینال دوم، در همان ۱۰ ثانیه:

```
$ ps aux | grep Z
amir   4910  0.0  0.0  6480 2280 pts/1  S+   21:15 0:00 grep --color=auto Z
```

این بار هیچ فرآیندی با وضعیت `Z` دیده نمی‌شود و تنها خط باقی‌مانده خود `grep` است.

| ویژگی | نسخه‌ی اصلی | نسخه‌ی اصلاح‌شده |
| --- | --- | --- |
| فراخوانی wait | ندارد | `waitpid(pid, &status, 0)` |
| وضعیت فرزند هنگام `sleep` والد | Zombie (`Z`، `<defunct>`) | کاملاً حذف شده |
| مقدار `exit status` فرزند | خوانده نمی‌شود | خوانده و چاپ می‌شود |

--------

=سوال ۳=

**تمرین ۳: اجرای همزمان چند دستور**

برنامه‌ای در C بنویسید که دو Child ایجاد کند. Child اول دستور `sleep 5` و Child دوم دستور `date` را اجرا کند. Parent باید هر دو Child را بدون انتظار بین دو `fork` ایجاد کند و سپس با `wait()` یا `waitpid()` منتظر پایان هر دو بماند. پس از پایان هر Child، پیامی شامل PID آن چاپ شود.

هدف تمرین: در این تمرین تفاوت «ایجاد ترتیبی Childها» با «منتظر ماندن بین Childها» را مشاهده می‌کنید. Parent باید هر دو Child را ابتدا ایجاد کند و بعد وارد مرحله انتظار شود.

=پاسخ ۳=

#### کد کامل

```c
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
```

#### نمونه اجرا

```
$ gcc -Wall -g ex3_two_children.c -o two_children
$ time ./two_children
Parent (PID=5210): child1 PID=5211 (sleep 5), child2 PID=5212 (date)
Fri Nov 13 21:30:12 +0330 2026
Parent: child PID 5212 (date) finished, exit code 0
Parent: child PID 5211 (sleep 5) finished, exit code 0      ← حدود ۵ ثانیه بعد
Parent: both children are done.

real    0m5.006s
```

#### توضیح

والد دو بار پشت سر هم `fork()` می‌کند و بین آن‌ها `wait()` ندارد، پس دو فرزند همزمان اجرا می‌شوند. هر فرزند با `execlp()` کد فعلی را با برنامه‌ی خودش (`sleep` یا `date`) جایگزین می‌کند. اگر `execlp()` شکست بخورد، `perror` و بعد `_exit(1)` اجرا می‌شود تا فرزند وارد ادامه‌ی کدِ والد نشود.

بعد از ساختن هر دو فرزند، والد دو بار `wait(&status)` را صدا می‌زند. هر فراخوانی شناسه‌ی اولین فرزندی را برمی‌گرداند که تمام شده، و با مقایسه‌ی آن با `pid1` و `pid2` معلوم می‌شود کدام دستور بوده است.

دستور `date` تقریباً فوری تمام می‌شود. برای همین اول شناسه‌ی فرزند دوم (۵۲۱۲) چاپ می‌شود و حدود ۵ ثانیه بعد شناسه‌ی فرزند اول (۵۲۱۱). پس ترتیب تمام شدن فرزندها به ترتیب ساخته شدنشان بستگی ندارد. کل برنامه هم حدود ۵ ثانیه طول کشید، یعنی به اندازه‌ی طولانی‌ترین فرزند، نه مجموع زمان دو فرزند.

اگر والد بعد از `fork()` اول بلافاصله `wait()` کند و بعد فرزند دوم را بسازد، `date` فقط بعد از تمام شدن `sleep 5` اجرا می‌شود و خروجی آن ۵ ثانیه دیرتر می‌آید. در آن حالت فرزندها پشت سر هم اجرا می‌شوند:

| ویژگی | ساختن هر دو فرزند و بعد wait (این تمرین) | wait بین دو fork |
| --- | --- | --- |
| نحوه‌ی اجرای فرزندها | همزمان | پشت سر هم |
| زمان چاپ خروجی `date` | بلافاصله | بعد از ۵ ثانیه |
| اولین فرزندی که تمام می‌شود | `date` | `sleep 5` |
| کل زمان اجرا | حدود ۵ ثانیه | حدود ۵ ثانیه به‌علاوه‌ی زمان `date` |

--------

=سوال ۴=

**تمرین ۴: تکمیل minishell ساده**

برنامه‌ی minishell بخش ۷ را به گونه‌ای توسعه دهید که دو قابلیت زیر را داشته باشد:

- دستور `cd <directory>` را در خود Shell و با `chdir()` اجرا کند؛ `cd` نباید در Child اجرا شود، زیرا تغییر directory در Child روی Parent اثر نمی‌گذارد.
- اگر command با `&` تمام شد، مانند `sleep 10 &`، Parent منتظر Child نماند و بلافاصله prompt بعدی را نمایش دهد. `&` باید از آرایه‌ی آرگومان‌های ارسالی به `execvp()` حذف شود.

```
mysh> cd /tmp
mysh> pwd
mysh> sleep 10 &
mysh> echo shell-is-ready
```

همچنین توضیح دهید چگونه `&` را تشخیص داده و از `argv` حذف کرده‌اید.

=پاسخ ۴=

#### کد کامل

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

#define MAX_CMD  256
#define MAX_ARGS 64

/* جمع‌آوری Childهای Background که تمام شده‌اند، بدون block شدن (جلوگیری از Zombie) */
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

        /* شکستن ورودی به آرگومان‌ها */
        int argc = 0;
        char *token = strtok(input, " \t");
        while (token != NULL && argc < MAX_ARGS - 1) {
            args[argc++] = token;
            token = strtok(NULL, " \t");
        }
        args[argc] = NULL;

        if (argc == 0)
            continue;

        /* تشخیص & در انتهای command و حذف آن از argv */
        int background = 0;
        if (strcmp(args[argc - 1], "&") == 0) {          /* حالت: sleep 10 & */
            background = 1;
            args[--argc] = NULL;
        } else {                                          /* حالت: sleep 10& */
            size_t len = strlen(args[argc - 1]);
            if (len > 1 && args[argc - 1][len - 1] == '&') {
                background = 1;
                args[argc - 1][len - 1] = '\0';
            }
        }

        if (argc == 0)          /* ورودی فقط «&» بوده */
            continue;

        /* دستورات داخلی (built-in) که باید در خود Shell اجرا شوند */
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

        /* دستورات خارجی: fork + execvp */
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
            printf("[bg] started PID %d\n", pid);  /* منتظر نمی‌مانیم */
        }
        else {
            if (waitpid(pid, NULL, 0) < 0)          /* فقط همین Child، نه Childهای Background */
                perror("waitpid");
        }
    }

    return 0;
}
```

#### نمونه اجرا

```
$ gcc -Wall -g ex4_minishell.c -o minishell
$ ./minishell
mysh> pwd
/home/amir/os-lab
mysh> cd /tmp
mysh> pwd
/tmp
mysh> sleep 10 &
[bg] started PID 6120
mysh> echo shell-is-ready
shell-is-ready
mysh> cd /not-exist
cd: No such file or directory
mysh> cd
mysh> pwd
/home/amir
mysh>                                  ← بعد از ۱۰ ثانیه Enter زده شد
[done] background PID 6120
mysh> exit
```

بعد از `cd /tmp`، دستور `pwd` که در یک فرزند اجرا می‌شود مسیر `/tmp` را نشان می‌دهد. یعنی directory خود Shell عوض شده و فرزندهای بعدی آن را به ارث برده‌اند. بعد از `sleep 10 &` هم prompt بلافاصله برمی‌گردد و `echo shell-is-ready` بدون انتظار ۱۰ ثانیه‌ای اجرا می‌شود.

#### پیاده‌سازی `cd`

دستور `cd` یک دستور داخلی (built-in) است. قبل از `fork()` بررسی می‌شود که `args[0]` برابر `"cd"` باشد. اگر باشد، `chdir(args[1])` در خود فرآیند Shell اجرا می‌شود و برنامه با `continue` به prompt بعدی می‌رود، بدون اینکه فرزندی ساخته شود.

دلیلش این است که هر فرآیند current working directory مخصوص خودش را دارد. اگر `cd` در فرزند اجرا شود، فقط directory همان فرزند عوض می‌شود و فرزند هم بلافاصله تمام می‌شود؛ Shell در directory قبلی می‌ماند. وقتی `chdir()` در خود Shell اجرا شود، هر فرزندی که بعداً با `fork()` ساخته می‌شود directory جدید را به ارث می‌برد.

اگر `cd` بدون آرگومان بیاید، Shell به مسیر `$HOME` می‌رود. اگر `chdir()` شکست بخورد، مثلاً چون directory وجود ندارد، پیام خطا با `perror("cd")` چاپ می‌شود و Shell به کارش ادامه می‌دهد. دستور `exit` هم به همین دلیل built-in است و قبل از `fork()` بررسی می‌شود.

#### تشخیص و حذف `&` از `argv`

ورودی اول با `strtok()` به آرگومان‌ها شکسته می‌شود و در آرایه‌ی `args[]` قرار می‌گیرد؛ متغیر `argc` تعداد آن‌ها را نگه می‌دارد. بعد آخرین آرگومان، یعنی `args[argc - 1]`، بررسی می‌شود و دو حالت دارد:

1. وقتی آخرین آرگومان دقیقاً `"&"` است (مثل `sleep 10 &`)، متغیر `background` برابر ۱ می‌شود و دستور `args[--argc] = NULL` آن خانه را خالی می‌کند. به این ترتیب `&` از آرایه حذف می‌شود و آرایه همچنان با `NULL` تمام می‌شود، همان‌طور که `execvp()` لازم دارد.
2. وقتی `&` به آخر آرگومان چسبیده است (مثل `sleep 10&`)، کاراکتر آخر آن رشته با `'\0'` جایگزین می‌شود و `"10&"` به `"10"` تبدیل می‌شود.

در هر دو حالت `execvp()` آرایه‌ی `{"sleep", "10", NULL}` را دریافت می‌کند. اگر `&` حذف نمی‌شد، برنامه‌ی `sleep` آن را آرگومان نامعتبر می‌دید و خطا می‌داد.

بعد از `fork()`، اگر `background` برابر ۱ باشد والد `waitpid()` را صدا نمی‌زند؛ فقط شناسه‌ی فرزند را چاپ می‌کند و به prompt برمی‌گردد. برای دستورهای معمولی (foreground) از `waitpid(pid, NULL, 0)` استفاده شده تا Shell فقط منتظر همان فرزند بماند. اگر از `wait(NULL)` استفاده می‌شد، تمام شدن یک فرزند پس‌زمینه ممکن بود با تمام شدن دستور فعلی اشتباه گرفته شود.

#### جلوگیری از Zombie برای فرزندهای Background

چون Shell منتظر فرزندهای پس‌زمینه نمی‌ماند، این فرزندها بعد از تمام شدن Zombie می‌شوند. تابع `reap_background()` قبل از نمایش هر prompt اجرا می‌شود و با `waitpid(-1, &status, WNOHANG)` همه‌ی فرزندهای تمام‌شده را جمع‌آوری می‌کند. گزینه‌ی `WNOHANG` باعث می‌شود اگر هیچ فرزندی تمام نشده باشد، فراخوانی فوراً مقدار ۰ برگرداند و Shell متوقف نشود.

--------

=سوال ۵=

**نتیجه‌گیری:** مهم‌ترین چالش‌های این جلسه و راه‌حل‌هایی که برای آن‌ها پیدا کرده‌اید.

=پاسخ ۵=

سه فراخوانی این جلسه با هم یک چرخه می‌سازند. `fork()` از فرآیند فعلی یک کپی می‌سازد و مقدار برگشتی‌اش (۰ در فرزند و شناسه‌ی فرزند در والد) مسیر اجرای این دو را از هم جدا می‌کند. `exec()` برنامه‌ی داخل فرزند را با برنامه‌ی دیگری جایگزین می‌کند ولی شناسه‌ی فرآیند را عوض نمی‌کند. `wait()` و `waitpid()` به والد اجازه می‌دهند منتظر پایان فرزند بماند و `exit status` آن را بخواند. minishell تمرین ۴ دقیقاً از همین سه فراخوانی ساخته شده است.

اولین چالش، شمردن فرآیندها بعد از چند `fork()` پشت سر هم بود. رسم درخت فرآیندها مسئله را روشن کرد: هر `fork()` که همه‌ی فرآیندها به آن برسند تعدادشان را دو برابر می‌کند. در همین تمرین معلوم شد ترتیب خروجی والد و فرزند تضمین‌شده نیست و اگر ترتیب مشخصی لازم باشد باید از `wait()` استفاده کرد.

در تمرین ۲، خروجی `ps aux | grep Z` همیشه یک خط اضافه داشت که مال خود `grep` بود. با `ps -o pid,ppid,stat,cmd` و نگاه کردن به ستون `STAT` و برچسب `<defunct>` می‌شد Zombie واقعی را از آن خط جدا کرد و رابطه‌ی آن با والد را از ستون `PPID` دید.

در تمرین ۳ باید معلوم می‌شد کدام فرزند زودتر تمام شده است. ساختن هر دو فرزند قبل از اولین `wait()` و مقایسه‌ی شناسه‌ی برگشتی از `wait()` با `pid1` و `pid2` این مشکل را حل کرد. نکته‌ی دیگر این بود که اگر `exec()` شکست بخورد، فرزند کد والد را ادامه می‌دهد؛ برای همین بلافاصله بعد از `exec()` یک `perror()` و `_exit()` گذاشتم.

بیشترین وقت را تمرین ۴ گرفت. اجرای `cd` در فرزند هیچ اثری روی Shell نداشت، و راه‌حل این بود که `cd` به‌صورت built-in و با `chdir()` در خود Shell و قبل از `fork()` اجرا شود. علامت `&` هم باید قبل از `execvp()` از آرایه‌ی آرگومان‌ها حذف می‌شد، وگرنه برنامه‌ی مقصد آن را آرگومان خودش می‌دید. مشکل آخر Zombie شدن فرزندهای پس‌زمینه بود که با `waitpid(-1, ..., WNOHANG)` قبل از هر prompt حل شد. استفاده از `waitpid(pid, ...)` به جای `wait()` برای دستورهای foreground هم جلوی قاطی شدن آن‌ها با فرزندهای پس‌زمینه را گرفت.
