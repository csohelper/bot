from datetime import datetime, timezone
from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Optional
import yaml
import shutil


class RemoveMessage(BaseModel):
    """Represents a message with its ID and creation timestamp."""
    message_id: int
    create_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PinMessage(BaseModel):
    """Represents a pinned help message in a specific chat."""
    chat_id: int
    message_id: int
    lang: str


class CacheStorage(BaseModel):
    """
    Stores removable and pinned messages with optional persistence to a YAML file.
    Automatically handles corrupted or missing files safely.
    """

    remove_messages: List[RemoveMessage] = Field(default_factory=list)
    help_pin_messages: List[PinMessage] = Field(default_factory=list)
    path: Path = Path("cache.yaml")

    def __init__(self, path: Optional[str | Path] = None, **data):
        """Initialize cache and ensure that the file exists."""
        super().__init__(**data)
        if path:
            self.path = Path(path)
        # Always ensure file exists
        if not self.path.exists():
            self.save()

    @staticmethod
    def from_file(path: str = "cache.yaml") -> "CacheStorage":
        """
        Create a CacheStorage instance and load data from a YAML file.

        If the file is invalid or corrupted, it will be backed up and replaced with a new empty one.
        """
        storage = CacheStorage(path=Path(path))
        storage.load()
        return storage

    def load(self) -> None:
        """
        Load data from the associated file if it exists.
        If the file is corrupted, back it up and start fresh.
        """
        if not self.path.exists():
            self.save()
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self.remove_messages = [RemoveMessage(**m) for m in data.get("remove_messages", [])]
            self.help_pin_messages = [PinMessage(**p) for p in data.get("pin_help_messages", [])]
        except Exception:
            backup_path = self._make_backup_path()
            shutil.move(self.path, backup_path)
            print(f"⚠️ Invalid cache file backed up to: {backup_path}")
            self.remove_messages = []
            self.help_pin_messages = []
            self.save()

    def _make_backup_path(self) -> Path:
        """Generate a timestamped backup filename in the same directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.path.stem}_backup_{timestamp}{self.path.suffix}"
        return self.path.with_name(backup_name)

    def save(self) -> None:
        """Save current data to the associated YAML file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {
                    "remove_messages": [m.model_dump() for m in self.remove_messages],
                    "pin_help_messages": [p.model_dump() for p in self.help_pin_messages],
                },
                f,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
            )

    def insert_message(self, message_id: int, stamp: Optional[datetime] = None) -> None:
        """Insert a new removable message into storage."""
        msg = RemoveMessage(message_id=message_id, create_time=stamp or datetime.now(timezone.utc))
        self.remove_messages.append(msg)
        self.save()

    def get_old_messages(self, delta: int) -> List[RemoveMessage]:
        """Return all removable messages older than 'delta' seconds."""
        now = datetime.now(timezone.utc)
        return [m for m in self.remove_messages if (now - m.create_time).total_seconds() > delta]

    def delete_messages(self, *message_ids: int) -> None:
        """Delete removable messages by their IDs and save the updated data."""
        ids = set(message_ids)
        self.remove_messages = [m for m in self.remove_messages if m.message_id not in ids]
        self.save()

    def add_pin_message(self, chat_id: int, message_id: int, lang: str) -> None:
        """Add a new pinned message (chat_id, message_id) if it does not already exist."""
        for pin in self.help_pin_messages:
            if pin.chat_id == chat_id and pin.message_id == message_id:
                return
        self.help_pin_messages.append(PinMessage(
            chat_id=chat_id, message_id=message_id, lang=lang
        ))
        self.save()

    def remove_pin_message(self, chat_id: int, message_id: int) -> None:
        """Remove a pinned message pair (chat_id, message_id) if it exists."""
        self.help_pin_messages = [
            pin for pin in self.help_pin_messages
            if not (pin.chat_id == chat_id and pin.message_id == message_id)
        ]
        self.save()


cache = CacheStorage.from_file("cache.yaml")
