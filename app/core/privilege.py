import sys
import platform


def is_windows():
    return platform.system() == "Windows"


def _get_shell32():
    if not is_windows():
        return None

    import ctypes
    return getattr(ctypes, "windll", None)


def is_admin():
    shell = _get_shell32()
    if not shell:
        return False

    try:
        return shell.shell32.IsUserAnAdmin()
    except Exception:
        return False


def relaunch_as_admin():
    shell = _get_shell32()
    if not shell:
        return

    if not is_admin():
        shell.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            None,
            None,
            1
        )
        sys.exit()
