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
import json
import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from app.mcp.server import save_memory, get_context, search_memory, forget_memory, list_memories

console = Console()


async def run_demo():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]TANVELO — Universal AI Memory Layer[/bold cyan]\n"
        "[italic white]Connect Once. Remember Everywhere.[/italic white]\n"
        "[yellow]Phase 1 Hackathon Live Demo (MCP Simulation)[/yellow]",
        border_style="cyan"
    ))

    time.sleep(1)

    # ----------------------------------------------------
    # STEP 1: Connect MCP Server
    # ----------------------------------------------------
    console.print("\n[bold green]► STEP 1: MCP Server Connection[/bold green]")
    console.print("[dim]Connecting MCP-compatible AI Clients (Cursor & Claude Code)...[/dim]")
    time.sleep(0.8)
    console.print("[green]✓ Connected to Tanvelo MCP Server on stdio transport[/green]")

    # ----------------------------------------------------
    # STEP 2 & 3: Save Memory via AI Tool A (Cursor)
    # ----------------------------------------------------
    console.print("\n[bold green]► STEP 2 & 3: AI Tool A (Cursor) — Save Memory[/bold green]")
    console.print("[bold blue]User to AI Tool A (Cursor):[/bold blue] \"Remember that Tanvelo uses FastAPI, Supabase and pgvector.\"")
    
    console.print("\n[dim]AI Tool A invoking MCP Tool: `save_memory`...[/dim]")
    save_result_json = await save_memory(content="Remember that Tanvelo uses FastAPI, Supabase and pgvector.")
    save_data = json.loads(save_result_json)

    table = Table(title="Tanvelo Memory Saved (via AI Tool A)")
    table.add_column("Memory ID", style="cyan")
    table.add_column("Action", style="green")
    table.add_column("Extracted Content", style="white")
    table.add_column("Type", style="yellow")
    table.add_column("Importance", style="magenta")

    for m in save_data.get("stored", []):
        table.add_row(m["id"], save_data["action"], m["content"], m["type"], str(m["importance"]))

    console.print(table)
    time.sleep(1.5)

    # ----------------------------------------------------
    # STEP 4 & 5: Switch to AI Tool B (Claude Code) & Retrieve
    # ----------------------------------------------------
    console.print("\n[bold green]► STEP 4 & 5: Switch to AI Tool B (Claude Code) — Retrieve Context[/bold green]")
    console.print("[bold yellow]User to AI Tool B (Claude Code):[/bold yellow] \"What backend and database am I using for Tanvelo?\"")
    console.print("[dim]Notice: The user did NOT explain the stack to AI Tool B![/dim]")

    console.print("\n[dim]AI Tool B invoking MCP Tool: `get_context(query='Tanvelo stack backend database')`...[/dim]")
    context_output = await get_context(query="Tanvelo backend database stack")

    console.print(Panel(context_output, title="Context Injected from Tanvelo into AI Tool B", border_style="green"))
    time.sleep(1.5)

    # ----------------------------------------------------
    # STEP 6: AI Tool B Answers Correctly
    # ----------------------------------------------------
    console.print("\n[bold green]► STEP 6: AI Tool B Answers User[/bold green]")
    ai_response = (
        "Based on your Tanvelo memory:\n"
        "• Backend: FastAPI\n"
        "• Database: Supabase with pgvector\n"
        "You don't need to configure these again!"
    )
    console.print(Panel(f"[bold white]{ai_response}[/bold white]", title="AI Tool B (Claude Code) Response", border_style="blue"))
    time.sleep(1.5)

    # ----------------------------------------------------
    # STEP 7: Forget Memory
    # ----------------------------------------------------
    console.print("\n[bold green]► STEP 7: AI Tool B Forgets Memory[/bold green]")
    console.print("[bold yellow]User to AI Tool B:[/bold yellow] \"Forget that Tanvelo uses Supabase.\"")

    console.print("\n[dim]AI Tool B invoking MCP Tool: `forget_memory(query='Tanvelo uses Supabase')`...[/dim]")
    forget_result_json = await forget_memory(query="Tanvelo uses Supabase")
    forget_data = json.loads(forget_result_json)

    console.print(f"[bold red]Result:[/bold red] {forget_data['message']}")
    console.print(f"[dim]Forgotten IDs: {forget_data.get('forgotten_ids', [])}[/dim]")

    time.sleep(1)

    # Verify search returns empty/filtered
    console.print("\n[dim]Verifying with `search_memory(query='Tanvelo database')`...[/dim]")
    search_res_json = await search_memory(query="Tanvelo database")
    search_data = json.loads(search_res_json)
    console.print(f"[green]Active Memories Found: {len(search_data.get('memories', []))}[/green]")

    console.print("\n" + "=" * 60)
    console.print("[bold cyan]✓ CORE HACKATHON CONCEPT PROVEN:[/bold cyan]")
    console.print("[italic green]\"Tell one AI once. Tanvelo remembers. Another AI knows.\"[/italic green]")
    console.print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
