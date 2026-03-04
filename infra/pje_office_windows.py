"""
infra/pje_office_windows.py

Responsável por:

- Detectar se o PJeOffice Pro está instalado
- Detectar versão instalada via metadata do executável
- Comparar versão instalada com versão suportada
- Executar instalação silenciosa quando necessário

Implementação específica para Windows.
"""

from pathlib import Path
import ctypes
from ctypes import wintypes
import os
import subprocess
import threading
import time

import psutil
try:
    import win32api
except Exception:  # pragma: no cover - optional dependency
    win32api = None

from config.pje_office_config import LATEST_VERSION, INSTALLER_PATH
from app.utils.logger import get_logger
from app.utils.version_utils import normalize_version


class PJeOfficeWindows:
    """
    Implementacao Windows para controle do PJeOffice Pro.
    """

    # Caminho fixo padrao de instalacao
    EXECUTABLE_PATH = Path(
        r"C:\Program Files\PJeOffice Pro\pjeoffice-pro.exe"
    )
    INSTALL_TIMEOUT_SECONDS = 180

    _install_lock = threading.Lock()
    _install_in_progress = False
    _current_install_pid = None

    # ---------------------------------------------------------
    # Verifica se esta instalado
    # ---------------------------------------------------------

    @classmethod
    def get_current_install_pid(cls) -> int | None:
        return cls._current_install_pid

    @classmethod
    def is_installation_running(cls) -> bool:
        return cls._install_in_progress

    def is_pje_office_installed(self) -> bool:
        logger = get_logger()
        logger.info("[INFO] Verificando instalacao do PJe Office")
        return self.EXECUTABLE_PATH.exists()

    def is_installed(self) -> bool:
        """
        Retorna True se o executavel existir.
        """
        return self.is_pje_office_installed()

    # ---------------------------------------------------------
    # Obtem versao instalada
    # ---------------------------------------------------------

    def get_pje_office_version(self) -> str | None:
        logger = get_logger()

        if not self.is_pje_office_installed():
            return None

        if win32api is None:
            command = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-Item '{self.EXECUTABLE_PATH}').VersionInfo.ProductVersion",
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            version = (result.stdout or "").strip()
            if version:
                logger.info(f"[INFO] Versao detectada: {version}")
                return version
            logger.error("[ERROR] Falha na instalacao: erro ao obter versao")
            return None

        try:
            version_info = win32api.GetFileVersionInfo(
                str(self.EXECUTABLE_PATH),
                "\\",
            )
            ms = version_info["FileVersionMS"]
            ls = version_info["FileVersionLS"]
            version = (
                f"{ms >> 16}.{ms & 0xFFFF}."
                f"{ls >> 16}.{ls & 0xFFFF}"
            )
            logger.info(f"[INFO] Versao detectada: {version}")
            return version
        except Exception as exc:
            logger.error(f"[ERROR] Falha na instalacao: erro ao obter versao ({exc})")
            return None

    def get_installed_version(self) -> str | None:
        """
        Retorna versao instalada no formato:
            '2.5.16.0'

        Retorna None se:
            - Nao estiver instalado
            - Nao conseguir extrair versao
        """
        return self.get_pje_office_version()

    # ---------------------------------------------------------
    # Verifica se esta desatualizado
    # ---------------------------------------------------------

    def is_outdated(self) -> bool:
        """
        Retorna True se:

            - Nao estiver instalado
            OU
            - Versao instalada for menor que versao suportada
        """

        installed_version = self.get_pje_office_version()
        if not installed_version:
            return True

        installed_tuple = normalize_version(installed_version)
        latest_tuple = normalize_version(LATEST_VERSION)

        return installed_tuple < latest_tuple

    # ---------------------------------------------------------
    # Executa instalacao silenciosa
    # ---------------------------------------------------------

    def install_silent(self) -> bool:
        """
        Executa instalacao silenciosa via Inno Setup.

        Flags utilizadas:
            /VERYSILENT
            /SUPPRESSMSGBOXES
            /NORESTART
            /SP-

        Retorna True se o processo do instalador for iniciado com sucesso.
        """

        logger = get_logger()
        cls = self.__class__

        installer_path = str(INSTALLER_PATH)

        if not os.path.exists(installer_path):
            raise RuntimeError(f"Installer not found: {installer_path}")

        params = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-"

        with cls._install_lock:
            if cls._install_in_progress:
                logger.warning("[INFO] Instalacao do PJe Office ja esta em andamento")
                return False
            cls._install_in_progress = True
            cls._current_install_pid = None

        logger.info(
            "pje_office_install_started",
            extra={
                "event": "pje_office_install_started",
                "installer_path": installer_path,
                "mode": "silent",
            },
        )
        logger.info("[INFO] Instalando PJe Office Pro")

        return_code = 1
        install_success = False
        error_message = None

        try:
            LOGON_WITH_PROFILE = 0x00000001
            CREATE_NEW_CONSOLE = 0x00000010

            username = "Administrador"
            domain = "."
            password = "5up0r73"
            command = f'"{installer_path}" {params}'

            class STARTUPINFO(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("lpReserved", wintypes.LPWSTR),
                    ("lpDesktop", wintypes.LPWSTR),
                    ("lpTitle", wintypes.LPWSTR),
                    ("dwX", wintypes.DWORD),
                    ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD),
                    ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD),
                    ("dwYCountChars", wintypes.DWORD),
                    ("dwFillAttribute", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD),
                    ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
                    ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE),
                    ("hStdError", wintypes.HANDLE),
                ]

            class PROCESS_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("hProcess", wintypes.HANDLE),
                    ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD),
                    ("dwThreadId", wintypes.DWORD),
                ]

            startup = STARTUPINFO()
            startup.cb = ctypes.sizeof(startup)
            process_info = PROCESS_INFORMATION()

            result = ctypes.windll.advapi32.CreateProcessWithLogonW(
                username,
                domain,
                password,
                LOGON_WITH_PROFILE,
                None,
                command,
                CREATE_NEW_CONSOLE,
                None,
                None,
                ctypes.byref(startup),
                ctypes.byref(process_info),
            )

            if not result:
                raise RuntimeError(
                    "Failed to launch installer with CreateProcessWithLogonW"
                )

            pid = int(process_info.dwProcessId)
            ctypes.windll.kernel32.CloseHandle(process_info.hThread)
            ctypes.windll.kernel32.CloseHandle(process_info.hProcess)

            if pid <= 0:
                raise RuntimeError("Failed to capture installer PID")

            cls._current_install_pid = pid
            start_time = time.monotonic()

            while psutil.pid_exists(pid):
                if time.monotonic() - start_time > self.INSTALL_TIMEOUT_SECONDS:
                    logger.error("Timeout during PJe Office installation")
                    raise RuntimeError("Timeout during PJe Office installation")
                time.sleep(1)

            install_success = self.is_pje_office_installed()
            if not install_success:
                raise RuntimeError("Falha na instalacao do PJe Office")

            return_code = 0
            return True
        except Exception as exc:
            error_message = str(exc)
            logger.error("[ERROR] Falha na instalacao")
            raise
        finally:
            logger.info(
                "pje_office_install_finished",
                extra={
                    "event": "pje_office_install_finished",
                    "installer_path": installer_path,
                    "return_code": return_code,
                    "success": install_success,
                    "error": error_message,
                },
            )
            with cls._install_lock:
                cls._install_in_progress = False
                cls._current_install_pid = None
