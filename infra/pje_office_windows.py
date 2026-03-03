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
import subprocess

from config.pje_office_config import LATEST_VERSION, INSTALLER_PATH
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

        if not INSTALLER_PATH.exists():
            raise FileNotFoundError(
                "Instalador não encontrado no cache."
            )

        command = [
            str(INSTALLER_PATH),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/SP-",
        ]

        process = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        return process.returncode == 0
