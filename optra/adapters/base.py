from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from optra.models.work_item import WorkItem


class BaseAdapter(ABC):
    """Base interface for all source adapters."""

    @abstractmethod
    def collect(self, since: Optional[datetime] = None) -> list[WorkItem]:
        """Collect work items from the source.

        Args:
            since: Only collect items after this timestamp. If None, collect all.

        Returns:
            List of normalized WorkItem objects.
        """
        ...
