# Caminho: pje-provisioner/tests/test_pje_office_service.py

from unittest.mock import patch
from app.core.pje_office_service import PJeOfficeService


def test_install_when_not_installed():

    with patch("app.core.pje_office_service.is_installed", return_value=False), \
         patch("app.core.pje_office_service.download_installer") as mock_download, \
         patch("app.core.pje_office_service.install_silent", return_value=True):

        service = PJeOfficeService()
        result = service.ensure_installed()

        assert result["status"] == "installed"
        mock_download.assert_called_once()
