"""Tests for memory module."""

import pytest

from code5.memory import (
    ConversationMemory,
    KeyInfoMemory,
    MemoryManager,
    extract_key_info_from_text,
)


class TestConversationMemory:
    def test_empty_history(self) -> None:
        memory = ConversationMemory()
        assert memory.build_context() == ""
        assert len(memory) == 0

    def test_add_user(self) -> None:
        memory = ConversationMemory()
        memory.add_user("Hello")
        assert len(memory) == 1
        assert "<user>Hello</user>" in memory.history

    def test_add_assistant(self) -> None:
        memory = ConversationMemory()
        memory.add_assistant("Hi there!")
        assert len(memory) == 1
        assert "<assistant>Hi there!</assistant>" in memory.history

    def test_add_tool(self) -> None:
        memory = ConversationMemory()
        memory.add_tool("Command output")
        assert len(memory) == 1
        assert "<tool>Command output</tool>" in memory.history

    def test_add_tool_truncation(self) -> None:
        memory = ConversationMemory()
        long_content = "x" * 1000
        memory.add_tool(long_content)
        assert len(memory.history[0]) < 600

    def test_build_context(self) -> None:
        memory = ConversationMemory()
        memory.add_user("Hello")
        memory.add_assistant("Hi!")
        context = memory.build_context()
        assert "<history>" in context
        assert "<user>Hello</user>" in context
        assert "<assistant>Hi!</assistant>" in context

    def test_build_context_max_turns(self) -> None:
        memory = ConversationMemory(max_turns=1)
        for i in range(10):
            memory.add_user(f"User {i}")
            memory.add_assistant(f"Assistant {i}")
        context = memory.build_context()
        assert "User 8" not in context
        assert "User 9" in context

    def test_clear(self) -> None:
        memory = ConversationMemory()
        memory.add_user("Hello")
        memory.clear()
        assert len(memory) == 0
        assert memory.build_context() == ""

    def test_to_list(self) -> None:
        memory = ConversationMemory()
        memory.add_user("Hello")
        memory.add_assistant("Hi!")
        result = memory.to_list()
        assert len(result) == 2
        assert isinstance(result, list)


class TestKeyInfoMemory:
    def test_empty_key_info(self) -> None:
        memory = KeyInfoMemory()
        assert len(memory) == 0
        assert memory.build_memory_xml() == "<memory></memory>"

    def test_add_item(self) -> None:
        memory = KeyInfoMemory()
        memory.add("Important info")
        assert len(memory) == 1
        assert memory.contains("Important info")

    def test_add_duplicate(self) -> None:
        memory = KeyInfoMemory()
        memory.add("Info")
        memory.add("Info")
        assert len(memory) == 1

    def test_add_different_items(self) -> None:
        memory = KeyInfoMemory()
        memory.add("Info 1")
        memory.add("Info 2")
        assert len(memory) == 2

    def test_remove_item(self) -> None:
        memory = KeyInfoMemory()
        memory.add("Info")
        result = memory.remove("Info")
        assert result is True
        assert len(memory) == 0

    def test_remove_nonexistent(self) -> None:
        memory = KeyInfoMemory()
        result = memory.remove("Not exists")
        assert result is False

    def test_max_items(self) -> None:
        memory = KeyInfoMemory(max_items=3)
        for i in range(5):
            memory.add(f"Info {i}")
        assert len(memory) == 3
        assert memory.contains("Info 4")
        assert not memory.contains("Info 0")

    def test_build_memory_xml(self) -> None:
        memory = KeyInfoMemory()
        memory.add("Item 1")
        memory.add("Item 2")
        xml = memory.build_memory_xml()
        assert "<memory>" in xml
        assert "<item>Item 1</item>" in xml
        assert "<item>Item 2</item>" in xml

    def test_clear(self) -> None:
        memory = KeyInfoMemory()
        memory.add("Info")
        memory.clear()
        assert len(memory) == 0


class TestMemoryManager:
    def test_update_with_user(self) -> None:
        manager = MemoryManager()
        manager.update(user_input="Hello")
        assert len(manager.conversation) == 1

    def test_update_with_all_params(self) -> None:
        manager = MemoryManager()
        manager.update(
            user_input="Hello",
            assistant_response="Hi!",
            tool_result="Command output",
        )
        assert len(manager.conversation) == 3

    def test_build_context(self) -> None:
        manager = MemoryManager()
        manager.update(user_input="Hello", assistant_response="Hi!")
        manager.key_info.add("Key info")
        context = manager.build_context()
        assert "<history>" in context
        assert "<memory>" in context

    def test_outside_access_grant(self) -> None:
        manager = MemoryManager()
        manager.grant_outside_access("/tmp/outside")
        assert manager.is_outside_access_granted("/tmp/outside")
        assert not manager.is_outside_access_granted("/tmp/other")

    def test_clear_all(self) -> None:
        manager = MemoryManager()
        manager.update(user_input="Hello")
        manager.key_info.add("Key")
        manager.grant_outside_access("/tmp")
        manager.clear_all()
        assert len(manager.conversation) == 0
        assert len(manager.key_info) == 0
        assert not manager.is_outside_access_granted("/tmp")

    def test_to_dict_from_dict(self) -> None:
        manager = MemoryManager()
        manager.update(user_input="Hello", assistant_response="Hi!")
        manager.key_info.add("Key")
        data = manager.to_dict()

        restored = MemoryManager.from_dict(data)
        assert len(restored.conversation) == 2
        assert len(restored.key_info) == 1


class TestExtractKeyInfo:
    def test_extract_single_item(self) -> None:
        text = "<memory><item>Key 1</item></memory>"
        result = extract_key_info_from_text(text)
        assert result == ["Key 1"]

    def test_extract_multiple_items(self) -> None:
        text = "<memory><item>Key 1</item><item>Key 2</item></memory>"
        result = extract_key_info_from_text(text)
        assert len(result) == 2

    def test_no_items(self) -> None:
        text = "<memory></memory>"
        result = extract_key_info_from_text(text)
        assert result == []

    def test_item_with_whitespace(self) -> None:
        text = "<memory><item>  Key with spaces  </item></memory>"
        result = extract_key_info_from_text(text)
        assert result == ["Key with spaces"]
