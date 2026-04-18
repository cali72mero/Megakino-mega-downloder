import asyncio
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console

from megakino.api.client import APIClient
from megakino.api.scraper import search_for_movie, get_media_details
from megakino.api.extractors.megakino import megakino_get_direct_link
from megakino.api.extractors.voe import voe_get_direct_link
from megakino.core.config import config, config_manager, CONFIG_FILE
from megakino.cli.actions.download import download_concurrently
from megakino.cli.actions.watch import watch
from megakino.cli.actions.syncplay import syncplay

console = Console()

async def check_for_updates(client: APIClient):
    from rich.panel import Panel
    from megakino import __version__ as LOCAL_VERSION
    
    remote_version = await client.get_latest_pypi_version()
    if remote_version and remote_version != LOCAL_VERSION:
        console.print(Panel(
            f"[bold green]✨ Eine neue Version ist verfügbar! ({remote_version})[/bold green]\n"
            f"[yellow]Du nutzt aktuell Version: {LOCAL_VERSION}[/yellow]\n\n"
            f"Zum Aktualisieren tippe:\n"
            f"[bold cyan]pip install --upgrade megakino-mega-downloader[/bold cyan]",
            title="Update Verfügbar",
            border_style="green"
        ))
        # Give the user a tiny bit of time to read it
        await asyncio.sleep(0.5)

def show_uninstall_guide():
    console.print("\n[bold red]=== DEINSTALLATIONS-HILFE ===[/bold red]")
    console.print("[yellow]So entfernst du das Programm und alle Hilfsprogramme vollständig:[/yellow]")
    console.print("\n[bold cyan]1. Das Programm über PIP löschen:[/bold cyan]")
    console.print("   Öffne dein Terminal und tippe:")
    console.print("   [b]pip uninstall megakino-mega-downloader[/b]")
    console.print("\n[bold cyan]2. Virtuelle Umgebung (venv) und Programm-Ordner löschen:[/bold cyan]")
    console.print("   Wenn du das Programm in einem eigenen Ordner installiert hast,")
    console.print("   lösche einfach den gesamten Ordner (inklusive des 'venv'-Ordners).")
    console.print("\n[bold cyan]3. Externe System-Programme (Homebrew, Winget, Apt) löschen:[/bold cyan]")
    console.print("   Diese Programme wurden NICHT über pip, sondern über dein System installiert:")
    console.print("   [b]macOS (Homebrew):[/b] brew uninstall ffmpeg mpv syncplay")
    console.print("   [b]Windows (Winget):[/b] winget uninstall ffmpeg mpv")
    console.print("   [b]Linux (Apt):[/b] sudo apt remove ffmpeg mpv")
    console.print("\n[bold cyan]4. Gespeicherte Einstellungen (Settings) löschen:[/bold cyan]")
    console.print(f"   Deine Einstellungen liegen hier: [b]{CONFIG_FILE}[/b]")
    console.print("   Lösche diese Datei, um alle persönlichen Configs zu entfernen.")
    console.print("\n[green]Danach ist alles restlos von deinem PC entfernt![/green]\n")
    input("Drücke ENTER, um zurück zum Menü zu gehen...")

async def interactive_app():
    if config.show_animations:
        console.print("[bold cyan]✨ Loading Megakino Downloader... ✨[/bold cyan]")
        await asyncio.sleep(0.5)
    
    console.print("[bold cyan]Welcome to Megakino Downloader![/bold cyan]")
    
    async with APIClient() as client:
        # Check for updates from PyPI at startup
        await check_for_updates(client)
        
        while True:
            action = await inquirer.select(
                message="What would you like to do?",
                choices=["Search Movie/Series", "Settings", "Deinstallations-Hilfe", "Exit"],
                default="Search Movie/Series"
            ).execute_async()
            
            if action == "Exit":
                break
            elif action == "Settings":
                await settings_menu()
            elif action == "Deinstallations-Hilfe":
                show_uninstall_guide()
            elif action == "Search Movie/Series":
                await search_flow(client)

