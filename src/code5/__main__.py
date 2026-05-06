"""CLI entry point for code5."""

from __future__ import annotations

import asyncio
import sys
import threading

import click

from .agent import Code5Agent
from .client import MockClient, create_client
from .config import load_config_from_env
from .db import Database
from .reviewer import CommandReviewer, MockReviewer


@click.command()
@click.argument("args", nargs=-1)
@click.option("--mock", is_flag=True, help="Use mock client")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def main(args: tuple, mock: bool, verbose: bool) -> None:
    """Code5 - AI Coding Agent"""

    # Parse command and name from args
    if args:
        command = args[0] if args[0] else None
        name = args[1] if len(args) > 1 else None
    else:
        command = None
        name = None
    if command is None:
        click.echo("用法:")
        click.echo("  code5 /new <name>           # 新 session，進入互動")
        click.echo("  code5 /attach <name>        # 繼續 session，進入互動")
        click.echo("  code5 /new <name> <<EOF    # 新 session + 執行")
        click.echo("  code5 /attach <name> <<EOF  # 指定 session + 執行")
        click.echo("  code5 /version             # 顯示版本")
        click.echo("  code5 /help               # 顯示幫助")
        click.echo("  code5 /doctor              # 診斷設定")
        click.echo("  code5 /list                # 列出所有 session")
        return

    command = command.lower()

    # /version
    if command in ("--version", "/version", "-v"):
        from . import __version__
        click.echo(f"code5 {__version__}")
        return

    # /help
    if command in ("--help", "/help", "-h"):
        click.echo("""
Code5 - AI Coding Agent

用法:
  code5 /new <name>           # 新 session，進入互動
  code5 /attach <name>        # 繼續 session，進入互動
  code5 /new <name> <<EOF    # 新 session + 執行
  code5 /attach <name> <<EOF  # 指定 session + 執行
  code5 /version             # 顯示版本
  code5 /help               # 顯示幫助
  code5 /doctor              # 診斷設定
  code5 /list                # 列出所有 session

互動模式指令:
  /help              - 顯示這說明
  /history           - 顯示目前 agent 提問
  /log               - 顯示目前 agent 完整記錄
  /shell <cmd>       - 執行 shell 命令
  /list              - 列出所有 session
  /now              - 顯示目前 session
  /new <name>       - 切換到新 session
  /attach <name>    - 切換到其他 session
  /agent list        - 列出目前 session 的所有 agent
  /agent new <name>  - 建立新 agent
  /agent attach <name> - 切換到其他 agent
  /agent history    - 顯示該 agent 提問
  /agent log         - 顯示該 agent 完整記錄
  /exit              - 結束對話
""")
        return

    # /doctor
    if command in ("/doctor", "doctor"):
        config = load_config_from_env()
        if mock:
            config.use_mock = True

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
        return

    # /list - 列出所有 session
    if command in ("/list", "list", "ls"):
        db = Database.get_instance()
        sessions = db.get_all_sessions()
        if not sessions:
            click.echo("No sessions found")
            return

        click.echo("=== Sessions ===")
        for s in sessions:
            click.echo(f"  {s['session_id']} ({s['count']} messages)")
        return

    # /new - 新 session
    if command in ("/new", "new"):
        if not name:
            click.echo("錯誤: 請指定 session 名稱", err=True)
            sys.exit(1)
        run_session("new", name, mock, verbose)
        return

    # /attach - 繼續 session
    if command in ("/attach", "attach"):
        if not name:
            click.echo("錯誤: 請指定 session 名稱", err=True)
            sys.exit(1)
        db = Database.get_instance()
        convs = db.get_conversations(name)
        if not convs:
            click.echo(f"錯誤: session '{name}' 不存在", err=True)
            sys.exit(1)
        run_session("attach", name, mock, verbose)
        return

    # Unknown command
    click.echo(f"未知指令: {command}", err=True)
    click.echo("使用 code5 /help 查看說明")
    sys.exit(1)


