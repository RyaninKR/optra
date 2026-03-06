from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from worklog.adapters.base import BaseAdapter
from worklog.config import settings
from worklog.models.work_item import ItemType, Source, WorkItem


class SlackAdapter(BaseAdapter):
    """Collects messages from Slack channels the bot has access to."""

    def __init__(self, token: Optional[str] = None):
        self._client = WebClient(token=token or settings.slack_bot_token)
        self._user_cache: dict[str, str] = {}
        self._bot_user_id: Optional[str] = None

    def _get_bot_user_id(self) -> str:
        if self._bot_user_id is None:
            resp = self._client.auth_test()
            self._bot_user_id = resp["user_id"]
        return self._bot_user_id

    def _resolve_user(self, user_id: str) -> str:
        if user_id not in self._user_cache:
            try:
                resp = self._client.users_info(user=user_id)
                profile = resp["user"]["profile"]
                self._user_cache[user_id] = (
                    profile.get("display_name")
                    or profile.get("real_name")
                    or user_id
                )
            except SlackApiError:
                self._user_cache[user_id] = user_id
        return self._user_cache[user_id]

    def _list_channels(self) -> list[dict]:
        """List all channels the bot is a member of."""
        channels = []
        cursor = None
        while True:
            resp = self._client.conversations_list(
                types="public_channel,private_channel,im,mpim",
                exclude_archived=True,
                limit=200,
                cursor=cursor,
            )
            for ch in resp["channels"]:
                if ch.get("is_member", False) or ch.get("is_im", False):
                    channels.append(ch)
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        return channels

    def _get_channel_name(self, channel: dict) -> str:
        if channel.get("is_im"):
            user_id = channel.get("user", "")
            return f"DM:{self._resolve_user(user_id)}"
        return channel.get("name", channel["id"])

    def _fetch_messages(
        self,
        channel_id: str,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch messages from a channel with pagination and rate limit handling."""
        messages = []
        cursor = None
        oldest = str(since.timestamp()) if since else None

        while True:
            try:
                kwargs: dict = {"channel": channel_id, "limit": 200}
                if oldest:
                    kwargs["oldest"] = oldest
                if cursor:
                    kwargs["cursor"] = cursor

                resp = self._client.conversations_history(**kwargs)
                messages.extend(resp.get("messages", []))

                cursor = resp.get("response_metadata", {}).get("next_cursor")
                if not cursor or not resp.get("has_more", False):
                    break
            except SlackApiError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 5))
                    time.sleep(retry_after)
                    continue
                raise

        return messages

    def _fetch_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> list[dict]:
        """Fetch replies in a thread."""
        replies = []
        cursor = None

        while True:
            try:
                kwargs: dict = {
                    "channel": channel_id,
                    "ts": thread_ts,
                    "limit": 200,
                }
                if cursor:
                    kwargs["cursor"] = cursor

                resp = self._client.conversations_replies(**kwargs)
                # Skip the first message (parent) as it's already captured
                batch = resp.get("messages", [])
                if not cursor and batch:
                    batch = batch[1:]
                replies.extend(batch)

                cursor = resp.get("response_metadata", {}).get("next_cursor")
                if not cursor or not resp.get("has_more", False):
                    break
            except SlackApiError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 5))
                    time.sleep(retry_after)
                    continue
                raise

        return replies

    def _message_to_work_item(
        self,
        msg: dict,
        channel_name: str,
        item_type: ItemType = ItemType.message,
    ) -> WorkItem:
        user_id = msg.get("user", "unknown")
        ts = float(msg.get("ts", 0))

        return WorkItem(
            source=Source.slack,
            source_id=msg.get("client_msg_id", msg.get("ts", "")),
            item_type=item_type,
            content=msg.get("text", ""),
            channel_or_space=channel_name,
            participants=[self._resolve_user(user_id)] if user_id != "unknown" else [],
            timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
            metadata_={
                "channel_id": msg.get("channel", ""),
                "thread_ts": msg.get("thread_ts"),
                "ts": msg.get("ts"),
                "subtype": msg.get("subtype"),
            },
        )

    def collect(self, since: Optional[datetime] = None) -> list[WorkItem]:
        """Collect messages from all accessible Slack channels.

        Args:
            since: Only collect messages after this timestamp.

        Returns:
            List of WorkItem objects.
        """
        bot_user_id = self._get_bot_user_id()
        channels = self._list_channels()
        items: list[WorkItem] = []

        for channel in channels:
            channel_id = channel["id"]
            channel_name = self._get_channel_name(channel)

            messages = self._fetch_messages(channel_id, since=since)

            for msg in messages:
                # Skip bot messages and subtypes like channel_join
                if msg.get("subtype") and msg["subtype"] not in ("file_share", "thread_broadcast"):
                    continue

                item = self._message_to_work_item(msg, channel_name)
                item.metadata_["channel_id"] = channel_id
                items.append(item)

                # If message has a thread, fetch replies
                if msg.get("reply_count", 0) > 0:
                    thread_ts = msg["ts"]
                    replies = self._fetch_thread_replies(channel_id, thread_ts)
                    for reply in replies:
                        if reply.get("subtype"):
                            continue
                        reply_item = self._message_to_work_item(
                            reply, channel_name, item_type=ItemType.thread
                        )
                        reply_item.metadata_["channel_id"] = channel_id
                        items.append(reply_item)

        return items
