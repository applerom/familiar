# START_MODULE_CONTRACT: MOD-SCAN-LINUX
# PURPOSE: Close file and socket access before a Linux worker reads untrusted scan bytes.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - Landlock limits file access and seccomp denies native socket and process operations [review: engine lead]
# CHANGES_WITH:
# - MOD-RECEIVED-SCAN
# :END_MODULE_CONTRACT
import ctypes as c
import errno
import os
import platform


def _filesystem():
    # These Landlock syscall numbers are shared by the supported Linux architectures.
    if platform.machine() not in {'x86_64', 'aarch64'}:
        raise OSError('scan isolation needs a supported Landlock architecture')
    libc = c.CDLL(None, use_errno=True)
    abi = libc.syscall(444, None, 0, 1)  # LANDLOCK_CREATE_RULESET_VERSION
    if abi < 1:
        raise OSError(c.get_errno(), 'scan isolation needs Landlock')
    rights = c.c_uint64((1 << (16 if abi >= 5 else 15 if abi >= 3 else 14 if abi >= 2 else 13)) - 1)
    fd = libc.syscall(444, c.byref(rights), c.sizeof(rights), 0)
    if fd < 0:
        raise OSError(c.get_errno(), 'cannot create the scan filesystem policy')
    try:
        # PR_SET_NO_NEW_PRIVS; prohibit fresh file reads/writes, using the already open stdio only.
        if libc.prctl(38, 1, 0, 0, 0) or libc.syscall(446, fd, 0):
            raise OSError(c.get_errno(), 'cannot apply the scan filesystem policy')
    finally:
        os.close(fd)


class _Argument(c.Structure):
    _fields_ = [('number', c.c_uint), ('operation', c.c_int), ('mask', c.c_uint64), ('value', c.c_uint64)]


def isolate():
    # Load the library before closing filesystem access. Seccomp sees native codec calls too.
    if len(os.listdir('/proc/self/task')) != 1:
        raise OSError('the scan worker started a thread before applying Landlock')
    seccomp = c.CDLL('libseccomp.so.2')
    seccomp.seccomp_init.argtypes = (c.c_uint32,)
    seccomp.seccomp_init.restype = c.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = (c.c_char_p,)
    seccomp.seccomp_rule_add_array.argtypes = (c.c_void_p, c.c_uint32, c.c_int, c.c_uint, c.POINTER(_Argument))
    seccomp.seccomp_load.argtypes = (c.c_void_p,)
    seccomp.seccomp_release.argtypes = (c.c_void_p,)
    policy = seccomp.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not policy:
        raise OSError('cannot create the scan syscall policy')

    def deny(name, error=errno.EPERM, argument=None):
        number = seccomp.seccomp_syscall_resolve_name(name.encode('ascii'))
        if number < 0:
            return  # Some architectures implement fork and vfork through clone only.
        result = seccomp.seccomp_rule_add_array(policy, 0x00050000 | error, number, bool(argument), argument)
        if result < 0:
            raise OSError(-result, f'cannot restrict the scan syscall {name}')

    try:
        for name in ('socket', 'socketpair', 'io_uring_setup', 'ptrace', 'process_vm_readv', 'process_vm_writev',
                     'pidfd_getfd', 'execve', 'execveat', 'fork', 'vfork', 'kill', 'tkill', 'tgkill'):
            deny(name)
        deny('clone', argument=_Argument(0, 7, 0x10000, 0))  # Allow only CLONE_THREAD.
        deny('clone3', errno.ENOSYS)  # Let libc fall back to clone for threads.
        _filesystem()
        if error := seccomp.seccomp_load(policy):
            raise OSError(-error, 'cannot apply the scan syscall policy')
    finally:
        seccomp.seccomp_release(policy)
