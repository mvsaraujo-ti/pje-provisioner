"""
app/utils/version_utils.py

Responsável por normalizar e comparar versões.
"""


def normalize_version(version: str) -> tuple:
    """
    Converte versões como:
        2.5.16u  -> (2, 5, 16, 0)
        2.5.16.0 -> (2, 5, 16, 0)
    """

    if not version:
        return (0, 0, 0, 0)

    version = version.replace("u", ".0")

    parts = version.split(".")

    # Garantir 4 partes
    while len(parts) < 4:
        parts.append("0")

    return tuple(int(p) for p in parts)
