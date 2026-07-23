"""Thread-safe JSON storage and resolution for saved locations and favorite cities."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path


class LocationRegistry:
    """Thread-safe location and city registry backed by a JSON file."""

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        self.lock = threading.RLock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create the registry file with default structure if it does not exist."""
        with self.lock:
            if not self.filepath.exists():
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
                default_data = {
                    "saved_locations": {},
                    "favorite_cities": {}
                }
                self._save(default_data)

    def _load(self) -> dict:
        """Load the registry data from disk. Assumes lock is held."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # In case of corruption or read error, return clean skeleton
            return {"saved_locations": {}, "favorite_cities": {}}

    def _save(self, data: dict) -> None:
        """Save the registry data to disk. Assumes lock is held."""
        temp_file = self.filepath.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.filepath)
        except Exception:
            if temp_file.exists():
                temp_file.unlink()
            raise

    def resolve(self, name: str) -> dict | None:
        """
        Resolve a name to location details (latitude, longitude, timezone).
        Checks saved_locations first, then favorite_cities, case-insensitively.
        """
        if not name:
            return None
            
        normalized = name.strip().lower()
        with self.lock:
            data = self._load()
            
            # Check saved locations
            for key, val in data.get("saved_locations", {}).items():
                if key.strip().lower() == normalized:
                    return val
                    
            # Check favorite cities
            for key, val in data.get("favorite_cities", {}).items():
                if key.strip().lower() == normalized:
                    return val
                    
        return None

    def get_all(self, category: str) -> dict:
        """Get all entries for a specific category ('saved_locations' or 'favorite_cities')."""
        if category not in ("saved_locations", "favorite_cities"):
            raise ValueError(f"Invalid category: {category}")
            
        with self.lock:
            data = self._load()
            return data.get(category, {})

    def add_entry(self, category: str, name: str, data: dict) -> None:
        """Add or update an entry in a category."""
        if category not in ("saved_locations", "favorite_cities"):
            raise ValueError(f"Invalid category: {category}")
        if not name or not name.strip():
            raise ValueError("Entry name is required")
            
        cleaned_name = name.strip()
        with self.lock:
            registry_data = self._load()
            if category not in registry_data:
                registry_data[category] = {}
            registry_data[category][cleaned_name] = data
            self._save(registry_data)

    def delete_entry(self, category: str, name: str) -> bool:
        """Delete an entry from a category. Returns True if deleted, False otherwise."""
        if category not in ("saved_locations", "favorite_cities"):
            raise ValueError(f"Invalid category: {category}")
            
        normalized = name.strip().lower()
        with self.lock:
            registry_data = self._load()
            category_data = registry_data.get(category, {})
            
            # Find key case-insensitively
            target_key = None
            for key in category_data:
                if key.strip().lower() == normalized:
                    target_key = key
                    break
                    
            if target_key is not None:
                del category_data[target_key]
                self._save(registry_data)
                return True
                
        return False
