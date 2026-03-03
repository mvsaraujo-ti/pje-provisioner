from infra.pje_office_windows import PJeOfficeWindows

pje = PJeOfficeWindows()

print("Instalada:", pje.get_installed_version())
print("Desatualizado?", pje.is_outdated())