async def settings_menu():
    while True:
        choice = await inquirer.select(
            message="Settings:",
            choices=[
                f"Download Path [{config.download_path}]",
                f"Concurrent Downloads [{config.concurrent_downloads}]",
                f"Preferred Provider [{config.preferred_provider}]",
                f"Menü-Effekte (Animationen) [{'AN' if config.show_animations else 'AUS'}]",
                "Back"
            ]
        ).execute_async()

        if choice == "Back":
            break
        elif choice.startswith("Download Path"):
            new_path = await inquirer.text(message="Enter new download path:", default=config.download_path).execute_async()
            config.download_path = new_path
        elif choice.startswith("Concurrent Downloads"):
            new_val = await inquirer.number(
                message="Max concurrent downloads:",
                min_allowed=1,
                max_allowed=10,
                default=config.concurrent_downloads
            ).execute_async()
            config.concurrent_downloads = int(new_val)
        elif choice.startswith("Preferred Provider"):
            new_prov = await inquirer.select(
                message="Select preferred provider:",
                choices=["Megakino", "VOE"],
                default=config.preferred_provider
            ).execute_async()
            config.preferred_provider = new_prov
        elif choice.startswith("Menü-Effekte"):
            console.print("\n[bold yellow]WICHTIG: Erklärung zu Menü-Effekten:[/bold yellow]")
            console.print("Diese Einstellung hat [bold red]NICHTS[/bold red] mit 'Anime' zu tun!")
            console.print("Es geht nur um das Aussehen des Programms (Lade-Animationen und Farben im Terminal).")
            console.print(" - [cyan]AN[/cyan]: Wenn du einen schnellen PC hast und es schick aussehen soll.")
            console.print(" - [cyan]AUS[/cyan]: Wenn das Terminal flackert oder du es lieber ganz schlicht magst.\n")
            
            config.show_animations = await inquirer.confirm(
                message="Menü-Effekte / Animationen einschalten?",
                default=config.show_animations
            ).execute_async()
        
        config_manager.save()
        console.print("[green]Settings saved![/green]")

async def search_flow(client: APIClient):
    query = await inquirer.text(message="Enter movie or series name:").execute_async()
    if not query or not query.strip():
        console.print("[yellow]Query cannot be empty![/yellow]")
        return
    
    query = query.strip()
    with console.status(f"[bold green]Searching for '{query}'...[/bold green]"):
        try:
            results = await search_for_movie(query, client)
        except Exception as e:
            console.print(f"[red]Search failed: {e}[/red]")
            return
        
    if not results:
        console.print("[red]No results found for your search.[/red]")
        return
        
    choices = [Choice(value=res.url, name=res.title) for res in results]
    choices.append(Choice(value=None, name="Cancel"))
    
    selected_url = await inquirer.select(
        message="Select a result:",
        choices=choices
    ).execute_async()
    
    if not selected_url:
        return
        
    with console.status("[bold green]Fetching details...[/bold green]"):
        details = await get_media_details(selected_url, client)
        
    if not details.episodes:
        console.print("[red]No playable media found for this selection.[/red]")
        return
        
    if len(details.episodes) == 1:
        # If it's just a movie (1 item), skip the annoying checkbox and auto-select it!
        selected_episodes = details.episodes
        console.print(f"[bold green]Auto-selected Movie:[/bold green] {selected_episodes[0].title}")
    else:
        ep_choices = [Choice(value=ep, name=ep.title) for ep in details.episodes]
        console.print("\n[bold yellow]💡 TIP: You MUST press SPACE to select an item (a filled circle will appear) BEFORE pressing ENTER![/bold yellow]")
        selected_episodes = await inquirer.checkbox(
            message="Select episodes (SPACE = Select, ENTER = Confirm, CTRL+A = Select All):",
            choices=ep_choices,
            validate=lambda result: len(result) > 0,
            invalid_message="ERROR: You didn't select anything! Press SPACE first, then ENTER."
        ).execute_async()
    
    if not selected_episodes:
        return
        
    action = await inquirer.select(
        message="What do you want to do with the selected episodes?",
        choices=[
            Choice("Watch", "Watch in MPV"),
            Choice("Download", f"Download to {config.download_path}"),
            Choice("Syncplay", "Watch with friends (Syncplay)")
        ],
        default="Watch"
    ).execute_async()
    
    provider = await inquirer.select(
        message="Select provider:",
        choices=["Megakino", "VOE"],
        default=config.preferred_provider
    ).execute_async()
    
    direct_links = []
    final_episodes = []
    
    with console.status("[bold green]Suche nach funktionierenden Streams...[/bold green]"):
        for ep in selected_episodes:
            if isinstance(ep, dict):
                from megakino.core.models import Episode
                ep = Episode(**ep)
                
            link = None
            primary = provider
            secondary = "VOE" if provider == "Megakino" else "Megakino"
            
            # Try Primary Provider
            if primary == "Megakino":
                link = await megakino_get_direct_link(ep.url, client)
            else:
                link = await voe_get_direct_link(ep.url, client)
                
            # AUTO-FALLBACK: If primary failed, try secondary
            if not link:
                console.print(f"[yellow]Hinweis: {primary} Link für '{ep.title}' nicht gefunden. Versuche Fallback auf {secondary}...[/yellow]")
                if secondary == "Megakino":
                    link = await megakino_get_direct_link(ep.url, client)
                else:
                    link = await voe_get_direct_link(ep.url, client)
            
            if link:
                direct_links.append(link)
                final_episodes.append(ep)
            else:
                console.print(f"[bold red]Fehler: Kein funktionierender Link für '{ep.title}' bei beiden Providern gefunden![/bold red]")
                
    if not direct_links:
        console.print("[red]No valid links could be extracted.[/red]")
        return
        
    if action == "Watch":
        watch(direct_links, final_episodes)
    elif action == "Download":
        download_concurrently(direct_links, final_episodes, client.ua)
    elif action == "Syncplay":
        syncplay(direct_links, final_episodes)
