"""主要代理實現 - Code5 核心類別

此模組包含 Code5Agent 類別，負責協調：
- LLM 互動（NVIDIA 或 Mock 客戶端）
- 工具執行（Shell 命令）
- 記憶體管理
- 安全審查
- Session 管理
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .client import LLMClient, MockClient, create_client
from .config import DEFAULT_CONFIG, Config
from .memory import MemoryManager, extract_key_info_from_text
from .prompts import SYSTEM_PROMPT
from .reviewer import CommandReviewer
from .session import SessionManager
from .tools import ShellTool, ToolExecutor, check_outside_access

if TYPE_CHECKING:
    from .client import LLMClient

# 正則表達式：用於解析代理回應中的 shell 標籤和結束標記
ShellPattern = re.compile(r"<shell>(.+?)</shell>", re.DOTALL)
EndPattern = re.compile(r"<end/>")


class Code5Agent:
    """具有工具執行能力的 AI 編碼代理"""

    def __init__(
        self,
        client: LLMClient | None = None,
        config: Config | None = None,
        reviewer: CommandReviewer | None = None,
        session_manager: SessionManager | None = None,
        session_id: str | None = None,
    ) -> None:
        self.config = config or DEFAULT_CONFIG
        # 如果沒有提供客戶端，則根據配置創建
        self.client = client or create_client(self.config)
        self.reviewer = reviewer or CommandReviewer()
        # Shell 工具和執行器
        self.shell_tool = ShellTool(timeout=self.config.shell_timeout)
        self.tool_executor = ToolExecutor(shell_tool=self.shell_tool, timeout=self.config.shell_timeout)
        # 記憶體管理器 - 傳入 session_id 以使用 SQLite
        self.memory = MemoryManager(
            max_turns=self.config.max_turns,
            max_key_info=20,
            session_id=session_id,
            use_db=True if session_id else False,
        )
        # Session 管理器
        self.session_manager = session_manager or SessionManager()
        # 已授權的目錄外訪問路徑
        self.outside_access_granted: set[str] = set()
        self._verbose = False

    @property
    def verbose(self) -> bool:
        """是否為詳細輸出模式"""
        return self._verbose

    @verbose.setter
    def verbose(self, value: bool) -> None:
        """設定詳細輸出模式"""
        self._verbose = value

    async def run(
        self,
        user_input: str,
        on_chunk: callable[[str], None] | None = None,
        keep_tags: bool = False,
    ) -> str:
        """執行單次對話

        Args:
            user_input: 使用者輸入
            on_chunk: 回呼函數，每個區塊回應時調用

        Returns:
            代理的回應文字
        """
        # 建立上下文（包含記憶體和歷史）
        context = self.memory.build_context()
        full_prompt = f"{context}\n\n<user>{user_input}</user>" if context else f"<user>{user_input}</user>"

        # 呼叫 LLM 獲取回應
        print(f"\n[LLM] 請求: {full_prompt}", file=sys.stderr)
        response = await self.client.generate(full_prompt, SYSTEM_PROMPT)
        print(f"[LLM] 回應: {response}", file=sys.stderr)

        # 回調每個區塊
        if on_chunk:
            on_chunk(response)

        tool_result: str | None = None
        current_response = response

# 處理回應中的工具調用
        while True:
            # 先解析 shell 命令
            shell_matches = ShellPattern.findall(current_response)

            if shell_matches:
                # 執行 shell 命令
                print("\n" + "=" * 60, file=sys.stderr)
                print("[Shell] 執行命令:", file=sys.stderr)

                all_outputs: list[str] = []
                for cmd in shell_matches:
                    cmd = cmd.strip()
                    print(f"  $ {cmd}", file=sys.stderr)

                    # 安全審查
                    print("[Shell] 安全審查中...", file=sys.stderr)
                    review_result = await self.reviewer.review_async(cmd)
                    if not review_result.is_safe:
                        output = f"命令被安全審查阻止：{review_result.reason}"
                        print(f"  [已阻止] {review_result.reason}", file=sys.stderr)
                        all_outputs.append(output)
                        continue

                    # 檢查是否需要目錄外訪問
                    needs_access, outside_path = check_outside_access(cmd, Path.cwd())
                    if needs_access:
                        if outside_path not in self.outside_access_granted:
                            if not self.config.allow_outside_access:
                                output = f"需要用戶明確授權才能訪問：{outside_path}"
                                print(f"  [需要授權] {outside_path}", file=sys.stderr)
                                all_outputs.append(output)
                                continue
                            self.outside_access_granted.add(outside_path)

                    # 執行 shell 命令
                    print("[Shell] 執行中...", file=sys.stderr)
                    result, allowed, msg = self.tool_executor.execute_shell(
                        cmd,
                        check_access=True,
                        ask_for_access=False,
                        granted_paths=self.outside_access_granted,
                    )

                    if not allowed:
                        all_outputs.append(f"拒絕訪問：{msg}")
                        continue

                    output = result.output if result.output.strip() else "(無輸出)"
                    all_outputs.append(f"$ {cmd}\n{output}")
                    print(f"[Shell] 完成: returncode={result.returncode}", file=sys.stderr)
                    if result.output:
                        print(f"[Shell] 輸出:\n{result.output}", file=sys.stderr)

                # 組合工具輸出
                tool_result = "\n".join(all_outputs)
                print("[Shell] 所有命令執行完成", file=sys.stderr)
                print("=" * 60 + "\n", file=sys.stderr)

                # 執行完 shell 後，檢查是否有 <end/> 標記
                if EndPattern.search(current_response):
                    if keep_tags:
                        response = current_response
                    else:
                        response = EndPattern.split(current_response)[0].strip()
                    break

                # 繼續對話，獲取下一步指示
                print("[LLM] 請求下一步指示...", file=sys.stderr)
                follow_up_prompt = f"""<context>{context}</context>

