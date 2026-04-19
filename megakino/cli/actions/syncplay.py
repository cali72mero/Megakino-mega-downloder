import getpass
import platform
import subprocess
from typing import List

from rich.console import Console

from megakino.core.dependencies import check_dependency
from megakino.core.models import Episode

console = Console()


def syncplay(direct_links: List[str], episodes: List[Episode]):
    executable = "SyncplayConsole" if platform.system() == "Windows" else "syncplay"

    if not check_dependency(executable):
        from megakino.core.dependencies import show_dependency_error

        show_dependency_error(["syncplay"])

    syncplay_username = getpass.getuser()
    syncplay_hostname = "syncplay.pl:8997"

    for link, episode in zip(direct_links, episodes):
        console.print(f"[bold magenta]Starting Syncplay for:[/bold magenta] {episode.title}")
        command = [
            executable,
            "--no-gui",
            "--no-store",
            "--host",
            syncplay_hostname,
            "--name",
            syncplay_username,
            "--room",
            episode.title,
            "--player",
            "mpv",
            link,
            "--",
            "--profile=fast",
            "--hwdec=auto-safe",
            "--fs",
            "--video-sync=display-resample",
            f"--force-media-title={episode.title}",
            "--http-header-fields=Referer: https://voe.sx/,Origin: https://voe.sx/",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            console.print(f"[bold red]Failed to start Syncplay for {episode.title}[/bold red]")