def run_session(command: str, session_name: str, mock: bool, verbose: bool, bg: bool = False) -> None:
    """Run session in interactive or batch mode."""
    config = load_config_from_env()
    if mock:
        config.use_mock = True

    client = MockClient() if mock else create_client(config)
    reviewer = MockReviewer() if mock else CommandReviewer()

    session_id = session_name
    db = Database.get_instance()

    if command in ("/attach", "attach"):
        convs = db.get_conversations(session_id)
        if not convs:
            click.echo(f"錯誤: session '{session_name}' 不存在", err=True)
            sys.exit(1)

    db.add_agent(session_id, "root", "root")

    agent = Code5Agent(
        client=client,
        config=config,
        reviewer=reviewer,
        session_id=session_id,
        agent_id="root",
    )

    if verbose:
        agent.verbose = True

    current_session_id = [session_name]
    current_agent_id = ["root"]
    current_agent = [agent]
    pending_tasks: dict[str, asyncio.Task] = {}
    task_counter = [0]
    user_input_lines: list[str] = []
    input_lock = threading.Lock()
    input_thread_running = [True]
    is_interactive = sys.stdin.isatty()

    def read_input_thread():
        while input_thread_running[0]:
            try:
                line = input()
                with input_lock:
                    user_input_lines.append(line)
            except (EOFError, KeyboardInterrupt):
                with input_lock:
                    user_input_lines.append("/exit")
                break

    async def check_pending_tasks() -> None:
        done_ids = []
        for task_id, task in list(pending_tasks.items()):
            if task.done():
                done_ids.append(task_id)
                try:
                    task.result()
                except Exception:
                    pass
        for tid in done_ids:
            del pending_tasks[tid]

    async def run_once():
        if not sys.stdin.isatty():
            stdin_text = sys.stdin.read()
            if stdin_text:
                stdin_lines = [line.rstrip() for line in stdin_text.strip().split("\n") if line.strip()]
            else:
                stdin_lines = []
        else:
            stdin_lines = []

        db = Database.get_instance()
        if stdin_lines:
            for user_input in stdin_lines:
                if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                    break

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    result = handle_command(user_input, current_session_id, current_agent_id, current_agent, client, config, reviewer, db, pending_tasks, task_counter)
                    if result is not None:
                        print(result)
                else:
                    print(f"[你] {user_input}")
                    await current_agent[0].run(user_input)
                    print(result)
                    print("-" * 50)

            while pending_tasks:
                await check_pending_tasks()
                await asyncio.sleep(0.2)
        else:
            print(f"Code5 - 對話區塊: {current_session_id[0]} | agent: {current_agent_id[0]}")
            print("指令: /help, /bg 背景執行, /jobs 查看任務")
            print("=" * 50)

            input_thread = threading.Thread(target=read_input_thread, daemon=True)
            input_thread.start()

            if is_interactive:
                sys.stderr.write(">>> ")
                sys.stderr.flush()

            while True:
                await check_pending_tasks()

                with input_lock:
                    if user_input_lines:
                        user_input = user_input_lines.pop(0)
                    else:
                        user_input = None
                        await asyncio.sleep(0.3)
                        continue

                user_input = user_input.strip() if user_input else ""

                if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                    print("再見！")
                    input_thread_running[0] = False
                    break

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    is_bg = user_input.startswith("/bg ")
                    result = handle_command(user_input, current_session_id, current_agent_id, current_agent, client, config, reviewer, db, pending_tasks, task_counter)
                    if result is not None:
                        print(result)
                    if is_interactive:
                        sys.stderr.write(">>> ")
                        sys.stderr.flush()
                else:
                    print(f"[你] {user_input}")
                    await check_pending_tasks()
                    try:
                        await current_agent[0].run(user_input)
                        print(result)
                    except Exception as e:
                        print(f"錯誤: {e}")
                    if is_interactive:
                        sys.stderr.write(">>> ")
                        sys.stderr.flush()

        input_thread_running[0] = False
        if hasattr(client, "close"):
            await client.close()

    asyncio.run(run_once())


