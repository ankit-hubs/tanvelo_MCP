"""
Tanvelo Unified Command Line Interface (CLI)
Provides administration, server orchestration, key management, and memory operations.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.config import settings
from app.database import async_session_factory, init_db, check_database_health
from app.models.user import User
from app.models.api_key import ApiKey
from app.schemas.memory import MemorySaveRequest
from app.services.auth_service import create_user_and_api_key, list_user_api_keys, revoke_user_api_key
from app.services.memory_service import memory_service

console = Console()


def run_async(coro):
    return asyncio.run(coro)


# --- Commands ---

def cmd_serve(args):
    """Start the FastAPI backend server."""
    import uvicorn
    console.print(Panel.fit(
        f"[bold cyan]Starting Tanvelo Memory Backend[/bold cyan]\n"
        f"[green]Host:[/green] {args.host}\n"
        f"[green]Port:[/green] {args.port}\n"
        f"[green]Environment:[/green] {settings.TANVELO_ENV}\n"
        f"[green]Docs:[/green] http://{args.host}:{args.port}/docs",
        title="Tanvelo Server",
        border_style="cyan"
    ))
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1
    )


def cmd_mcp(args):
    """Start the Model Context Protocol (MCP) server."""
    from app.mcp.runner import main as mcp_main
    sys.argv = ["tanvelo-mcp", "--transport", args.transport, "--host", args.host, "--port", str(args.port)]
    if args.api_key:
        sys.argv.extend(["--api-key", args.api_key])
    mcp_main()


async def _db_init():
    console.print("[yellow]Initializing Tanvelo database schema...[/yellow]")
    await init_db()
    ok, msg = await check_database_health()
    if ok:
        console.print("[bold green]✓ Database initialized and healthy![/bold green]")
    else:
        console.print(f"[bold red]✗ Database error: {msg}[/bold red]")


def cmd_db_init(args):
    run_async(_db_init())


async def _keys_create(email: str, name: str):
    await init_db()
    async with async_session_factory() as db:
        user, key_model, raw_key = await create_user_and_api_key(
            db=db,
            email=email,
            key_name=name
        )
        console.print(Panel(
            f"[bold green]API Key Generated Successfully![/bold green]\n\n"
            f"[bold white]Key ID:[/bold white]   {key_model.id}\n"
            f"[bold white]User ID:[/bold white]  {user.id}\n"
            f"[bold white]Email:[/bold white]    {user.email or '(none)'}\n"
            f"[bold white]Name:[/bold white]     {key_model.name}\n\n"
            f"[bold yellow]API Key:[/bold yellow]  [bold cyan]{raw_key}[/bold cyan]\n\n"
            f"[dim]Please store this key safely. It will not be shown again.[/dim]",
            title="Tanvelo API Key",
            border_style="green"
        ))


def cmd_keys_create(args):
    run_async(_keys_create(args.email, args.name))


async def _keys_list(email: str):
    await init_db()
    async with async_session_factory() as db:
        from sqlalchemy import select
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalars().first()
        if not user:
            console.print(f"[red]User with email '{email}' not found.[/red]")
            return

        keys = await list_user_api_keys(db=db, user_id=user.id)
        table = Table(title=f"API Keys for {email}")
        table.add_column("Key ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Masked Key", style="yellow")
        table.add_column("Created At", style="green")
        table.add_column("Status", style="bold")

        for k in keys:
            status_style = "[green]Active[/green]" if k.is_active else "[red]Revoked[/red]"
            table.add_row(k.id, k.name, k.masked_key, k.created_at.strftime("%Y-%m-%d %H:%M"), status_style)

        console.print(table)


def cmd_keys_list(args):
    run_async(_keys_list(args.email))


async def _keys_revoke(key_id: str, email: str):
    await init_db()
    async with async_session_factory() as db:
        from sqlalchemy import select
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalars().first()
        if not user:
            console.print(f"[red]User with email '{email}' not found.[/red]")
            return

        revoked = await revoke_user_api_key(db=db, user_id=user.id, key_id=key_id)
        if revoked:
            console.print(f"[bold green]✓ Key '{key_id}' successfully revoked.[/bold green]")
        else:
            console.print(f"[red]✗ Key '{key_id}' not found or already revoked.[/red]")


def cmd_keys_revoke(args):
    run_async(_keys_revoke(args.key_id, args.email))


async def _memory_save(content: str, email: str, type_val: str, project_id: str):
    await init_db()
    async with async_session_factory() as db:
        from sqlalchemy import select
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalars().first()
        if not user:
            user, _, _ = await create_user_and_api_key(db=db, email=email)

        req = MemorySaveRequest(
            content=content,
            type=type_val,
            project_id=project_id,
            source="cli"
        )
        res = await memory_service.save_memory(db=db, user_id=user.id, request=req)
        console.print(f"[green]Action:[/green] {res.action}")
        console.print(f"[green]Memory ID:[/green] {res.memory_id}")
        console.print(f"[green]Message:[/green] {res.message}")


def cmd_memory_save(args):
    run_async(_memory_save(args.content, args.email, args.type, args.project))


async def _memory_search(query: str, email: str, limit: int):
    await init_db()
    async with async_session_factory() as db:
        from sqlalchemy import select
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalars().first()
        if not user:
            console.print(f"[red]User '{email}' not found.[/red]")
            return

        res = await memory_service.search_memories(db=db, user_id=user.id, query=query, limit=limit)
        table = Table(title=f"Search Results for: '{query}'")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Content", style="white")
        table.add_column("Similarity", style="yellow")
        table.add_column("Score", style="green")

        for m in res.memories:
            sim_str = f"{m.similarity:.2f}" if m.similarity is not None else "-"
            score_str = f"{m.hybrid_score:.2f}" if m.hybrid_score is not None else "-"
            table.add_row(m.id, m.type, m.content, sim_str, score_str)

        console.print(table)


def cmd_memory_search(args):
    run_async(_memory_search(args.query, args.email, args.limit))


async def _memory_list(email: str, limit: int, offset: int, project_id: str, type_val: str):
    await init_db()
    async with async_session_factory() as db:
        from sqlalchemy import select
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalars().first()
        if not user:
            console.print(f"[red]User '{email}' not found.[/red]")
            return

        res = await memory_service.list_memories(
            db=db,
            user_id=user.id,
            limit=limit,
            offset=offset,
            project_id=project_id,
            memory_type=type_val
        )
        table = Table(title=f"Memories for {email} (Total: {res.total})")
        table.add_column("Memory ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Content", style="white")
        table.add_column("Importance", style="yellow")
        table.add_column("Project", style="green")
        table.add_column("Created", style="dim")

        for m in res.memories:
            table.add_row(
                m.id,
                m.type,
                m.content,
                f"{m.importance:.2f}",
                m.project_id or "-",
                m.created_at.strftime("%Y-%m-%d %H:%M")
            )

        console.print(table)


def cmd_memory_list(args):
    run_async(_memory_list(args.email, args.limit, args.offset, args.project, args.type))


async def _memory_update(memory_id: str, content: str, type_val: str, importance: float, email: str):
    await init_db()
    async with async_session_factory() as db:
        from sqlalchemy import select
        from app.schemas.memory import MemoryUpdateRequest
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalars().first()
        if not user:
            console.print(f"[red]User '{email}' not found.[/red]")
            return

        req = MemoryUpdateRequest(
            content=content,
            type=type_val,
            importance=importance
        )
        updated = await memory_service.update_memory(
            db=db,
            user_id=user.id,
            memory_id=memory_id,
            request=req
        )
        if updated:
            console.print(f"[bold green]✓ Memory '{memory_id}' updated successfully![/bold green]")
            console.print(f"[cyan]Content:[/cyan] {updated.content}")
            console.print(f"[cyan]Type:[/cyan] {updated.type} | [cyan]Importance:[/cyan] {updated.importance:.2f}")
        else:
            console.print(f"[bold red]✗ Memory '{memory_id}' not found.[/bold red]")


def cmd_memory_update(args):
    run_async(_memory_update(args.memory_id, args.content, args.type, args.importance, args.email))


async def _memory_forget(memory_id: str, query: str, email: str):
    await init_db()
    async with async_session_factory() as db:
        from sqlalchemy import select
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalars().first()
        if not user:
            console.print(f"[red]User '{email}' not found.[/red]")
            return

        res = await memory_service.forget_memory(
            db=db,
            user_id=user.id,
            memory_id=memory_id,
            query=query
        )
        if res.success:
            console.print(f"[bold green]✓ {res.message}[/bold green]")
            if res.forgotten_ids:
                console.print(f"[dim]Forgotten IDs: {', '.join(res.forgotten_ids)}[/dim]")
        else:
            console.print(f"[bold red]✗ {res.message}[/bold red]")


def cmd_memory_forget(args):
    run_async(_memory_forget(args.memory_id, args.query, args.email))


async def _memory_stats(email: str):
    await init_db()
    async with async_session_factory() as db:
        from sqlalchemy import select
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalars().first()
        if not user:
            console.print(f"[red]User '{email}' not found.[/red]")
            return

        stats = await memory_service.get_stats(db=db, user_id=user.id)
        console.print(Panel(
            f"[bold white]Total Memories:[/bold white]   {stats.total_memories}\n"
            f"[bold white]Active Memories:[/bold white]  {stats.active_memories}\n"
            f"[bold white]Expired Memories:[/bold white] {stats.expired_memories}\n\n"
            f"[bold cyan]Categories:[/bold cyan]\n" +
            ("\n".join(f"  • {k}: {v}" for k, v in stats.by_type.items()) if stats.by_type else "  (none)") + "\n\n" +
            f"[bold cyan]Projects:[/bold cyan]\n" +
            ("\n".join(f"  • {k}: {v}" for k, v in stats.by_project.items()) if stats.by_project else "  (none)"),
            title=f"Tanvelo Memory Statistics ({email})",
            border_style="cyan"
        ))


def cmd_memory_stats(args):
    run_async(_memory_stats(args.email))


def main():
    parser = argparse.ArgumentParser(prog="tanvelo", description="Tanvelo Enterprise CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # serve
    p_serve = subparsers.add_parser("serve", help="Start the FastAPI backend server")
    p_serve.add_argument("--host", default=settings.HOST, help="Host to bind")
    p_serve.add_argument("--port", type=int, default=settings.PORT, help="Port to bind")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload")
    p_serve.add_argument("--workers", type=int, default=1, help="Worker processes")
    p_serve.set_defaults(func=cmd_serve)

    # mcp
    p_mcp = subparsers.add_parser("mcp", help="Start the MCP Server")
    p_mcp.add_argument("--transport", choices=["stdio", "sse", "streamable_http"], default="stdio")
    p_mcp.add_argument("--host", default="0.0.0.0", help="Host to bind for SSE/HTTP")
    p_mcp.add_argument("--port", type=int, default=settings.MCP_PORT)
    p_mcp.add_argument("--api-key", type=str, default=None)
    p_mcp.set_defaults(func=cmd_mcp)

    # db
    p_db = subparsers.add_parser("db", help="Database management")
    p_db_sub = p_db.add_subparsers()
    p_db_init = p_db_sub.add_parser("init", help="Initialize tables and schema")
    p_db_init.set_defaults(func=cmd_db_init)

    # keys
    p_keys = subparsers.add_parser("keys", help="API Key management")
    p_keys_sub = p_keys.add_subparsers()

    p_k_create = p_keys_sub.add_parser("create", help="Create a new API Key")
    p_k_create.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_k_create.add_argument("--name", default="Default Key", help="Key name")
    p_k_create.set_defaults(func=cmd_keys_create)

    p_k_list = p_keys_sub.add_parser("list", help="List user API keys")
    p_k_list.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_k_list.set_defaults(func=cmd_keys_list)

    p_k_revoke = p_keys_sub.add_parser("revoke", help="Revoke an API key")
    p_k_revoke.add_argument("key_id", help="Key ID to revoke")
    p_k_revoke.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_k_revoke.set_defaults(func=cmd_keys_revoke)

    # memory
    p_mem = subparsers.add_parser("memory", help="Memory operations")
    p_mem_sub = p_mem.add_subparsers()

    p_m_save = p_mem_sub.add_parser("save", help="Save a memory")
    p_m_save.add_argument("content", help="Memory content to save")
    p_m_save.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_m_save.add_argument("--type", default=None, help="Memory category")
    p_m_save.add_argument("--project", default=None, help="Project ID")
    p_m_save.set_defaults(func=cmd_memory_save)

    p_m_list = p_mem_sub.add_parser("list", help="List all stored memories")
    p_m_list.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_m_list.add_argument("--limit", type=int, default=20, help="Max results")
    p_m_list.add_argument("--offset", type=int, default=0, help="Offset")
    p_m_list.add_argument("--project", default=None, help="Filter by project")
    p_m_list.add_argument("--type", default=None, help="Filter by category")
    p_m_list.set_defaults(func=cmd_memory_list)

    p_m_search = p_mem_sub.add_parser("search", help="Search memories")
    p_m_search.add_argument("query", help="Search query")
    p_m_search.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_m_search.add_argument("--limit", type=int, default=5, help="Result limit")
    p_m_search.set_defaults(func=cmd_memory_search)

    p_m_update = p_mem_sub.add_parser("update", help="Update an existing memory")
    p_m_update.add_argument("memory_id", help="ID of memory to update")
    p_m_update.add_argument("--content", default=None, help="New content")
    p_m_update.add_argument("--type", default=None, help="New category")
    p_m_update.add_argument("--importance", type=float, default=None, help="New importance (0.0 - 1.0)")
    p_m_update.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_m_update.set_defaults(func=cmd_memory_update)

    p_m_forget = p_mem_sub.add_parser("forget", help="Forget/delete a memory")
    p_m_forget.add_argument("--id", dest="memory_id", default=None, help="Memory ID to delete")
    p_m_forget.add_argument("--query", default=None, help="Natural language query to forget")
    p_m_forget.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_m_forget.set_defaults(func=cmd_memory_forget)

    p_m_stats = p_mem_sub.add_parser("stats", help="Memory statistics")
    p_m_stats.add_argument("--email", default="developer@tanvelo.ai", help="User email")
    p_m_stats.set_defaults(func=cmd_memory_stats)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

