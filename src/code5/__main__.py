"""CLI entry point for code5."""

from __future__ import annotations

import asyncio
import sys

import click

from .agent import Code5Agent
from .client import MockClient, create_client
from .config import load_config_from_env
from .reviewer import CommandReviewer, MockReviewer


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    pass


@cli.command()
@click.argument("message", required=False)
@click.option("--session", "-s", help="Session ID to use")
@click.option("--model", "-m", help="Model to use")
@click.option("--api-key", help="NVIDIA API key")
@click.option("--use-mock", is_flag=True, help="Use mock client for testing")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(message: str | None, session: str | None, model: str | None, api_key: str | None, use_mock: bool, verbose: bool) -> None:
    config = load_config_from_env()

    if api_key:
        config.api_key = api_key
    if model:
        config.model = model
    if use_mock:
        config.use_mock = True

    client = create_client(config)

    reviewer = CommandReviewer() if not use_mock else MockReviewer()

    agent = Code5Agent(client=client, config=config, reviewer=reviewer)

    if verbose:
        agent.verbose = True

    if message:
        result = asyncio.run(agent.run(message))
        print(result)
    else:
        asyncio.run(agent.run_interactive())


@cli.command()
@click.option("--session", "-s", help="Session ID to continue")
def attach(session: str | None) -> None:
    click.echo("Attach feature not yet implemented")


@cli.command()
def session() -> None:
    from .session import SessionManager
    manager = SessionManager()
    sessions = manager.list_sessions()

    if not sessions:
        click.echo("No sessions found")
        return

    click.echo("Sessions:")
    for s in sessions:
        click.echo(f"  {s.session_id[:8]} - {s.updated_at.strftime('%Y-%m-%d %H:%M')}")


@cli.command()
@click.argument("session_id")
def delete_session(session_id: str) -> None:
    from .session import SessionManager
    manager = SessionManager()
    if manager.delete_session(session_id):
        click.echo(f"Deleted session: {session_id}")
    else:
        click.echo(f"Session not found: {session_id}")


@cli.command()
@click.option("--model", help="Model to test")
def doctor(model: str | None) -> None:
    config = load_config_from_env()
    if model:
        config.model = model

    if config.use_mock or not config.api_key:
        click.echo("Using mock client")
        client = MockClient()
    else:
        click.echo(f"Testing NVIDIA API with model: {config.model}")
        client = create_client(config)

    async def test() -> None:
        try:
            result = await client.generate("Say 'Hello, Code5!'", "")
            click.echo(f"Success: {result}")
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    asyncio.run(test())


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
