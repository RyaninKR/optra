from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

from notion_client import Client
from notion_client.errors import APIResponseError, HTTPResponseError

from worklog.adapters.base import BaseAdapter
from worklog.config import get_notion_token
from worklog.models.work_item import ItemType, Source, WorkItem


class NotionAdapter(BaseAdapter):
    """Collects pages and database entries from Notion."""

    RATE_LIMIT_DELAY = 0.35  # ~3 req/sec

    def __init__(self, token: Optional[str] = None):
        resolved = token or get_notion_token()
        if not resolved:
            raise ValueError(
                "Notion token not found. Run 'worklog auth notion' or set NOTION_TOKEN in .env"
            )
        self._client = Client(auth=resolved)

    def _rate_limit(self) -> None:
        time.sleep(self.RATE_LIMIT_DELAY)

    def _extract_title(self, page: dict) -> str:
        """Extract title from a Notion page's properties."""
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_parts = prop.get("title", [])
                return "".join(t.get("plain_text", "") for t in title_parts)
        return "Untitled"

    def _extract_blocks_text(self, block_id: str) -> str:
        """Recursively extract plain text from all blocks in a page."""
        texts: list[str] = []
        cursor: Optional[str] = None

        while True:
            self._rate_limit()
            try:
                kwargs: dict[str, Any] = {"block_id": block_id, "page_size": 100}
                if cursor:
                    kwargs["start_cursor"] = cursor

                resp = self._client.blocks.children.list(**kwargs)
            except (APIResponseError, HTTPResponseError) as e:
                if hasattr(e, "status") and e.status == 429:
                    time.sleep(2)
                    continue
                raise

            for block in resp.get("results", []):
                block_type = block.get("type", "")
                block_data = block.get(block_type, {})

                # Extract rich_text from the block
                rich_text = block_data.get("rich_text", [])
                if rich_text:
                    line = "".join(rt.get("plain_text", "") for rt in rich_text)
                    texts.append(line)

                # Handle child blocks recursively
                if block.get("has_children", False):
                    child_text = self._extract_blocks_text(block["id"])
                    if child_text:
                        texts.append(child_text)

            if not resp.get("has_more", False):
                break
            cursor = resp.get("next_cursor")

        return "\n".join(texts)

    def _classify_item_type(self, page: dict) -> ItemType:
        """Classify a Notion page into an ItemType based on its parent."""
        parent = page.get("parent", {})
        parent_type = parent.get("type", "")

        if parent_type == "database_id":
            return ItemType.task
        return ItemType.page

    def _get_participants(self, page: dict) -> list[str]:
        """Extract creator/editor info from page."""
        participants = []
        created_by = page.get("created_by", {})
        if created_by.get("name"):
            participants.append(created_by["name"])
        elif created_by.get("id"):
            participants.append(created_by["id"])

        last_edited_by = page.get("last_edited_by", {})
        editor_name = last_edited_by.get("name") or last_edited_by.get("id", "")
        if editor_name and editor_name not in participants:
            participants.append(editor_name)

        return participants

    def _get_parent_name(self, page: dict) -> str:
        """Get the parent database or page name (best effort)."""
        parent = page.get("parent", {})
        parent_type = parent.get("type", "")

        if parent_type == "database_id":
            try:
                self._rate_limit()
                db = self._client.databases.retrieve(database_id=parent["database_id"])
                title_parts = db.get("title", [])
                return "".join(t.get("plain_text", "") for t in title_parts) or "Database"
            except Exception:
                return "Database"
        elif parent_type == "page_id":
            return "Subpage"
        return "Workspace"

    def _search_pages(self, since: Optional[datetime] = None) -> list[dict]:
        """Search for all pages shared with the integration."""
        pages: list[dict] = []
        cursor: Optional[str] = None

        while True:
            self._rate_limit()
            try:
                kwargs: dict[str, Any] = {
                    "filter": {"property": "object", "value": "page"},
                    "sort": {
                        "direction": "descending",
                        "timestamp": "last_edited_time",
                    },
                    "page_size": 100,
                }
                if cursor:
                    kwargs["start_cursor"] = cursor

                resp = self._client.search(**kwargs)
            except (APIResponseError, HTTPResponseError) as e:
                if hasattr(e, "status") and e.status == 429:
                    time.sleep(2)
                    continue
                raise

            for page in resp.get("results", []):
                last_edited = page.get("last_edited_time", "")
                if since and last_edited:
                    edited_dt = datetime.fromisoformat(last_edited.replace("Z", "+00:00"))
                    if edited_dt < since:
                        # Pages are sorted by last_edited descending, so we can stop
                        return pages
                pages.append(page)

            if not resp.get("has_more", False):
                break
            cursor = resp.get("next_cursor")

        return pages

    def _page_to_work_item(self, page: dict, fetch_content: bool = True) -> WorkItem:
        """Convert a Notion page to a WorkItem."""
        title = self._extract_title(page)
        page_id = page["id"]

        content = title
        if fetch_content:
            body = self._extract_blocks_text(page_id)
            if body:
                content = f"{title}\n\n{body}"

        created_time = page.get("created_time", "")
        last_edited = page.get("last_edited_time", created_time)
        timestamp = datetime.fromisoformat(last_edited.replace("Z", "+00:00"))

        return WorkItem(
            source=Source.notion,
            source_id=page_id,
            item_type=self._classify_item_type(page),
            content=content,
            channel_or_space=self._get_parent_name(page),
            participants=self._get_participants(page),
            timestamp=timestamp,
            metadata_={
                "page_id": page_id,
                "url": page.get("url", ""),
                "created_time": created_time,
                "last_edited_time": last_edited,
                "title": title,
                "archived": page.get("archived", False),
            },
        )

    def collect(self, since: Optional[datetime] = None) -> list[WorkItem]:
        """Collect pages from Notion.

        Args:
            since: Only collect pages edited after this timestamp.

        Returns:
            List of WorkItem objects.
        """
        pages = self._search_pages(since=since)
        items: list[WorkItem] = []

        for page in pages:
            if page.get("archived", False):
                continue
            item = self._page_to_work_item(page)
            items.append(item)

        return items
