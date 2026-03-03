from infra.downloader import InstallerDownloader

downloader = InstallerDownloader()
path = downloader.ensure_installer()

print("Instalador em:", path)
