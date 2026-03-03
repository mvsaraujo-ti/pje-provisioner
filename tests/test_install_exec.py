from infra.pje_office_windows import PJeOfficeWindows

pje = PJeOfficeWindows()

print("Versão detectada:", pje.get_installed_version())
