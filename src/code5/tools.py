"""Tool execution for code5 - shell commands and file operations."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def output(self) -> str:
        if self.timed_out:
            return f"Command timed out\n{self.stdout}"
        return self.stdout + (f"\n{self.stderr}" if self.stderr else "")


class ShellTool:
    """Execute shell commands safely with timeout and output capture."""

    def __init__(self, timeout: int = 30, cwd: Path | None = None) -> None:
        self.timeout = timeout
        self.cwd = cwd or Path.cwd()

    def execute(self, command: str) -> CommandResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.cwd),
            )
            return CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired as e:
            return CommandResult(
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=f"Command timed out after {self.timeout} seconds",
                returncode=-1,
                timed_out=True,
            )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
            )

    async def execute_async(self, command: str) -> CommandResult:
        import asyncio

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.cwd),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            return CommandResult(
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
                returncode=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {self.timeout} seconds",
                returncode=-1,
                timed_out=True,
            )


class FileTool:
    """File reading and writing operations."""

    @staticmethod
    def read(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    @staticmethod
    def write(path: Path, content: str) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    @staticmethod
    def exists(path: Path) -> bool:
        return path.exists()

    @staticmethod
    def list_dir(path: Path) -> list[str]:
        if not path.is_dir():
            return []
        return sorted([p.name for p in path.iterdir()])


def check_outside_access(command: str, cwd: Path) -> tuple[bool, str]:
    """Check if a command attempts to access paths outside the current directory.

    Args:
        command: The shell command to check
        cwd: Current working directory

    Returns:
        Tuple of (is_outside, path) where is_outside is True if access is outside
    """
    paths = extract_paths_from_command(command)
    cwd_abs = cwd.resolve()

    for path in paths:
        if path == ".." or path.startswith("../"):
            return True, str(cwd.parent.resolve())

        if path.startswith("/"):
            abs_path = Path(path)
        else:
            abs_path = (cwd / path).resolve()

        if not str(abs_path).startswith(str(cwd_abs)):
            return True, str(abs_path)

    return False, ""


def extract_paths_from_command(command: str) -> list[str]:
    """Extract file paths from a shell command.

    Args:
        command: The shell command to parse

    Returns:
        List of extracted paths
    """
    paths: list[str] = []
    patterns = [
        r"(?:^|\s)(?:cat|ls|cd|rm|cp|mv|chmod|chown|find|grep|open|code|vim|vi|nano)\s+([^\s]+)",
        r"(?:^|\s)\.\./[^\s]*",
        r"(?:^|\s)\.\.(?:\s|$)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, command, re.MULTILINE):
            path = match.group(1).strip() if match.lastindex and match.lastindex > 0 else ".."
            if path and path not in paths:
                paths.append(path)

    return paths


def ask_outside_access(path: str) -> bool:
    """Ask user for permission to access outside directory.

    Args:
        path: The path being accessed

    Returns:
        True if user granted permission
    """
    print(f"\nWARNING: Command attempts to access outside directory: {path}")
    print("Allow access? (y/N): ", end="")
    try:
        response = input().strip().lower()
        return response in ["y", "yes"]
    except (EOFError, KeyboardInterrupt):
        return False


class ToolExecutor:
    """Combined executor for shell and file tools with safety checks."""

    def __init__(
        self,
        shell_tool: ShellTool | None = None,
        file_tool: FileTool | None = None,
        timeout: int = 30,
    ) -> None:
        self.shell = shell_tool or ShellTool(timeout=timeout)
        self.file = file_tool or FileTool()
        self.timeout = timeout

    def execute_shell(
        self,
        command: str,
        cwd: Path | None = None,
        check_access: bool = True,
        ask_for_access: bool = False,
        granted_paths: set[str] | None = None,
    ) -> tuple[CommandResult, bool, str]:
        """Execute shell command with safety checks.

        Returns:
            Tuple of (result, allowed, message)
        """
        if check_access:
            is_outside, outside_path = check_outside_access(command, cwd or Path.cwd())
            if is_outside:
                if ask_for_access:
                    if not ask_outside_access(outside_path):
                        result = CommandResult("", "Access denied by user", -1)
                        return result, False, outside_path
                    if granted_paths is not None:
                        granted_paths.add(outside_path)
                else:
                    result = CommandResult("", f"Access to {outside_path} denied", -1)
                    return result, False, outside_path

        result = self.shell.execute(command)
        return result, True, ""

    def read_file(self, path: Path) -> tuple[bool, str]:
        try:
            content = self.file.read(path)
            return True, content
        except Exception as e:
            return False, str(e)

    def write_file(self, path: Path, content: str) -> tuple[bool, str]:
        success = self.file.write(path, content)
        if success:
            return True, ""
        return False, "Failed to write file"
