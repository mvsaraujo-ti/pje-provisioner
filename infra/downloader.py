"""
infra/downloader.py

Responsável por:
- Garantir existência do diretório de cache
- Baixar o instalador do PJeOffice apenas se necessário
- Retornar o caminho final do instalador
"""

import requests
from pathlib import Path
from config.pje_office_config import DOWNLOAD_URL, INSTALLER_PATH, CACHE_DIR


class InstallerDownloader:
    """
    Gerencia o download do instalador oficial.
    """

    def ensure_installer(self) -> Path:
        """
        Garante que o instalador esteja presente no cache.
        Se já existir, reutiliza.
        Caso contrário, realiza download.
        """

        # 1️⃣ Criar diretório de cache se não existir
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # 2️⃣ Se já existe, não baixa novamente
        if INSTALLER_PATH.exists():
            return INSTALLER_PATH

        # 3️⃣ Baixar instalador
        response = requests.get(DOWNLOAD_URL, stream=True, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(
                f"Falha no download. HTTP {response.status_code}"
            )

        # 4️⃣ Salvar arquivo em disco
        with open(INSTALLER_PATH, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        return INSTALLER_PATH
