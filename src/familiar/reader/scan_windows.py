# START_MODULE_CONTRACT: MOD-SCAN-WINDOWS
# PURPOSE: Run untrusted scan bytes with Windows-enforced file and network isolation.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - the fresh AppContainer has no capabilities and inherits only the three scan streams [review: engine lead]
# - the OS job is assigned before the worker starts and leaves no child behind [review: engine lead]
# CHANGES_WITH:
# - MOD-RECEIVED-SCAN
# :END_MODULE_CONTRACT
import ctypes as c
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from ctypes import wintypes as w
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from tempfile import TemporaryFile
from uuid import uuid4


class Startup(c.Structure):
    _fields_ = [('size', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR), ('title', w.LPWSTR),
                ('position', w.DWORD * 7), ('flags', w.DWORD), ('show', w.WORD), ('reserved_size', w.WORD),
                ('reserved_bytes', w.LPVOID), ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE),
                ('attributes', w.LPVOID)]


class Process(c.Structure):
    _fields_ = [('handle', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]


class Capabilities(c.Structure):
    _fields_ = [('sid', w.LPVOID), ('capabilities', w.LPVOID), ('count', w.DWORD), ('reserved', w.DWORD)]


def _api(library, name, result, *arguments):
    function = getattr(library, name)
    function.argtypes, function.restype = arguments, result
    return function


@contextmanager
def _profile():
    user = c.WinDLL('userenv', use_last_error=True)
    advapi = c.WinDLL('advapi32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    create = _api(user, 'CreateAppContainerProfile', c.c_long, w.LPCWSTR, w.LPCWSTR, w.LPCWSTR,
                  w.LPVOID, w.DWORD, c.POINTER(w.LPVOID))
    delete = _api(user, 'DeleteAppContainerProfile', c.c_long, w.LPCWSTR)
    stringify = _api(advapi, 'ConvertSidToStringSidW', w.BOOL, w.LPVOID, c.POINTER(w.LPWSTR))
    free = _api(advapi, 'FreeSid', w.LPVOID, w.LPVOID)
    local_free = _api(kernel, 'LocalFree', w.LPVOID, w.LPVOID)
    name = 'Familiar.Scan.' + uuid4().hex
    sid, string = w.LPVOID(), w.LPWSTR()
    error = create(name, 'Familiar scan decoder', 'Temporary scan decoder', None, 0, c.byref(sid))
    if error != 0:
        raise OSError(f'cannot create scan AppContainer (HRESULT {error & 0xffffffff:#x})')
    try:
        if not stringify(sid, c.byref(string)):
            raise c.WinError(c.get_last_error())
        try:
            yield sid, string.value
        finally:
            local_free(string)
    finally:
        free(sid)
        delete(name)


def _runtime(root, module):
    """Copy only the interpreter, its standard library and the scan decoder wheels."""
    python = Path(sys._base_executable)
    root.mkdir()
    shutil.copyfile(python, root / python.name)
    for path in python.parent.glob('*.dll'):
        shutil.copyfile(path, root / path.name)
    ignore = shutil.ignore_patterns('__pycache__', 'site-packages', 'test', 'tests', 'idlelib', 'tkinter', 'ensurepip')
    for folder in ('Lib', 'DLLs'):
        if (python.parent / folder).is_dir():
            shutil.copytree(python.parent / folder, root / folder, ignore=ignore)
    if python_zip := next(python.parent.glob('python[0-9]*.zip'), None):
        shutil.copyfile(python_zip, root / python_zip.name)
    for name in ('pillow', 'pillow-heif', 'pypdfium2'):
        try:
            package = distribution(name)
        except PackageNotFoundError:
            continue
        for entry in package.files or ():
            path = Path(entry)
            if path.is_absolute() or '..' in path.parts or '__pycache__' in path.parts:
                continue
            source, target = package.locate_file(entry), root / path
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    for source in (module, module.with_name('scans.py'), module.parents[1] / 'desk' / 'attachments.py'):
        target = root / 'familiar' / source.relative_to(module.parents[1])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return root / python.name


@contextmanager
def _process(kernel, command, root, env, sid, handles):
    initialize = _api(kernel, 'InitializeProcThreadAttributeList', w.BOOL, w.LPVOID, w.DWORD, w.DWORD,
                      c.POINTER(c.c_size_t))
    update = _api(kernel, 'UpdateProcThreadAttribute', w.BOOL, w.LPVOID, w.DWORD, c.c_size_t, w.LPVOID,
                  c.c_size_t, w.LPVOID, w.LPVOID)
    delete = _api(kernel, 'DeleteProcThreadAttributeList', None, w.LPVOID)
    create = _api(kernel, 'CreateProcessW', w.BOOL, w.LPCWSTR, w.LPWSTR, w.LPVOID, w.LPVOID, w.BOOL,
                  w.DWORD, w.LPVOID, w.LPCWSTR, c.POINTER(Startup), c.POINTER(Process))
    close = _api(kernel, 'CloseHandle', w.BOOL, w.HANDLE)
    terminate = _api(kernel, 'TerminateProcess', w.BOOL, w.HANDLE, w.UINT)
    size = c.c_size_t()
    initialize(None, 2, 0, c.byref(size))
    attributes = c.create_string_buffer(size.value)
    if not initialize(attributes, 2, 0, c.byref(size)):
        raise c.WinError(c.get_last_error())
    child = Process()
    try:
        capabilities = Capabilities(sid, None, 0, 0)
        inherited = (w.HANDLE * len(handles))(*handles)
        for key, value in ((0x20002, inherited), (0x20009, capabilities)):
            if not update(attributes, 0, key, c.byref(value), c.sizeof(value), None, None):
                raise c.WinError(c.get_last_error())
        startup = Startup(size=c.sizeof(Startup), flags=0x100,  # STARTF_USESTDHANDLES
                          stdin=handles[0], stdout=handles[1], stderr=handles[2],
                          attributes=c.cast(attributes, w.LPVOID))
        args = c.create_unicode_buffer(subprocess.list2cmdline(command))
        # EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT | CREATE_SUSPENDED | CREATE_NO_WINDOW.
        if not create(command[0], args, None, None, True, 0x08080404, env, str(root),
                      c.byref(startup), c.byref(child)):
            raise c.WinError(c.get_last_error())
    finally:
        delete(attributes)
    try:
        yield child
    finally:
        terminate(child.handle, 1)  # Also reap a suspended child if setup raised before job assignment.
        close(child.thread)
        close(child.handle)


def run(module, root, script, args, raw, job, timeout, max_output):
    import msvcrt
    kernel = c.WinDLL('kernel32', use_last_error=True)
    system_root = c.create_unicode_buffer(32768)
    windows_directory = _api(kernel, 'GetWindowsDirectoryW', w.UINT, w.LPWSTR, w.UINT)
    if not 0 < windows_directory(system_root, len(system_root)) < len(system_root):
        raise c.WinError(c.get_last_error())
    values = {name: str(root) for name in ('APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP', 'USERPROFILE')}
    values['SystemRoot'] = system_root.value
    env = c.create_unicode_buffer(''.join(f'{name}={value}\0' for name, value in sorted(values.items())))
    wait = _api(kernel, 'WaitForSingleObject', w.DWORD, w.HANDLE, w.DWORD)
    resume = _api(kernel, 'ResumeThread', w.DWORD, w.HANDLE)
    exit_code = _api(kernel, 'GetExitCodeProcess', w.BOOL, w.HANDLE, c.POINTER(w.DWORD))
    terminate = _api(kernel, 'TerminateProcess', w.BOOL, w.HANDLE, w.UINT)
    with _profile() as (sid, sid_string):
        result = subprocess.run([str(Path(system_root.value) / 'System32' / 'icacls.exe'), str(root),
                                 '/grant', f'*{sid_string}:(OI)(CI)RX', '/Q'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise OSError('cannot grant the AppContainer read access to its temporary runtime')
        python = _runtime(root / 'runtime', module)
        command = [str(python), '-I', '-S', '-B', '-c', script, str(root / 'runtime'), *args]
        read, write = os.pipe()
        with (os.fdopen(read, 'rb') as output, os.fdopen(write, 'wb') as child_output,
              TemporaryFile(dir=root) as input_file, open(os.devnull, 'wb') as errors):
            input_file.write(raw)
            input_file.seek(0)
            streams = (input_file, child_output, errors)
            for stream in streams:
                os.set_inheritable(stream.fileno(), True)
            handles = [msvcrt.get_osfhandle(stream.fileno()) for stream in streams]
            with _process(kernel, command, root, env, sid, handles) as child:
                for stream in (input_file, errors):
                    os.set_inheritable(stream.fileno(), False)
                child_output.close()
                with ThreadPoolExecutor(1) as reader:
                    image = reader.submit(output.read, max_output + 1)
                    try:
                        with job(child.pid):
                            if resume(child.thread) == 0xffffffff:
                                raise c.WinError(c.get_last_error())
                            status = wait(child.handle, timeout * 1000)
                            if status == 258:
                                raise subprocess.TimeoutExpired(command, timeout)
                            code = w.DWORD()
                            if status != 0 or not exit_code(child.handle, c.byref(code)):
                                raise c.WinError(c.get_last_error())
                    finally:
                        if wait(child.handle, 0) != 0:
                            terminate(child.handle, 1)
                            wait(child.handle, 1000)
                    return code.value, image.result()
