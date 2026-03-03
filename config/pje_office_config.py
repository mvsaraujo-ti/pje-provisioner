"""
config/pje_office_config.py

Configurações oficiais do módulo PJeOffice.
Este arquivo é a única fonte de verdade da versão suportada.
"""

from pathlib import Path

# 🔹 Versão oficial suportada pelo Provisioner
LATEST_VERSION = "2.5.16u"

# 🔹 URL oficial externa
DOWNLOAD_URL = (
    "https://pje-office.pje.jus.br/pro/"
    "pjeoffice-pro-v2.5.16u-windows_x64.exe"
)

# 🔹 Nome esperado do instalador
INSTALLER_FILENAME = "pjeoffice-pro-v2.5.16u-windows_x64.exe"

# 🔹 Diretório global de cache
CACHE_DIR = Path(r"C:\ProgramData\PJEProvisioner\cache")

# 🔹 Caminho completo do instalador em cache
INSTALLER_PATH = CACHE_DIR / INSTALLER_FILENAME
