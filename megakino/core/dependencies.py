import platform
import shutil

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

INSTALL_INSTRUCTIONS = {
    "mpv": {
        "Windows": "Download from https://mpv.io/installation/ or use 'winget install mpv'",
        "Darwin": "brew install mpv",
        "Linux": "sudo apt install mpv (Debian/Ubuntu) or sudo pacman -S mpv (Arch)",
    },
    "syncplay": {
        "Windows": "Download from https://syncplay.pl/download/",
        "Darwin": "brew install --cask syncplay",
        "Linux": "Download the AppImage from https://syncplay.pl/download/",
    },
    "yt-dlp": {
        "Windows": "pip install yt-dlp",
        "Darwin": "brew install yt-dlp or pip install yt-dlp",
        "Linux": "sudo wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp",
    },
    "ffmpeg": {
        "Windows": "Download from https://ffmpeg.org/download.html or use 'winget install ffmpeg'",
        "Darwin": "brew install ffmpeg",
        "Linux": "sudo apt install ffmpeg (Debian/Ubuntu) or sudo pacman -S ffmpeg (Arch)",
    },
}


def check_dependency(name: str) -> bool:
    return shutil.which(name) is not None


def show_dependency_error(missing_executables):
    table = Table(title="Missing System Dependencies", show_header=True, header_style="bold red")
    table.add_column("Dependency", style="cyan")
    table.add_column("Install Command / Instructions", style="green")

    os_name = platform.system()

    for name in missing_executables:
        instruction = INSTALL_INSTRUCTIONS.get(name, {}).get(os_name, "Visit official website")
        table.add_row(name, instruction)

    console.print(Panel(table, border_style="red", title="System Requirements Not Met"))
    console.print("\n[yellow]Note: After installing these, please restart the program.[/yellow]")
    exit(1)


def assert_system_dependencies():
    # yt-dlp is used as a library, but checking for the CLI can be helpful too
    # but primarily we need mpv for 'Watch' and syncplay for 'Syncplay'
    # We check them only when the user tries to use them, OR at startup?
    # Startup check is better for a "pro" feel.

    # We don't exit here immediately because 'Download' doesn't need mpv/syncplay.
    # However, for a complete experience, let's list them.
    pass


def check_python_libraries():
    # Map install names to their actual Python import names
    required = {
        "yt-dlp": "yt_dlp",
        "httpx": "httpx",
        "beautifulsoup4": "bs4",
        "fake_useragent": "fake_useragent",
        "rich": "rich",
        "InquirerPy": "InquirerPy",
        "appdirs": "appdirs",
        "cachetools": "cachetools",
    }
    missing = []
    import importlib.util

    for install_name, import_name in required.items():
        if importlib.util.find_spec(import_name) is None:
            missing.append(install_name)

    if missing:
        console.print(
            Panel(
                f"[bold red]Missing Python Libraries:[/bold red]\n{', '.join(missing)}",
                border_style="red",
            )
        )
        console.print(
            "\n[bold green]To install all dependencies in a virtual environment, run:[/bold green]"
        )
        console.print("1. python -m venv venv")
        console.print("2. source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        console.print("3. pip install megakino-mega-downloader")
        console.print("\nOr manually:")
        console.print(f"pip install {' '.join(missing)}")
        exit(1)
