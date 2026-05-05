"""CLI entry point for code5."""

from __future__ import annotations

import asyncio
import sys

import click

from .agent import Code5Agent
from .client import MockClient, create_client
from .config import load_config_from_env
from .db import Database
from .reviewer import CommandReviewer, MockReviewer


@click.group()
@click.version_option(version="0.2.0")
def cli() -> None:
    """Code5 - AI Coding Agent"""
    pass


@cli.command()
@click.argument("prompt", required=False)
@click.option("--name", "-n", required=False, help="Session name (required)")
@click.option("--use-mock", is_flag=True, help="Use mock client")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(prompt: str | None, name: str | None, use_mock: bool, verbose: bool) -> None:
    """Run a single prompt or start interactive chat"""
    # Check session name is required
    if not name:
        click.echo("錯誤: 請指定 session 名稱 (-n 或 --name)", err=True)
        click.echo("範例: code5 run -n mysession", err=True)
        sys.exit(1)

    config = load_config_from_env()
    if use_mock:
        config.use_mock = True

    client = MockClient() if use_mock else create_client(config)
    reviewer = CommandReviewer() if not use_mock else MockReviewer()

    # Use session name as session_id
    session_id = name

    # Create agent with session_id for database
    agent = Code5Agent(
        client=client,
        config=config,
        reviewer=reviewer,
        session_id=session_id,
        agent_id="root",
    )

    # Ensure root agent exists in DB
    db = Database.get_instance()
    db.add_agent(session_id, "root", "root")

    if verbose:
        agent.verbose = True

    current_session_id = [session_id]
    current_agent_id = ["root"]
    current_agent = [agent]

    async def run_once():
        db = Database.get_instance()
        if prompt:
            result = await current_agent[0].run(prompt)
            print(result)
        else:
            print(f"Code5 - 對話區塊: {current_session_id[0]} | agent: {current_agent_id[0]}")
            print("指令: /help 說明, /session, /agent 指令")
            print("=" * 50)
            while True:
                try:
                    user_input = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n再見！")
                    break

                if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                    print("再見！")
                    break

                if not user_input:
                    continue

                # 處理特殊命令
                if user_input.lower() == "/help":
                    print("""
=== 可用指令 ===
/help              - 顯示這說明
/history           - 顯示目前 agent 提問
/log               - 顯示目前 agent 完整記錄
/shell <cmd>      - 執行 shell 命令
/session list     - 列出所有 session
/session now      - 顯示目前 session
/session new <name> - 切換到新 session
/session attach <name> - 切換到其他 session
/agent list       - 列出目前 session 的所有 agent
/agent now         - 顯示目前 agent
/agent new <name> - 建立新 agent
/agent attach <name> - 切換到其他 agent
/agent history    - 顯示該 agent 提問
/agent log        - 顯示該 agent 完整記錄
/exit             - 結束對話
""")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /shell <command>
                if user_input.lower().startswith("/shell ") or user_input.lower().startswith("shell "):
                    shell_cmd = user_input.split("shell ", 1)[1].strip()
                    if shell_cmd:
                        import subprocess
                        try:
                            result = subprocess.run(
                                shell_cmd,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=30,
                            )
                            if result.stdout:
                                print(result.stdout)
                            if result.stderr:
                                print(f"[stderr] {result.stderr}")
                            if result.returncode != 0 and not result.stdout:
                                print(f"returncode: {result.returncode}")
                        except subprocess.TimeoutExpired:
                            print("命令執行逾時")
                        except Exception as e:
                            print(f"執行錯誤: {e}")
                    print("=" * 50)
                    continue

                # /session list
                if user_input.lower().startswith("/session list"):
                    db = Database.get_instance()
                    sessions = db.get_all_sessions()
                    print("\n=== 所有 Sessions ===")
                    for s in sessions:
                        marker = " <-" if s["session_id"] == current_session_id[0] else ""
                        print(f"  {s['session_id']} ({s['count']} messages){marker}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /session now
                if user_input.lower() == "/session now":
                    print(f"\n目前 session: {current_session_id[0]}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /session new <name>
                if user_input.lower().startswith("/session new ") or user_input.lower().startswith("session new "):
                    new_name = user_input.split("session new ", 1)[1].strip()
                    current_session_id[0] = new_name
                    current_agent_id[0] = "root"
                    current_agent[0] = Code5Agent(
                        client=client,
                        config=config,
                        reviewer=reviewer,
                        session_id=new_name,
                        agent_id="root",
                    )
                    print(f"\n已切換到 session: {new_name}, agent: root")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /session attach <name>
                if user_input.lower().startswith("/session attach ") or user_input.lower().startswith("session attach "):
                    attach_name = user_input.split("session attach ", 1)[1].strip()
                    db = Database.get_instance()
                    convs = db.get_conversations(attach_name)
                    if not convs:
                        click.echo(f"錯誤: session '{attach_name}' 不存在")
                        print("=" * 50)
                        continue
                    current_session_id[0] = attach_name
                    current_agent_id[0] = "root"
                    current_agent[0] = Code5Agent(
                        client=client,
                        config=config,
                        reviewer=reviewer,
                        session_id=attach_name,
                        agent_id="root",
                    )
                    print(f"\n已切換到 session: {attach_name}, agent: root")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /agent list
                if user_input.lower().startswith("/agent list"):
                    db = Database.get_instance()
                    agents = db.get_agents(current_session_id[0])
                    print("\n=== Agents ===")
                    # Add root manually if not in DB
                    all_agents = [{"agent_id": "root", "name": "root", "created_at": ""}]
                    for a in agents:
                        if a["agent_id"] != "root":
                            all_agents.append(a)
                    for a in all_agents:
                        marker = " <-" if a["agent_id"] == current_agent_id[0] else ""
                        print(f"  {a['agent_id']}{marker}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /agent now
                if user_input.lower() == "/agent now":
                    print(f"\n目前 agent: {current_agent_id[0]}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /agent new <name>
                if user_input.lower().startswith("/agent new ") or user_input.lower().startswith("agent new "):
                    new_agent_name = user_input.split("agent new ", 1)[1].strip()
                    current_agent_id[0] = new_agent_name
                    # Save to DB
                    db = Database.get_instance()
                    db.add_agent(current_session_id[0], new_agent_name, new_agent_name)
                    current_agent[0] = Code5Agent(
                        client=client,
                        config=config,
                        reviewer=reviewer,
                        session_id=current_session_id[0],
                        agent_id=new_agent_name,
                    )
                    print(f"\n已建立並切換到 agent: {new_agent_name}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /agent attach <name>
                if user_input.lower().startswith("/agent attach ") or user_input.lower().startswith("agent attach "):
                    attach_agent_name = user_input.split("agent attach ", 1)[1].strip()
                    # root always exists for any session
                    if attach_agent_name == "root":
                        current_agent_id[0] = "root"
                        current_agent[0] = Code5Agent(
                            client=client,
                            config=config,
                            reviewer=reviewer,
                            session_id=current_session_id[0],
                            agent_id="root",
                        )
                        print(f"\n已切換到 agent: root")
                        print("=" * 50)
                        db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                        continue
                    db = Database.get_instance()
                    # Check if agent exists in DB
                    if attach_agent_name != "root":
                        # For non-root agents, check DB
                        agent_info = db.get_agent(current_session_id[0], attach_agent_name)
                        if not agent_info:
                            print(f"錯誤: agent '{attach_agent_name}' 不存在")
                            print("=" * 50)
                            continue
                    current_agent_id[0] = attach_agent_name
                    current_agent[0] = Code5Agent(
                        client=client,
                        config=config,
                        reviewer=reviewer,
                        session_id=current_session_id[0],
                        agent_id=attach_agent_name,
                    )
                    print(f"\n已切換到 agent: {attach_agent_name}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /agent history - 顯示該 agent 的提問（不含指令）
                if user_input.lower() == "/agent history":
                    db = Database.get_instance()
                    questions = db.get_user_conversations(current_session_id[0], current_agent_id[0])
                    # Filter out /xxx commands, keep only actual questions
                    actual_questions = [q for q in questions if not q.startswith("/")]
                    print(f"\n=== {current_agent_id[0]} 提問歷史 ===")
                    for i, q in enumerate(actual_questions):
                        print(f"{i+1}. {q}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /agent log - 顯示該 agent 的完整記錄
                if user_input.lower() == "/agent log":
                    db = Database.get_instance()
                    # Filter out /xxx commands
                    convs = [c for c in db.get_conversations(current_session_id[0], current_agent_id[0]) if not c["content"].startswith("/")]
                    key_info = db.get_key_info(current_session_id[0], current_agent_id[0])
                    print(f"\n=== {current_agent_id[0]} 完整記錄 ===")
                    if key_info:
                        print(f"\n--- 關鍵資訊 ({len(key_info)} 項) ---")
                        for item in key_info:
                            print(f"  * {item}")
                    print(f"\n--- 對話記錄 ({len(convs)} 項) ---")
                    for c in convs:
                        marker = "你" if c["role"] == "user" else "AI"
                        print(f"[{marker}] {c['content']}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /history - 顯示目前 agent 提問
                if user_input.lower() == "/history":
                    db = Database.get_instance()
                    questions = db.get_user_conversations(current_session_id[0], current_agent_id[0])
                    print(f"\n=== {current_agent_id[0]} 提問 ===")
                    for i, q in enumerate(questions):
                        print(f"{i+1}. {q}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                # /log - 顯示目前 agent 完整記錄
                if user_input.lower() == "/log":
                    db = Database.get_instance()
                    convs = db.get_conversations(current_session_id[0], current_agent_id[0])
                    key_info = db.get_key_info(current_session_id[0], current_agent_id[0])
                    print(f"\n=== {current_agent_id[0]} 完整記錄 ===")
                    if key_info:
                        print(f"\n--- 關鍵資訊 ({len(key_info)} 項) ---")
                        for item in key_info:
                            print(f"  * {item}")
                    print(f"\n--- 對話記錄 ({len(convs)} 項) ---")
                    for c in convs:
                        marker = "你" if c["role"] == "user" else "AI"
                        print(f"[{marker}] {c['content']}")
                    print("=" * 50)
                    db.add_conversation(current_session_id[0], current_agent_id[0], "user", user_input)
                    continue

                print("-" * 50)
                result = await current_agent[0].run(user_input)
                print(result)

        if hasattr(client, 'close'):
            await client.close()

    asyncio.run(run_once())


@cli.command()
@click.argument("action", default="list", required=False)
@click.argument("name", required=False)
def session(action: str, name: str | None) -> None:
    """Session management: list / new <name> / attach <name>"""
    db = Database.get_instance()

    if action == "list" or action is None:
        sessions = db.get_all_sessions()
        if not sessions:
            click.echo("No sessions found")
            return

        click.echo("=== Sessions ===")
        for s in sessions:
            click.echo(f"  {s['session_id']} ({s['count']} messages)")
        return

    if not name:
        click.echo("錯誤: 請指定 session 名稱", err=True)
        sys.exit(1)

    if action == "new":
        click.echo(f"將建立新 session: {name}")
        click.echo(f"請使用: code5 run -n {name}")
        return

    if action == "attach":
        convs = db.get_conversations(name)
        if not convs:
            click.echo(f"錯誤: session '{name}' 不存在", err=True)
            sys.exit(1)
        click.echo(f"Session '{name}' 有 {len(convs)} 條記錄")
        click.echo(f"請使用: code5 run -n {name}")
        return

    click.echo("未知指令. 請使用: code5 session list / session new <name> / session attach <name>")


@cli.command()
@click.option("--model", help="Model to test")
def doctor(model: str | None) -> None:
    """Diagnose configuration"""
    config = load_config_from_env()
    if model:
        config.model = model

    if config.use_mock or not config.api_key:
        click.echo("Using mock client")
        client = MockClient()
    else:
        click.echo(f"Testing NVIDIA API with model: {config.model}")
        client = create_client(config)

    async def test():
        try:
            async with client:
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
