from __future__ import annotations

from app.modules.browser_module import run_browser_fix as run_browser_fix_module


class ProvisionerService:
    def run_browser_fix(self) -> dict:
        return run_browser_fix_module()

