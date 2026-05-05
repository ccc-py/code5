"""Tests for tools module."""

from pathlib import Path

import pytest

from code5.tools import (
    CommandResult,
    FileTool,
    ShellTool,
    ToolExecutor,
    check_outside_access,
    extract_paths_from_command,
)


class TestCommandResult:
    def test_success_result(self) -> None:
        result = CommandResult(stdout="output", stderr="", returncode=0)
        assert result.success is True
        assert result.output == "output"

    def test_failure_result(self) -> None:
        result = CommandResult(stdout="", stderr="error", returncode=1)
        assert result.success is False

    def test_timed_out_result(self) -> None:
        result = CommandResult(stdout="", stderr="timeout", returncode=-1, timed_out=True)
        assert result.timed_out is True
        assert "timed out" in result.output

    def test_output_with_stderr(self) -> None:
        result = CommandResult(stdout="stdout", stderr="stderr", returncode=0)
        assert "stderr" in result.output


class TestShellTool:
    def test_execute_ls(self, tmp_path: Path) -> None:
        tool = ShellTool(timeout=30, cwd=tmp_path)
        result = tool.execute("ls")
        assert result.success is True
        assert result.returncode == 0

    def test_execute_invalid_command(self, tmp_path: Path) -> None:
        tool = ShellTool(timeout=30, cwd=tmp_path)
        result = tool.execute("invalid_command_xyz")
        assert result.success is False

    def test_execute_with_cwd(self, tmp_path: Path) -> None:
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        tool = ShellTool(timeout=30, cwd=tmp_path)
        result = tool.execute("ls subdir")
        assert result.success is True

    def test_execute_timeout(self, tmp_path: Path) -> None:
        tool = ShellTool(timeout=1, cwd=tmp_path)
        result = tool.execute("sleep 10")
        assert result.timed_out is True

    @pytest.mark.asyncio
    async def test_execute_async(self, tmp_path: Path) -> None:
        tool = ShellTool(timeout=30, cwd=tmp_path)
        result = await tool.execute_async("echo hello")
        assert result.success is True
        assert "hello" in result.stdout


class TestFileTool:
    def test_write_and_read(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"

        success = FileTool.write(file_path, content)
        assert success is True

        read_content = FileTool.read(file_path)
        assert read_content == content

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        file_path = tmp_path / "nested" / "dir" / "test.txt"
        success = FileTool.write(file_path, "content")
        assert success is True
        assert file_path.exists()

    def test_read_nonexistent(self, tmp_path: Path) -> None:
        file_path = tmp_path / "nonexistent.txt"
        with pytest.raises(FileNotFoundError):
            FileTool.read(file_path)

    def test_exists(self, tmp_path: Path) -> None:
        file_path = tmp_path / "exists.txt"
        assert FileTool.exists(file_path) is False
        file_path.write_text("content")
        assert FileTool.exists(file_path) is True

    def test_list_dir(self, tmp_path: Path) -> None:
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        result = FileTool.list_dir(tmp_path)
        assert "file1.txt" in result
        assert "file2.txt" in result

    def test_list_dir_non_directory(self, tmp_path: Path) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        result = FileTool.list_dir(file_path)
        assert result == []


class TestCheckOutsideAccess:
    def test_no_outside_access(self) -> None:
        cwd = Path("/home/user/project")
        is_outside, path = check_outside_access("ls -la", cwd)
        assert is_outside is False
        assert path == ""

    def test_absolute_path_outside(self) -> None:
        cwd = Path("/home/user/project")
        is_outside, path = check_outside_access("cat /etc/passwd", cwd)
        assert is_outside is True
        assert "/etc" in path

    def test_parent_directory_access(self) -> None:
        cwd = Path("/home/user/project")
        is_outside, path = check_outside_access("ls ..", cwd)
        assert is_outside is True

    def test_relative_path_inside(self) -> None:
        cwd = Path("/home/user/project")
        is_outside, path = check_outside_access("cat file.txt", cwd)
        assert is_outside is False

    def test_mixed_paths(self) -> None:
        cwd = Path("/home/user/project")
        is_outside, path = check_outside_access("cat file.txt && ls /tmp", cwd)
        assert is_outside is True


class TestExtractPathsFromCommand:
    def test_extract_cat_path(self) -> None:
        paths = extract_paths_from_command("cat /etc/passwd")
        assert "/etc/passwd" in paths

    def test_extract_ls_with_absolute_path(self) -> None:
        paths = extract_paths_from_command("ls /home/user")
        assert "/home/user" in paths

    def test_extract_multiple_paths(self) -> None:
        paths = extract_paths_from_command("cat file1.txt && cat file2.txt")
        assert "file1.txt" in paths
        assert "file2.txt" in paths


class TestToolExecutor:
    def test_execute_shell_allowed(self, tmp_path: Path) -> None:
        shell = ShellTool(timeout=30, cwd=tmp_path)
        executor = ToolExecutor(shell_tool=shell)
        result, allowed, msg = executor.execute_shell("echo hello", cwd=tmp_path)
        assert allowed is True
        assert result.success is True

    def test_execute_shell_blocked_by_access(self, tmp_path: Path) -> None:
        shell = ShellTool(timeout=30, cwd=tmp_path)
        executor = ToolExecutor(shell_tool=shell)
        result, allowed, msg = executor.execute_shell(
            "cat /etc/passwd",
            cwd=tmp_path,
            check_access=True,
            ask_for_access=False,
        )
        assert allowed is False
        assert "/etc/passwd" in msg

    def test_read_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        executor = ToolExecutor()
        success, content = executor.read_file(file_path)
        assert success is True
        assert content == "content"

    def test_read_file_not_found(self, tmp_path: Path) -> None:
        file_path = tmp_path / "nonexistent.txt"
        executor = ToolExecutor()
        success, error = executor.read_file(file_path)
        assert success is False

    def test_write_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "new.txt"
        executor = ToolExecutor()
        success, msg = executor.write_file(file_path, "new content")
        assert success is True
        assert file_path.read_text() == "new content"
