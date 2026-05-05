"""Memory management for code5 conversation history and key info."""

import re


class ConversationMemory:
    """Manages rolling conversation history with a maximum size limit."""

    def __init__(self, max_turns: int = 10) -> None:
        self.max_turns = max_turns
        self.history: list[str] = []

    def add_user(self, content: str) -> None:
        self.history.append(f"<user>{content}</user>")

    def add_assistant(self, content: str) -> None:
        self.history.append(f"<assistant>{content}</assistant>")

    def add_tool(self, content: str) -> None:
        truncated = content[:500] if len(content) > 500 else content
        self.history.append(f"<tool>{truncated}</tool>")

    def build_context(self) -> str:
        if not self.history:
            return ""
        display_history = self.history[-(self.max_turns * 2) :]
        return "<history>\n" + "\n".join(display_history) + "\n</history>"

    def clear(self) -> None:
        self.history.clear()

    def __len__(self) -> int:
        return len(self.history)

    def to_list(self) -> list[str]:
        return self.history.copy()


class KeyInfoMemory:
    """Manages long-term key information extraction and storage."""

    def __init__(self, max_items: int = 20) -> None:
        self.max_items = max_items
        self.key_info: list[str] = []

    def add(self, item: str) -> None:
        cleaned = item.strip()
        if cleaned and cleaned not in self.key_info:
            self.key_info.append(cleaned)
            if len(self.key_info) > self.max_items:
                self.key_info.pop(0)

    def contains(self, item: str) -> bool:
        return item.strip() in self.key_info

    def remove(self, item: str) -> bool:
        cleaned = item.strip()
        if cleaned in self.key_info:
            self.key_info.remove(cleaned)
            return True
        return False

    def clear(self) -> None:
        self.key_info.clear()

    def build_memory_xml(self) -> str:
        if not self.key_info:
            return "<memory></memory>"
        items_xml = "\n".join(f"  <item>{k}</item>" for k in self.key_info)
        return f"<memory>\n{items_xml}\n</memory>"

    def __len__(self) -> int:
        return len(self.key_info)

    def to_list(self) -> list[str]:
        return self.key_info.copy()


class MemoryManager:
    """Combined memory manager for conversation and key info."""

    def __init__(self, max_turns: int = 10, max_key_info: int = 20) -> None:
        self.conversation = ConversationMemory(max_turns=max_turns)
        self.key_info = KeyInfoMemory(max_items=max_key_info)
        self._outside_access_granted: set[str] = set()

    def update(
        self,
        user_input: str | None = None,
        assistant_response: str | None = None,
        tool_result: str | None = None,
    ) -> None:
        if user_input:
            self.conversation.add_user(user_input)
        if assistant_response:
            self.conversation.add_assistant(assistant_response)
        if tool_result:
            self.conversation.add_tool(tool_result)

    def build_context(self) -> str:
        parts = []
        memory_xml = self.key_info.build_memory_xml()
        if "<item>" in memory_xml:
            parts.append(memory_xml)
        history = self.conversation.build_context()
        if history:
            parts.append(history)
        return "\n\n".join(parts)

    def grant_outside_access(self, path: str) -> None:
        self._outside_access_granted.add(path)

    def is_outside_access_granted(self, path: str) -> bool:
        return path in self._outside_access_granted

    def clear_all(self) -> None:
        self.conversation.clear()
        self.key_info.clear()
        self._outside_access_granted.clear()

    def to_dict(self) -> dict:
        return {
            "conversation": self.conversation.to_list(),
            "key_info": self.key_info.to_list(),
            "outside_access_granted": list(self._outside_access_granted),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryManager":
        manager = cls()
        manager.conversation.history = data.get("conversation", [])
        manager.key_info.key_info = data.get("key_info", [])
        manager._outside_access_granted = set(data.get("outside_access_granted", []))
        return manager


def extract_key_info_from_text(text: str) -> list[str]:
    """Extract key info items from LLM response text.

    Args:
        text: Response text potentially containing <item> tags

    Returns:
        List of extracted items
    """
    pattern = r"<item>(.*?)</item>"
    matches = re.findall(pattern, text, re.DOTALL)
    return [m.strip() for m in matches if m.strip()]
