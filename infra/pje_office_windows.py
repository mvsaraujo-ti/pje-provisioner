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
import subprocess
import time

from config.pje_office_config import LATEST_VERSION, INSTALLER_PATH
from app.utils.logger import get_logger
from app.utils.version_utils import normalize_version


class PJeOfficeWindows:
    """
    Implementação Windows para controle do PJeOffice Pro.
    """

    # Caminho fixo padrão de instalação
    EXECUTABLE_PATH = Path(
        r"C:\Program Files\PJeOffice Pro\pjeoffice-pro.exe"
    )

    # ---------------------------------------------------------
    # 🔍 Verifica se está instalado
    # ---------------------------------------------------------

    def is_installed(self) -> bool:
        """
        Retorna True se o executável existir.
        """
        return self.EXECUTABLE_PATH.exists()

    # ---------------------------------------------------------
    # 🔎 Obtém versão instalada
    # ---------------------------------------------------------

    def get_installed_version(self) -> str | None:
        """
        Retorna versão instalada no formato:
            '2.5.16.0'

        Retorna None se:
            - Não estiver instalado
            - Não conseguir extrair versão
        """

        if not self.is_installed():
            return None

        command = [
            "powershell",
            "-Command",
            f"(Get-Item '{self.EXECUTABLE_PATH}').VersionInfo.ProductVersion"
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        version = result.stdout.strip()

        if not version:
            return None

        return version

    # ---------------------------------------------------------
    # 📊 Verifica se está desatualizado
    # ---------------------------------------------------------

    def is_outdated(self) -> bool:
        """
        Retorna True se:

            - Não estiver instalado
            OU
            - Versão instalada for menor que versão suportada
        """

        installed_version = self.get_installed_version()

        # Não instalado = precisa instalar
        if not installed_version:
            return True

        installed_tuple = normalize_version(installed_version)
        latest_tuple = normalize_version(LATEST_VERSION)

        return installed_tuple < latest_tuple

    # ---------------------------------------------------------
    # ⚙ Executa instalação silenciosa
    # ---------------------------------------------------------

    def install_silent(self) -> bool:
        """
        Executa instalação silenciosa via Inno Setup.

        Flags utilizadas:
            /VERYSILENT
            /SUPPRESSMSGBOXES
            /NORESTART
            /SP-

        Retorna True se exit code == 0
        """

        logger = get_logger()

        if not INSTALLER_PATH.exists():
            raise FileNotFoundError(
                "Instalador não encontrado no cache."
            )

        parameters = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-"

        logger.info(
            "pje_office_install_started",
            extra={
                "event": "pje_office_install_started",
                "installer_path": str(INSTALLER_PATH),
                "mode": "silent",
            },
        )

        print("EXECUTING REAL INSTALLER")

        shell_execute_code = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            str(INSTALLER_PATH),
            parameters,
            None,
            1,
        )

        if shell_execute_code <= 32:
            logger.info(
                "pje_office_install_finished",
                extra={
                    "event": "pje_office_install_finished",
                    "installer_path": str(INSTALLER_PATH),
                    "return_code": shell_execute_code,
                    "success": False,
                },
            )
            raise RuntimeError(
                "Falha ao iniciar instalação silenciosa com elevação. "
                f"ShellExecuteW code: {shell_execute_code}"
            )

        installer_name = INSTALLER_PATH.name
        timeout_seconds = 60 * 30
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout_seconds:
            result = subprocess.run(
                [
                    "tasklist",
                    "/FI",
                    f"IMAGENAME eq {installer_name}",
                    "/FO",
                    "CSV",
                    "/NH",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if installer_name.lower() not in result.stdout.lower():
                break
            time.sleep(1)
        else:
            logger.info(
                "pje_office_install_finished",
                extra={
                    "event": "pje_office_install_finished",
                    "installer_path": str(INSTALLER_PATH),
                    "return_code": 1,
                    "success": False,
                },
            )
            raise RuntimeError(
                "Timeout aguardando término da instalação silenciosa do PJeOffice Pro."
            )

        install_success = self.is_installed() and not self.is_outdated()
        return_code = 0 if install_success else 1

        logger.info(
            "pje_office_install_finished",
            extra={
                "event": "pje_office_install_finished",
                "installer_path": str(INSTALLER_PATH),
                "return_code": return_code,
                "success": install_success,
            },
        )

        if not install_success:
            raise RuntimeError(
                "Falha na instalação silenciosa do PJeOffice Pro."
            )

        return True
