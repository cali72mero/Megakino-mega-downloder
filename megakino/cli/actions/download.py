import concurrent.futures
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import List

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from yt_dlp import YoutubeDL

from megakino.core.config import config
from megakino.core.dependencies import check_dependency, show_dependency_error
from megakino.core.models import Episode

console = Console()


@dataclass(frozen=True)
class DownloadResult:
    title: str
    ok: bool
    error: str = ""


def sanitize_filename(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name)
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", normalized).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)

    if not cleaned:
        return "download"

    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if cleaned.upper() in reserved_names:
        cleaned = f"{cleaned}_"

    return cleaned[:180]


def download_task(
    link: str,
    episode: Episode,
    progress: Progress,
    task_id,
    user_agent: str,
) -> DownloadResult:
    safe_title = sanitize_filename(episode.title)
    output_dir = Path(config.download_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{safe_title}.mp4"

    def my_hook(d):
        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total_bytes:
                progress.update(task_id, total=total_bytes)
            downloaded = d.get("downloaded_bytes", 0)
            progress.update(task_id, completed=downloaded)

    def my_pp_hook(d):
        if d["status"] == "started":
            pp = d.get("postprocessor", "Unbekannt")
            if pp in {"Merger", "FFmpegMerger"}:
                progress.update(
                    task_id,
                    description=f"[bold green]Setze Video zusammen...[/bold green] {safe_title}",
                )
            elif pp == "FixupM3u8":
                progress.update(
                    task_id,
                    description=f"[bold cyan]Repariere Video-Format...[/bold cyan] {safe_title}",
                )
            else:
                progress.update(
                    task_id, description=f"[bold magenta]Verarbeite...[/bold magenta] {safe_title}"
                )

    ydl_opts = {
        "format": "bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_file),
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [my_hook],
        "postprocessor_hooks": [my_pp_hook],
        "fragment_retries": 20,
        "retries": 10,
        "concurrent_fragment_downloads": 5,
        "merge_output_format": "mp4",
        "overwrites": False,
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
        "http_headers": {
            "User-Agent": user_agent,
            "Referer": "https://voe.sx/",
            "Origin": "https://voe.sx/",
        },
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        task = next((task for task in progress.tasks if task.id == task_id), None)
        progress.update(
            task_id,
            completed=task.total if task and task.total else 100,
            total=task.total if task and task.total else 100,
            description=f"[green]Fertig:[/green] {safe_title}",
        )
        return DownloadResult(title=safe_title, ok=True)
    except Exception as e:
        progress.update(task_id, description=f"[red]Fehlgeschlagen:[/red] {safe_title}")
        console.print(f"\n[red]Fehler bei {safe_title}: {e}[/red]")
        return DownloadResult(title=safe_title, ok=False, error=str(e))


def download_concurrently(direct_links: List[str], episodes: List[Episode], user_agent: str):
    if not check_dependency("ffmpeg"):
        console.print("[bold red]ACHTUNG: FFmpeg fehlt auf deinem System![/bold red]")
        console.print(
            "Ohne FFmpeg sind die heruntergeladenen MP4-Dateien oft fehlerhaft (Broken Container) und lassen sich nicht abspielen."
        )
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
            task_id = progress.add_task(
                f"[cyan]Lade herunter...[/cyan] {episode.title}", total=None
            )
            tasks.append((link, episode, task_id))

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=config.concurrent_downloads
        ) as executor:
            futures = [
                executor.submit(download_task, link, episode, progress, task_id, user_agent)
                for link, episode, task_id in tasks
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

    successes = sum(1 for result in results if result.ok)
    failures = len(results) - successes
    if failures:
        console.print(
            f"\n[bold yellow]Downloads beendet: {successes} erfolgreich, {failures} fehlgeschlagen.[/bold yellow]"
        )
    else:
        console.print(f"\n[bold green]Alle Downloads abgeschlossen ({successes}).[/bold green]")
