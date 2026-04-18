import subprocess
from rich.console import Console
from typing import List
from megakino.core.models import Episode
from megakino.core.dependencies import check_dependency

console = Console()

def watch(direct_links: List[str], episodes: List[Episode]):
    if not check_dependency("mpv"):
        from megakino.core.dependencies import show_dependency_error
        show_dependency_error(["mpv"])
    
    for link, episode in zip(direct_links, episodes):
        console.print(f"[bold cyan]Now playing:[/bold cyan] {episode.title}")
        command = [
            "mpv",
            link,
            "--fs",
            "--quiet",
            "--really-quiet",
            "--profile=fast",
            "--hwdec=auto-safe",
            "--video-sync=display-resample",
            "--video-zoom=0.05", # Slightly zoom in to hide edge logos
            "--panscan=1.0",      # Crop edges if aspect ratio differs slightly
            f"--force-media-title={episode.title}",
            "--http-header-fields=Referer: https://voe.sx/,Origin: https://voe.sx/",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            console.print(f"[bold red]Failed to play {episode.title}[/bold red]")
