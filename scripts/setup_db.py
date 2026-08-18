import os
import sys
import ctypes

# Preload libstdc++.so.6 if required in minimal nix environments without polluting shell LD_LIBRARY_PATH
_candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv/lib/libstdc++.so.6"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv/lib/python3.11/site-packages/libstdc++.so.6"),
    "/nix/store/03h8f1wmpb86s9v8xd0lcb7jnp7nwm6l-idx-env-fhs/usr/lib/libstdc++.so.6",
    "/nix/store/09kfkia2q352fqdj7g2bf6aljzb85rx2-idx-env-fhs/usr/lib/libstdc++.so.6",
]

for _p in _candidates:
    if os.path.exists(_p):
        try:
            ctypes.CDLL(_p)
            break
        except Exception:
            pass

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.database import init_db, async_session_factory
from app.services.auth_service import create_user_and_api_key

console = Console()


async def main():
    console.print("[bold cyan]Initializing Tanvelo Database...[/bold cyan]")
    await init_db()
    console.print("[green]✓ Database tables created/verified successfully.[/green]")

    async with async_session_factory() as db:
        user, api_key_model, raw_key = await create_user_and_api_key(
            db=db,
            email="developer@tanvelo.ai",
            key_name="Hackathon Demo Key"
        )

        table = Table(title="Tanvelo Provisioned Credentials")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("User ID", user.id)
        table.add_row("User Email", user.email)
        table.add_row("Key Name", api_key_model.name)
        table.add_row("API Key (Raw)", raw_key)
        table.add_row("Key Hash (SHA-256)", api_key_model.key_hash[:16] + "...")

        console.print(table)
        console.print(Panel.fit(
            f"[bold yellow]Add this to your environment or MCP configuration:[/bold yellow]\n\n"
            f"export TANVELO_API_KEY=\"{raw_key}\"",
            title="Next Step"
        ))


if __name__ == "__main__":
    asyncio.run(main())
