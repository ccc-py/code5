"""Simple CLI mode - works like Hermes Agent"""

import asyncio
import sys

import click

from .agent import Code5Agent
from .client import MockClient, create_client
from .config import load_config_from_env
from .reviewer import CommandReviewer, MockReviewer


@click.command()
@click.argument("prompt", required=False)
@click.option("--use-mock", is_flag=True, help="Use mock client")
def cli(prompt: str | None, use_mock: bool) -> None:
    """Hermes-style simple CLI - read from stdin, print to stdout"""
    config = load_config_from_env()
    if use_mock:
        config.use_mock = True

    client = MockClient() if use_mock else create_client(config)
    reviewer = CommandReviewer() if not use_mock else MockReviewer()
    agent = Code5Agent(client=client, config=config, reviewer=reviewer)

    if prompt:
        user_input = prompt
    else:
        print("Code5 CLI - 輸入你的問題 (Ctrl+C 離開)")
        print("-" * 40)
        user_input = input("> ").strip()

    while user_input:
        print("-" * 40)

        async def run_agent():
            return await agent.run(user_input)

        result = asyncio.run(run_agent())
        print(result)

        print("-" * 40)
        user_input = input("> ").strip()


@click.command()
@click.argument("prompt", required=False)
@click.option("--use-mock", is_flag=True, help="Use mock client")
def chat(prompt: str | None, use_mock: bool) -> None:
    """Simple chat mode - input on one line, output below"""
    config = load_config_from_env()
    if use_mock:
        config.use_mock = True

    client = MockClient() if use_mock else create_client(config)
    reviewer = CommandReviewer() if not use_mock else MockReviewer()
    agent = Code5Agent(client=client, config=config, reviewer=reviewer)

    loop = True
    while loop:
        try:
            if prompt:
                user_input = prompt
                loop = False
            else:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
        except (EOFError, KeyboardInterrupt):
            print("\n再見！")
            break

        async def run_agent():
            return await agent.run(user_input)

        result = asyncio.run(run_agent())
        print(result)

        if not loop:
            break


def main():
    """Entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "tui":
            click.echo("TUI 已移除，請使用: code5 chat")
            sys.argv[1] = "chat"
    cli()


if __name__ == "__main__":
    cli()
