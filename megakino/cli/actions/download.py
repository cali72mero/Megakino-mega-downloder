import os
import concurrent.futures
import re
from pathlib import Path
from typing import List
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, SpinnerColumn
from yt_dlp import YoutubeDL
from megakino.core.models import Episode
from megakino.core.config import config
from megakino.core.dependencies import check_dependency, show_dependency_error

console = Console()

def sanitize_filename(name: str) -> str:
    # Remove invalid characters for all OS filesystems
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def download_task(link: str, episode: Episode, progress: Progress, task_id, user_agent: str):
    safe_title = sanitize_filename(episode.title)
    output_dir = Path(config.download_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{safe_title}.mp4"

    def my_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                progress.update(task_id, total=total_bytes)
            downloaded = d.get('downloaded_bytes', 0)
            progress.update(task_id, completed=downloaded)
            
    def my_pp_hook(d):
        if d['status'] == 'started':
            pp = d.get('postprocessor', 'Unbekannt')
            if pp == 'Merger' or pp == 'FFmpegMerger':
                progress.update(task_id, description=f"[bold green]Setze Video zusammen...[/bold green] {safe_title}")
            elif pp == 'FixupM3u8':
                progress.update(task_id, description=f"[bold cyan]Repariere Video-Format...[/bold cyan] {safe_title}")
            else:
                progress.update(task_id, description=f"[bold magenta]Verarbeite...[/bold magenta] {safe_title}")

    ydl_opts = {
        # Prefer Apple-compatible codecs (H.264 video, AAC audio) in MP4 container
        'format': 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': str(output_file),
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [my_hook],
        'postprocessor_hooks': [my_pp_hook],
        'fragment_retries': 20,
        'retries': 10,
        'concurrent_fragment_downloads': 5,
        'nocheckcertificate': True,
        'merge_output_format': 'mp4', # Ensures broken streams are remuxed into a proper MP4
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4', # Guarantees the final output is a clean .mp4 container for Apple
        }],
        'http_headers': {
            'User-Agent': user_agent,
            'Referer': 'https://voe.sx/',
            'Origin': 'https://voe.sx/'
        }
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        progress.update(task_id, completed=progress.tasks[task_id].total or 100, description=f"[green]Fertig:[/green] {safe_title}")
    except Exception as e:
        progress.update(task_id, description=f"[red]Fehlgeschlagen:[/red] {safe_title}")
        console.print(f"\n[red]Fehler bei {safe_title}: {e}[/red]")

def download_concurrently(direct_links: List[str], episodes: List[Episode], user_agent: str):
    if not check_dependency("ffmpeg"):
        console.print("[bold red]ACHTUNG: FFmpeg fehlt auf deinem System![/bold red]")
        console.print("Ohne FFmpeg sind die heruntergeladenen MP4-Dateien oft fehlerhaft (Broken Container) und lassen sich nicht abspielen.")
        show_dependency_error(["ffmpeg"])
        
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        tasks = []
        for link, episode in zip(direct_links, episodes):
            task_id = progress.add_task(f"[cyan]Lade herunter...[/cyan] {episode.title}", total=None)
            tasks.append((link, episode, task_id))
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.concurrent_downloads) as executor:
            futures = [
                executor.submit(download_task, link, episode, progress, task_id, user_agent)
                for link, episode, task_id in tasks
            ]
            concurrent.futures.wait(futures)
            
    console.print("\n[bold green]Alle Downloads abgeschlossen![/bold green]")
