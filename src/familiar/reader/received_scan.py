# START_MODULE_CONTRACT: MOD-RECEIVED-SCAN
# PURPOSE: Render a relative's untrusted original in a bounded process before family display.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - native decoding begins only inside OS-enforced memory and time bounds; Windows uses a networkless AppContainer [review: engine lead]
# - the reader receives a newly encoded, metadata-free, bounded raster [review: engine lead]
# CHANGES_WITH:
# - MOD-INTAKE-PHOTO (private original and public rendition)
# - MOD-READER-SCANS (common raster encoding)
# :END_MODULE_CONTRACT
import io
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile

from familiar.desk.attachments import ATTACH_LIMITS

MEMORY_BYTES = 768 * 1024 * 1024
PIXELS = 50_000_000
WALL_SECONDS = 12
MAX_OUTPUT = 16 * 1024 * 1024
ISOLATION_FAILED = 77
OUTPUT_TYPES = {'jpg': ('JPEG', b'\xff\xd8\xff'), 'png': ('PNG', b'\x89PNG\r\n\x1a\n'),
                'webp': ('WEBP', b'RIFF')}


@contextmanager
def _windows_limit(pid):
    """Assign the worker to a Job before it receives a byte of the original."""
    import ctypes as c
    from ctypes import wintypes as w

    class BasicLimits(c.Structure):
        _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong),
                    ('flags', w.DWORD), ('min_working_set', c.c_size_t), ('max_working_set', c.c_size_t),
                    ('active_processes', w.DWORD), ('affinity', c.c_size_t),
                    ('priority', w.DWORD), ('scheduling', w.DWORD)]

    class ExtendedLimits(c.Structure):
        _fields_ = [('basic', BasicLimits), ('io', c.c_ulonglong * 6),
                    ('process_memory', c.c_size_t), ('job_memory', c.c_size_t),
                    ('peak_process_memory', c.c_size_t), ('peak_job_memory', c.c_size_t)]

    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = (w.LPVOID, w.LPCWSTR)
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.OpenProcess.argtypes = (w.DWORD, w.BOOL, w.DWORD)
    kernel.OpenProcess.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = (w.HANDLE, c.c_int, w.LPVOID, w.DWORD)
    kernel.SetInformationJobObject.restype = w.BOOL
    kernel.AssignProcessToJobObject.argtypes = (w.HANDLE, w.HANDLE)
    kernel.AssignProcessToJobObject.restype = w.BOOL
    kernel.CloseHandle.argtypes = (w.HANDLE,)
    kernel.CloseHandle.restype = w.BOOL

    limits = ExtendedLimits()
    # JOB_OBJECT_LIMIT_ACTIVE_PROCESS | PROCESS_MEMORY | KILL_ON_JOB_CLOSE.
    limits.basic.flags = 0x0008 | 0x0100 | 0x2000
    limits.basic.active_processes = 1
    limits.process_memory = MEMORY_BYTES
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise c.WinError(c.get_last_error())
    try:
        if not kernel.SetInformationJobObject(job, 9, c.byref(limits), c.sizeof(limits)):
            raise c.WinError(c.get_last_error())
        process = kernel.OpenProcess(0x0100 | 0x0001, False, pid)  # SET_QUOTA | TERMINATE
        if not process:
            raise c.WinError(c.get_last_error())
        try:
            if not kernel.AssignProcessToJobObject(job, process):
                raise c.WinError(c.get_last_error())
        finally:
            kernel.CloseHandle(process)
        yield
    finally:
        kernel.CloseHandle(job)


def _run(raw, suffix):
    with TemporaryDirectory(prefix='familiar-scan-') as temporary:
        if os.name == 'nt':
            from .scan_windows import run
            script = ("import runpy, sys; sys.path.append(sys.argv.pop(1)); "
                      f"runpy.run_module({__spec__.name!r}, run_name='__main__')")
            return run(Path(__file__).resolve(), Path(temporary), script, [suffix], raw,
                       _windows_limit, WALL_SECONDS, MAX_OUTPUT)
        command = [sys.executable, '-I', '-B', '-m', __spec__.name, suffix]
        with TemporaryFile() as output:
            process = subprocess.run(command, input=raw, stdout=output, stderr=subprocess.DEVNULL,
                                     cwd=temporary, env={}, close_fds=True, timeout=WALL_SECONDS)
            output.seek(0)
            return process.returncode, output.read(MAX_OUTPUT + 1)


def raster(raw, suffix='jpg'):
    """Decode once in a worker. A failed decode never makes the original a display asset."""
    if not 0 < len(raw) <= ATTACH_LIMITS['file_bytes']:
        raise ValueError('received scan exceeds the file limit')
    _, signature = OUTPUT_TYPES[suffix]
    try:
        code, image = _run(raw, suffix)
    except subprocess.TimeoutExpired:
        raise ValueError('received scan exceeded its decoding time limit') from None
    except OSError as error:
        raise ValueError(f'cannot start a restricted scan decoder: {error}') from error
    if code == ISOLATION_FAILED:
        raise ValueError('cannot isolate the scan decoder; on Linux enable Landlock and install libseccomp')
    if code or len(image) > MAX_OUTPUT or not image.startswith(signature):
        raise ValueError('cannot render the received scan within its pixel and memory limits; '
                         'check the original and install Familiar with the images extra')
    return image


def _isolate_posix():
    if sys.platform == 'linux':
        from .scan_linux import isolate
        isolate()
    elif sys.platform == 'darwin':
        import ctypes
        sandbox = ctypes.CDLL('/usr/lib/libsandbox.1.dylib')
        sandbox.sandbox_init.argtypes = (ctypes.c_char_p, ctypes.c_uint64,
                                         ctypes.POINTER(ctypes.c_char_p))
        sandbox.sandbox_free_error.argtypes = (ctypes.c_char_p,)
        error = ctypes.c_char_p()
        if sandbox.sandbox_init(b'(version 1)(deny default)(allow sysctl-read)', 0, ctypes.byref(error)):
            sandbox.sandbox_free_error(error)
            raise OSError('cannot apply the scan Seatbelt profile')
    else:
        raise OSError('no scan sandbox for this operating system')


def _worker(suffix):
    if os.name != 'nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU, (WALL_SECONDS, WALL_SECONDS))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT, MAX_OUTPUT))
    import warnings
    from PIL import Image, ImageOps  # noqa: F401 -- preloaded for the filesystem policy
    from .scans import derivative, first_page

    Image.MAX_IMAGE_PIXELS = PIXELS
    warnings.simplefilter('error', Image.DecompressionBombWarning)
    if os.name != 'nt':
        Image.init()
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass
        try:
            import pypdfium2  # noqa: F401 -- load the native library before closing file access
        except ImportError:
            pass
        try:
            _isolate_posix()
        except (OSError, AttributeError):
            sys.exit(ISOLATION_FAILED)
    raw = sys.stdin.buffer.read(ATTACH_LIMITS['file_bytes'] + 1)
    if not 0 < len(raw) <= ATTACH_LIMITS['file_bytes']:
        return
    # PDFium renders the first page at no more than WEB_SIDE on either side.
    jpeg = first_page(raw) if raw.startswith(b'%PDF-') else derivative(raw)
    if jpeg is None:
        return
    if suffix != 'jpg':
        # Existing adopted assets keep the same URL through the upgrade.
        with Image.open(io.BytesIO(jpeg)) as image:
            out = io.BytesIO()
            image.save(out, OUTPUT_TYPES[suffix][0])
            jpeg = out.getvalue()
    sys.stdout.buffer.write(jpeg)


if __name__ == '__main__':
    _worker(sys.argv[1])