def handle_command(user_input: str, current_session_id: list, current_agent_id: list, current_agent: list, client, config, reviewer, db, pending_tasks: dict | None = None, task_counter: list | None = None) -> str | None:
    """Handle / commands."""
    current_agent[0].memory.update(user_input, "", None)
    cmd = user_input.lower()

    # /help
    if cmd == "/help":
        return """
=== 可用指令 ===
/help              - 顯示這說明
/history           - 顯示目前 agent 提問
/log               - 顯示目前 agent 完整記錄
/shell <cmd>      - 執行 shell 命令
/list              - 列出所有 session
/now              - 顯示目前 session
/new <name>       - 切換到新 session
/attach <name>    - 切換到其他 session
/agent list        - 列出目前 session 的所有 agent
/agent new <name>  - 建立新 agent
/agent attach <name> - 切換到其他 agent
/agent history    - 顯示該 agent 提問
/agent log         - 顯示該 agent 完整記錄
/bg <prompt>       - 背景執行，不等待結果
/jobs              - 查看背景任務狀態
/exit              - 結束對話
"""

    # /bg - 背景執行
    if cmd.startswith("/bg "):
        if pending_tasks is None or task_counter is None:
            return "錯誤: 背景模式不可用"
        prompt = user_input.split("/bg ", 1)[1].strip()
        if not prompt:
            return "用法: /bg <prompt>"
        task_counter[0] += 1
        task_id = str(task_counter[0])

        from io import StringIO
        output_buffer = StringIO()

        async def run_bg():
            import sys
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            try:
                sys.stdout = output_buffer
                sys.stderr = output_buffer
                await current_agent[0].run(prompt)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                output = output_buffer.getvalue()
                if output:
                    print(f"[背景任務 #{task_id} 輸出]\n{output}")

        task = asyncio.create_task(run_bg())
        pending_tasks[task_id] = task
        return "任務已在背景執行 ..."

    # /jobs - 查看背景任務
    if cmd in ("/jobs", "jobs"):
        if not pending_tasks:
            return "\n沒有進行中的任務"
        output = "\n=== 背景任務 ==="
        for tid, task in pending_tasks.items():
            status = "完成" if task.done() else "進行中"
            output += f"\n  #{tid}: {status}"
        output += "\n" + "=" * 50
        return output

    # /shell <command>
    if cmd.startswith("/shell ") or cmd.startswith("shell "):
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
        return "=" * 50

    # /list
    if cmd.startswith("/list") or cmd.startswith("list"):
        sessions = db.get_all_sessions()
        output = "\n=== 所有 Sessions ==="
        for s in sessions:
            marker = " <-" if s["session_id"] == current_session_id[0] else ""
            output += f"\n  {s['session_id']} ({s['count']} messages){marker}"
        output += "\n" + "=" * 50
        return output

    # /now
    if cmd == "/now":
        return f"\n目前 session: {current_session_id[0]} | agent: {current_agent_id[0]}\n" + "=" * 50

    # /new <name>
    if cmd.startswith("/new ") or cmd.startswith("new "):
        new_name = user_input.split("new ", 1)[1].strip()
        current_session_id[0] = new_name
        current_agent_id[0] = "root"
        current_agent[0] = Code5Agent(
            client=client,
            config=config,
            reviewer=reviewer,
            session_id=new_name,
            agent_id="root",
        )
        db.add_agent(new_name, "root", "root")
        return f"\n已切換到 session: {new_name}, agent: root\n" + "=" * 50

    # /attach <name>
    if cmd.startswith("/attach ") or cmd.startswith("attach "):
        attach_name = user_input.split("attach ", 1)[1].strip()
        convs = db.get_conversations(attach_name)
        if not convs:
            return f"錯誤: session '{attach_name}' 不存在\n" + "=" * 50
        current_session_id[0] = attach_name
        current_agent_id[0] = "root"
        current_agent[0] = Code5Agent(
            client=client,
            config=config,
            reviewer=reviewer,
            session_id=attach_name,
            agent_id="root",
        )
        return f"\n已切換到 session: {attach_name}, agent: root\n" + "=" * 50

    # /agent list
    if cmd.startswith("/agent list") or cmd.startswith("agent list"):
        agents = db.get_agents(current_session_id[0])
        output = "\n=== Agents ==="
        all_agents = [{"agent_id": "root", "name": "root", "created_at": ""}]
        for a in agents:
            if a["agent_id"] != "root":
                all_agents.append(a)
        for a in all_agents:
            marker = " <-" if a["agent_id"] == current_agent_id[0] else ""
            output += f"\n  {a['agent_id']}{marker}"
        output += "\n" + "=" * 50
        return output

    # /agent new <name>
    if cmd.startswith("/agent new ") or cmd.startswith("agent new "):
        new_agent_name = user_input.split("agent new ", 1)[1].strip()
        current_agent_id[0] = new_agent_name
        db.add_agent(current_session_id[0], new_agent_name, new_agent_name)
        current_agent[0] = Code5Agent(
            client=client,
            config=config,
            reviewer=reviewer,
            session_id=current_session_id[0],
            agent_id=new_agent_name,
        )
        return f"\n已建立並切換到 agent: {new_agent_name}\n" + "=" * 50

    # /agent attach <name>
    if cmd.startswith("/agent attach ") or cmd.startswith("agent attach "):
        attach_agent_name = user_input.split("agent attach ", 1)[1].strip()
        if attach_agent_name == "root":
            current_agent_id[0] = "root"
            current_agent[0] = Code5Agent(
                client=client,
                config=config,
                reviewer=reviewer,
                session_id=current_session_id[0],
                agent_id="root",
            )
            return "\n已切換到 agent: root\n" + "=" * 50
        agent_info = db.get_agent(current_session_id[0], attach_agent_name)
        if not agent_info:
            return f"錯誤: agent '{attach_agent_name}' 不存在\n" + "=" * 50
        current_agent_id[0] = attach_agent_name
        current_agent[0] = Code5Agent(
            client=client,
            config=config,
            reviewer=reviewer,
            session_id=current_session_id[0],
            agent_id=attach_agent_name,
        )
        return f"\n已切換到 agent: {attach_agent_name}\n" + "=" * 50

    # /agent history
    if cmd == "/agent history":
        questions = db.get_user_conversations(current_session_id[0], current_agent_id[0])
        actual_questions = [q for q in questions if not q.startswith("/")]
        output = f"\n=== {current_agent_id[0]} 提問歷史 ==="
        for i, q in enumerate(actual_questions):
            output += f"\n{i+1}. {q}"
        output += "\n" + "=" * 50
        return output

    # /agent log
    if cmd == "/agent log":
        convs = [c for c in db.get_conversations(current_session_id[0], current_agent_id[0]) if not c["content"].startswith("/")]
        key_info = db.get_key_info(current_session_id[0], current_agent_id[0])
        output = f"\n=== {current_agent_id[0]} 完整記錄 ==="
        if key_info:
            output += f"\n--- 關鍵資訊 ({len(key_info)} 項) ---"
            for item in key_info:
                output += f"\n  * {item}"
        output += f"\n--- 對話記錄 ({len(convs)} 項) ---"
        for c in convs:
            marker = "你" if c["role"] == "user" else "AI"
            output += f"\n[{marker}] {c['content']}"
        output += "\n" + "=" * 50
        return output

    # /history
    if cmd.startswith("/history") or cmd.startswith("history"):
        parts = user_input.split()
        n = None
        if len(parts) > 1:
            try:
                n = int(parts[1])
            except ValueError:
                pass
        all_questions = db.get_user_conversations(current_session_id[0], current_agent_id[0])
        questions = all_questions[-n:] if n else all_questions
        start_idx = len(all_questions) - len(questions) + 1
        output = f"\n=== {current_agent_id[0]} 提問 ==="
        for i, q in enumerate(questions):
            output += f"\n{start_idx + i}. {q}"
        output += "\n" + "=" * 50
        return output

    # /log
    if cmd.startswith("/log") or cmd.startswith("log"):
        parts = user_input.split()
        n = None
        if len(parts) > 1:
            try:
                n = int(parts[1])
            except ValueError:
                pass
        all_convs = db.get_conversations(current_session_id[0], current_agent_id[0])
        convs = all_convs[-n:] if n else all_convs
        start_idx = len(all_convs) - len(convs) + 1
        key_info = db.get_key_info(current_session_id[0], current_agent_id[0])
        output = f"\n=== {current_agent_id[0]} 完整記錄 ==="
        if key_info:
            output += f"\n--- 關鍵資訊 ({len(key_info)} 項) ---"
            for item in key_info:
                output += f"\n  * {item}"
        output += f"\n--- 對話記錄 ({len(convs)} 項) ---"
        for c in convs:
            marker = "你" if c["role"] == "user" else "AI"
            output += f"\n[{marker}] {c['content']}"
        output += "\n" + "=" * 50
        return output

    # /exit
    if cmd in ("/exit", "/quit", "exit", "quit"):
        print("再見！")
        sys.exit(0)

    return None


if __name__ == "__main__":
    main()
