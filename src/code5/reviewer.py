"""Security reviewer for shell commands in code5."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import LLMClient


DANGEROUS_PATTERNS = [
    (r"rm\s+-rf\s+/?", "Recursive deletion of root directory"),
    (r"rm\s+-rf\s+/\*", "Recursive deletion of root contents"),
    (r"dd\s+.*of=/dev/", "Direct disk writing with dd"),
    (r"mkfs", "Filesystem formatting"),
    (r":\(\)\{|bash\s+-i", "Bash interactive mode injection"),
    (r"curl.*\|.*sh", "Download and execute script"),
    (r"wget.*\|.*sh", "Download and execute script via wget"),
    (r"sudo\s+.*\s+-i$", "sudo interactive mode"),
    (r"chmod\s+777\s+/\.", "Setting 777 permissions on root"),
    (r">/dev/sd[a-z]", "Direct device writing"),
    (r"shred\s+.*-u", "Secure file deletion"),
    (r"fdisk\s+", "Disk partitioning"),
    (r"parted\s+", "Disk partitioning"),
]

SAFE_COMMANDS = {
    "ls", "cat", "pwd", "cd", "echo", "printf", "grep", "find", "awk",
    "sed", "cut", "sort", "uniq", "wc", "head", "tail", "less", "more",
    "mkdir", "rmdir", "touch", "cp", "mv", "stat", "file", "type",
    "which", "whereis", "whoami", "id", "date", "cal", "du", "df",
    "ps", "top", "kill", "killall", "pgrep", "pkill",
    "git", "hg", "svn",
    "python", "python3", "node", "npm", "pip", "pip3", "nodejs",
    "cargo", "rustc", "go", "java", "javac",
    "vim", "vi", "nano", "emacs", "code", "subl",
    "curl", "wget", "ping", "traceroute", "nslookup",
    "ssh", "scp", "rsync", "tar", "gzip", "gunzip", "zip", "unzip",
    "make", "cmake", "autoconf", "configure",
}


@dataclass
class ReviewResult:
    is_safe: bool
    reason: str
    reviewed_by: str = "rule_based"


class CommandReviewer:
    """Review shell commands for safety before execution."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client
        self.use_llm_review = False

    async def review_async(self, command: str) -> ReviewResult:
        if self.use_llm_review and self.llm_client:
            return await self._review_with_llm(command)
        return self._review_with_rules(command)

    def review(self, command: str) -> ReviewResult:
        if self.use_llm_review and self.llm_client:
            import asyncio
            return asyncio.run(self.review_async(command))
        return self._review_with_rules(command)

    def _review_with_rules(self, command: str) -> ReviewResult:
        for pattern, reason in DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return ReviewResult(False, reason)

        first_word = command.strip().split()[0] if command.strip() else ""
        if first_word in SAFE_COMMANDS:
            return ReviewResult(True, "")

        return ReviewResult(True, "")

    async def _review_with_llm(self, command: str) -> ReviewResult:
        if not self.llm_client:
            return self._review_with_rules(command)

        prompt = f"""You are a security reviewer. Determine if the following shell command is safe to execute.

Safety rules:
1. Allow reading files, browsing directories, searching code
2. Allow harmless development tools (git, ls, cat, grep, find, python, node, etc.)
3. Disallow commands that delete data (rm -rf, dd, mkfs, etc.)
4. Disallow commands that modify system (sudo, chmod 777, system settings, etc.)
5. Disallow dangerous network operations (curl/wget download and execute scripts)
6. Disallow any commands that may cause data leakage or system damage

Command to review:
{command}

Respond exactly in this format:
- If safe: SAFE
- If unsafe: UNSAFE - reason

Do not output anything else."""

        try:
            response = await self.llm_client.generate(prompt, "")
            response = response.strip()

            if response.startswith("SAFE"):
                return ReviewResult(True, "", "llm")
            if response.startswith("UNSAFE"):
                reason = response.replace("UNSAFE", "").strip(" -\n")
                return ReviewResult(False, reason, "llm")

            return ReviewResult(True, "LLM review returned unexpected format", "llm")
        except Exception as e:
            return ReviewResult(False, f"LLM review failed: {e}", "llm")

    def enable_llm_review(self, client: LLMClient) -> None:
        self.llm_client = client
        self.use_llm_review = True

    def disable_llm_review(self) -> None:
        self.use_llm_review = False


class MockReviewer(CommandReviewer):
    """Mock reviewer for testing - always returns safe unless command contains 'dangerous'."""

    def _review_with_rules(self, command: str) -> ReviewResult:
        if "dangerous" in command.lower():
            return ReviewResult(False, "Mock dangerous command detected")
        return ReviewResult(True, "")