<user>{user_input}</user>
<assistant>{current_response}</assistant>
<output>
{chr(10).join(all_outputs)}
</output>

如果需要更多命令，輸出 <shell>。否則，輸出 <end/> 結束："""

                current_response = await self.client.generate(follow_up_prompt, SYSTEM_PROMPT)
                print(f"[LLM] 下一步: {current_response}", file=sys.stderr)

                # 回調每個區塊
                if on_chunk:
                    on_chunk(current_response)
            else:
                # 沒有 shell 命令，檢查是否有 <end/> 標記
                if EndPattern.search(current_response):
                    if keep_tags:
                        response = current_response
                    else:
                        response = EndPattern.split(current_response)[0].strip()
                else:
                    response = current_response
                break

                # 執行 shell 命令
                result, allowed, msg = self.tool_executor.execute_shell(
                    cmd,
                    check_access=True,
                    ask_for_access=False,
                    granted_paths=self.outside_access_granted,
                )

                if not allowed:
                    all_outputs.append(f"拒絕訪問：{msg}")
                    continue

                output = result.output if result.output.strip() else "(無輸出)"
                all_outputs.append(f"$ {cmd}\n{output}")

                if self._verbose:
                    print(f"  結果：{result.returncode}", file=sys.stderr)

            # 組合工具輸出
            tool_result = "\n".join(all_outputs)

            # 執行完 shell 後，檢查是否有 <end/> 標記
            if EndPattern.search(current_response):
                response = EndPattern.split(current_response)[0].strip()
                break

            # 繼續對話，獲取下一步指示
            follow_up_prompt = f"""<context>{context}</context>

<user>{user_input}</user>
<assistant>{current_response}</assistant>
<output>
{chr(10).join(all_outputs)}
</output>

如果需要更多命令，輸出 <shell>。否則，輸出 <end/> 結束："""

            current_response = await self.client.generate(follow_up_prompt, SYSTEM_PROMPT)

        else:
            # 沒有 shell 命令，檢查是否有 <end/> 標記
            if EndPattern.search(current_response):
                response = EndPattern.split(current_response)[0].strip()
            else:
                response = current_response

        # 更新記憶體
        self.memory.update(user_input, response, tool_result)

        # 如果有工具輸出且使用真實 LLM，提取關鍵資訊
        if tool_result and self.client and not isinstance(self.client, MockClient):
            await self._extract_key_info(user_input, response)

        return response

    async def run_interactive(self) -> None:
        """互動式對話模式"""
        session = self.session_manager.current_session() or self.session_manager.create_session()

        print(f"Code5 代理 (session: {session.session_id[:8]})")
        print("指令：/quit、/memory、/session [id]")
        print()

        while True:
            try:
                user_input = input("你：").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再見！")
                self.session_manager.save_current_session()
                break

            if not user_input:
                continue

            # 處理特殊指令
            if user_input.lower() in ["/quit", "/exit", "/q"]:
                print("再見！")
                self.session_manager.save_current_session()
                break

            if user_input.lower() == "/memory":
                print(f"關鍵資訊：{self.memory.key_info.to_list()}")
                continue

            if user_input.lower().startswith("/session"):
                parts = user_input.split()
                if len(parts) > 1:
                    target_id = parts[1]
                    if self.session_manager.set_current_session(target_id):
                        print(f"已切換到 session：{target_id}")
                    else:
                        print(f"找不到 session：{target_id}")
                else:
                    sessions = self.session_manager.list_sessions()
                    print("Sessions：")
                    for s in sessions[:10]:
                        print(f"  {s.session_id[:8]} - {s.updated_at.strftime('%Y-%m-%d %H:%M')}")
                continue

            # 執行一般對話
            response = await self.run(user_input)
            print(f"\n代理：{response}\n")

    async def _extract_key_info(self, user_input: str, assistant_response: str) -> None:
        """從對話中提取需要長期記憶的關鍵資訊"""
        extract_prompt = f"""根據這段對話，提取需要長期記憶的關鍵資訊。
如果有，輸出以下格式（最多 2 項）。如果沒有，輸出 <memory></memory>。

<memory>
  <item>關鍵資訊 1</item>
  <item>關鍵資訊 2</item>
</memory>

對話：
<user>{user_input}</user>
<assistant>{assistant_response}</assistant>"""

        try:
            result = await self.client.generate(extract_prompt, "")
            items = extract_key_info_from_text(result)
            for item in items:
                self.memory.key_info.add(item)
        except Exception:
            pass

    def reset(self) -> None:
        """重置代理狀態（清除記憶和授權）"""
        self.memory.clear_all()
        self.outside_access_granted.clear()

    def load_session(self, session_id: str) -> bool:
        """載入指定 session"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return False
        self.memory = session.memory
        self.session_manager.set_current_session(session_id)
        return True

    def save_session(self) -> None:
        """保存當前 session"""
        session = self.session_manager.current_session()
        if session:
            session.memory = self.memory
            self.session_manager.save_current_session()
