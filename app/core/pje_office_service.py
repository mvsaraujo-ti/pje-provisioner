from __future__ import annotations

from infra.downloader import InstallerDownloader
from infra.pje_office_windows import PJeOfficeWindows


class PJeOfficeService:
    def ensure_installed(self) -> dict:
        windows = PJeOfficeWindows()

        print("CHECKING INSTALLATION")
        installed = windows.is_installed()

        if installed and not windows.is_outdated():
            return {
                "status": "up_to_date",
                "message": "PJe Office já está instalado.",
            }

        InstallerDownloader().ensure_installer()

        print("INSTALLING NOW")
        installed_ok = windows.install_silent()
        if installed_ok:
            return {
                "status": "updated" if installed else "installed",
                "message": "PJe Office instalado com sucesso.",
            }

        return {
            "status": "error",
            "message": "Falha ao instalar PJe Office.",
        }
