#define _GNU_SOURCE
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/resource.h>
#include <linux/capability.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <errno.h>
#include <stddef.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

#define BLOCK_NR(n) BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K, (n), 0, 1), BPF_STMT(BPF_RET|BPF_K, SECCOMP_RET_ERRNO | (EPERM & SECCOMP_RET_DATA))
static struct sock_filter filter[] = {
  BPF_STMT(BPF_LD|BPF_W|BPF_ABS, offsetof(struct seccomp_data, nr)),
#ifdef SYS_clone
  BLOCK_NR(SYS_clone),
#endif
#ifdef SYS_clone3
  BLOCK_NR(SYS_clone3),
#endif
#ifdef SYS_fork
  BLOCK_NR(SYS_fork),
#endif
#ifdef SYS_vfork
  BLOCK_NR(SYS_vfork),
#endif
#ifdef SYS_mount
  BLOCK_NR(SYS_mount),
#endif
#ifdef SYS_umount2
  BLOCK_NR(SYS_umount2),
#endif
#ifdef SYS_pivot_root
  BLOCK_NR(SYS_pivot_root),
#endif
#ifdef SYS_ptrace
  BLOCK_NR(SYS_ptrace),
#endif
#ifdef SYS_unshare
  BLOCK_NR(SYS_unshare),
#endif
#ifdef SYS_bpf
  BLOCK_NR(SYS_bpf),
#endif
#ifdef SYS_socket
  BLOCK_NR(SYS_socket),
#endif
  BPF_STMT(BPF_RET|BPF_K, SECCOMP_RET_ALLOW)
};
static int limit(int kind, rlim_t soft, rlim_t hard) {
    struct rlimit value = {soft, hard};
    return setrlimit(kind, &value);
}
int main(int argc, char **argv) {
    if (argc < 1) return 64;
    if(chdir("/work") != 0) return 65;
    if(limit(RLIMIT_CPU, 8, 9) || limit(RLIMIT_AS, 512UL*1024*1024, 512UL*1024*1024) ||
       limit(RLIMIT_FSIZE, 1024UL*1024, 1024UL*1024) || limit(RLIMIT_CORE, 0, 0) ||
       limit(RLIMIT_NOFILE, 64, 64)) return 66;
    if(prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) return 67;
    struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct caps[2] = {{0,0,0},{0,0,0}};
    if(syscall(SYS_capset, &header, caps) != 0) return 68;
    struct sock_fprog program = {sizeof(filter)/sizeof(filter[0]), filter};
    if(prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) != 0) return 69;
    char *args[] = {"/usr/bin/python3.13", "-B", "-m", "unittest", "discover", "-s", "tests", "-v", NULL};
    char *env[] = {"PATH=/usr/bin", "HOME=/work", "PYTHONPATH=/work", "PYTHONDONTWRITEBYTECODE=1", "LC_ALL=C.UTF-8", NULL};
    execve(args[0], args, env);
    return 70;
}