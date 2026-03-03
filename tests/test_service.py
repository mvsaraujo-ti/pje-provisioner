from app.core.pje_office_service import PJeOfficeService

service = PJeOfficeService()
result = service.ensure_installed()

print(result)
