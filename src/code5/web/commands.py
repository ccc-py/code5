"""Web commands module - CLI-like commands for web interface."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field


@dataclass
class WebAgent:
    """Web agent for tracking conversations."""

    name: str
    history: list[dict[str, str]] = field(default_factory=list)


class WebAgentStore:
    """In-memory store for web agents."""

    def __init__(self) -> None:
        self.agents: dict[str, WebAgent] = {}
        self.current_agent: str = "root"

    def create_agent(self, name: str) -> WebAgent:
        """Create a new agent."""
        agent = WebAgent(name=name)
        self.agents[name] = agent
        return agent

    def get_agent(self, name: str) -> WebAgent | None:
        """Get agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> list[str]:
        """List all agent names."""
        return list(self.agents.keys())

    def add_conversation(self, agent_name: str, role: str, content: str) -> None:
        """Add conversation to agent history."""
        agent = self.agents.get(agent_name)
        if agent:
            agent.history.append({"role": role, "content": content})

    def get_user_messages(self, agent_name: str, n: int | None = None) -> list[str]:
        """Get user messages from agent history."""
        agent = self.agents.get(agent_name)
        if not agent:
            return []
        user_msgs = [h["content"] for h in agent.history if h["role"] == "user"]
        if n:
            return user_msgs[-n:]
        return user_msgs

    def get_full_history(self, agent_name: str, n: int | None = None) -> list[dict[str, str]]:
        """Get full conversation history."""
        agent = self.agents.get(agent_name)
        if not agent:
            return []
        if n:
            return agent.history[-n:]
        return agent.history


agent_store = WebAgentStore()


def is_command(message: str) -> bool:
    """Check if message is a command (starts with /)."""
    return message.strip().startswith("/")


def parse_command(message: str) -> tuple[str, list[str]]:
    """Parse command into name and args."""
    parts = message.strip().split()
    cmd = parts[0] if parts else ""
    args = parts[1:] if len(parts) > 1 else []
    return cmd, args


def execute_shell(command: str) -> str:
    """Execute shell command and return result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"[stderr] {result.stderr}\n"
        if result.returncode != 0 and not result.stdout:
            output += f"returncode: {result.returncode}\n"
        return f"```\n{output or '命令執行完成'}\n```"
    except subprocess.TimeoutExpired:
        return "命令執行逾時"
    except Exception as e:
        return f"執行錯誤: {e}"


def execute_history(n: int, session_history: list[dict[str, str]]) -> str:
    """Execute /history command."""
    user_messages = [h["content"] for h in session_history if h["role"] == "user"]
    if not user_messages:
        return "目前沒有提問記錄"
    messages = user_messages[-n:]
    output = f"【提問記錄】(最近 {len(messages)} 筆)\n"
    for i, m in enumerate(messages, 1):
        content = m[:100] + "..." if len(m) > 100 else m
        output += f"{i}. {content}\n"
    output += "=" * 40
    return output


def execute_log(n: int, session_history: list[dict[str, str]]) -> str:
    """Execute /log command."""
    if not session_history:
        return "目前沒有記錄"
    history = session_history[-n:]
    output = f"【完整記錄】(最近 {len(history)} 筆)\n"
    for h in history:
        marker = "你" if h["role"] == "user" else "AI"
        content = h["content"][:100] + "..." if len(h["content"]) > 100 else h["content"]
        output += f"[{marker}] {content}\n"
    output += "=" * 40
    return output


def execute_agent_list() -> str:
    """Execute /agent list command."""
    agents = agent_store.list_agents()
    current = agent_store.current_agent
    if not agents:
        agents = ["root"]
        agent_store.create_agent("root")
    output = "【Agents】\n"
    for a in agents:
        marker = " <-" if a == current else ""
        output += f"  {a}{marker}\n"
    output += "-" * 40
    return output


def execute_agent_new(name: str) -> str:
    """Execute /agent new <name> command."""
    if agent_store.get_agent(name):
        return f"Agent '{name}' 已存在"
    agent_store.create_agent(name)
    agent_store.current_agent = name
    return f"已建立並切換到 agent: {name}"


def execute_agent_attach(name: str) -> str:
    """Execute /agent attach <name> command."""
    agent = agent_store.get_agent(name)
    if not agent:
        return f"Agent '{name}' 不存在"
    agent_store.current_agent = name
    return f"已切換到 agent: {name}"


def execute_agent_history(n: int | None = None) -> str:
    """Execute /agent history command."""
    agent = agent_store.get_agent(agent_store.current_agent)
    if not agent:
        return "目前沒有 agent"
    history = agent_store.get_user_messages(agent_store.current_agent, n)
    if not history:
        return f"Agent '{agent_store.current_agent}' 沒有提問記錄"
    output = f"【{agent_store.current_agent} 提問】\n"
    for i, h in enumerate(history, 1):
        output += f"{i}. {h}\n"
    output += "-" * 40
    return output


def execute_agent_log(n: int | None = None) -> str:
    """Execute /agent log command."""
    history = agent_store.get_full_history(agent_store.current_agent, n)
    if not history:
        return f"Agent '{agent_store.current_agent}' 沒有記錄"
    output = f"【{agent_store.current_agent} 記錄】\n"
    for h in history:
        marker = "你" if h["role"] == "user" else "AI"
        output += f"[{marker}] {h['content'][:80]}...\n"
    output += "-" * 40
    return output


def execute_command(message: str, session_history: list[dict[str, str]]) -> str:
    """Execute web command and return result."""
    cmd, args = parse_command(message)
    result = ""

    if cmd in ("/shell", "shell"):
        if not args:
            return "用法: /shell <command>"
        result = execute_shell(" ".join(args))

    elif cmd in ("/history", "history"):
        try:
            n = int(args[0]) if args else 10
        except ValueError:
            return "用法: /history <n> - n 必須是數字"
        result = execute_history(n, session_history)

    elif cmd in ("/log", "log"):
        try:
            n = int(args[0]) if args else 10
        except ValueError:
            return "用法: /log <n> - n 必須是數字"
        result = execute_log(n, session_history)

    elif cmd in ("/agent", "agent"):
        if not args:
            return "用法: /agent <list|new|attach|history|log> [args]"
        subcmd = args[0]
        if subcmd == "list":
            result = execute_agent_list()
        elif subcmd == "new":
            if len(args) < 2:
                return "用法: /agent new <name>"
            result = execute_agent_new(args[1])
        elif subcmd == "attach":
            if len(args) < 2:
                return "用法: /agent attach <name>"
            result = execute_agent_attach(args[1])
        elif subcmd == "history":
            n = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
            result = execute_agent_history(n)
        elif subcmd == "log":
            n = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
            result = execute_agent_log(n)
        else:
            result = f"未知 agent 指令: {subcmd}"

    elif cmd in ("/help", "help"):
        result = """【Code5 指令說明】

