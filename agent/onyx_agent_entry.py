"""Stable PyInstaller entry point for the packaged Onyx agent."""
from onyx_agent.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
