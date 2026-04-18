import asyncio
import sys

def main():
    # First, check if basic libraries for error reporting are available
    try:
        from megakino.core.dependencies import check_python_libraries
        check_python_libraries()
    except ImportError:
        print("Error: Essential components of Megakino-Downloader are missing.")
        print("Please run: pip install -e .")
        sys.exit(1)

    try:
        from megakino.cli.app import interactive_app
        # Run the app
        asyncio.run(interactive_app())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