/shell <cmd>   - 執行 shell 命令
/history <n>   - 查看前 n 筆提問
/log <n>      - 查看前 n 筆記錄
/agent list    - 列出所有 agent
/agent new <name> - 建立新 agent
/agent attach <name> - 切換 agent
/agent history - 顯示 agent 提問
/agent log     - 顯示 agent 記錄
/list          - 列出所有 sessions
/new <name>   - 建立新 session
/attach <name> - 切換到其他 session
/now           - 顯示目前 session 和 agent
/exit          - 結束對話
/help          - 顯示說明

"""

    elif cmd in ("/list", "list"):
        from .app import session_store
        sessions = session_store.list()
        if not sessions:
            result = "目前沒有 sessions"
        else:
            result = "【Sessions】\n"
            for s in sessions:
                result += f"  {s['session_id']} ({s['message_count']} messages)\n"
            result += "-" * 40

    elif cmd in ("/new", "new"):
        if not args:
            return "用法: /new <name>"
        from .app import session_store
        session = session_store.create(args[0])
        result = f"已建立並切換到 session: {session.session_id}"

    elif cmd in ("/attach", "attach"):
        if not args:
            return "用法: /attach <name>"
        from .app import session_store
        session = session_store.get(args[0])
        if not session:
            result = f"Session '{args[0]}' 不存在"
        else:
            session_store.set_current(args[0])
            result = f"已切換到 session: {args[0]}"

    elif cmd in ("/now", "now"):
        from .app import session_store
        result = f"目前 session: {session_store.current_session_id or '無'}\\n"
        result += f"目前 agent: {agent_store.current_agent}"

    elif cmd in ("/exit", "/quit", "exit", "quit"):
        result = "再見！如要重新開始，請刷新頁面。"

    else:
        result = f"未知指令: {cmd}"

    agent_store.add_conversation(
        agent_store.current_agent,
        "user",
        message,
    )
    agent_store.add_conversation(
        agent_store.current_agent,
        "assistant",
        result,
    )

    return result
