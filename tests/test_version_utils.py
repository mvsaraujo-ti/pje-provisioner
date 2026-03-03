from app.utils.version_utils import normalize_version

print(normalize_version("2.5.16u"))
print(normalize_version("2.5.16.0"))
print(normalize_version("2.5.9"))
