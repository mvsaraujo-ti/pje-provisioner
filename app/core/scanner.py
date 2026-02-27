class SystemScanner:
    def run_full_scan(self):
        return {
            "token": {
                "status": True,
                "message": "Token detectado (simulado)"
            },
            "driver": {
                "status": False,
                "message": "Driver desatualizado"
            },
            "pje_office": {
                "status": False,
                "message": "PJe Office não instalado"
            },
            "browser": {
                "status": True,
                "message": "Navegadores configurados"
            }
        }

    def run_simulated_fixes(self, scan_results):
        fixed_results = {}

        for component, data in scan_results.items():
            if data["status"]:
                fixed_results[component] = data
                continue

            fixed_results[component] = {
                "status": True,
                "message": f"{component.replace('_', ' ').title()} corrigido (simulado)"
            }

        return fixed_results
