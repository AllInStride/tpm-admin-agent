"""Async event bus for in-process pub/sub.

The event bus decouples event producers from consumers.
Publishers emit events, subscribers receive events they're interested in.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from src.events.base import Event
from src.events.store import EventStore

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Event)
EventHandler = Callable[[Event], None] | Callable[[Event], Awaitable[None]]


class EventBus:
    """Simple async event bus for in-process pub/sub.

    Features:
    - Type-safe subscriptions
    - Async handler support
    - Optional persistence via EventStore
    - Error isolation (one handler failure doesn't affect others)
    """

    def __init__(self, store: EventStore | None = None):
        """Initialize event bus.

        Args:
            store: Optional EventStore for persistence
        """
        self._subscribers: dict[type[Event], list[EventHandler]] = {}
        self._store = store
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: type[T],
        handler: Callable[[T], None] | Callable[[T], Awaitable[None]],
    ) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: The event class to subscribe to
            handler: Function to call when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.__name__}")

    def unsubscribe(
        self,
        event_type: type[T],
        handler: EventHandler,
    ) -> None:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: The event class to unsubscribe from
            handler: The handler to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Unsubscribed handler from {event_type.__name__}")
            except ValueError:
                pass  # Handler wasn't subscribed

    async def publish(self, event: Event, persist: bool = False) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The event to publish
            persist: Whether to persist event to store (if available)
        """
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])

        logger.debug(f"Publishing {event.event_type} to {len(handlers)} handler(s)")

        # Persist event if requested and store is available
        if persist and self._store:
            try:
                await self._store.append(event)
            except Exception as e:
                logger.error(f"Failed to persist event: {e}")
                raise

        # Run handlers concurrently
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(self._run_async_handler(handler, event))
            else:
                tasks.append(self._run_sync_handler(handler, event))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Log any handler errors but don't re-raise
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Handler error for {event.event_type}: {result}")

    async def publish_and_store(self, event: Event) -> None:
        """Publish event and persist to store.

        Convenience method that always persists.
        """
        await self.publish(event, persist=True)

    async def _run_async_handler(
        self,
        handler: Callable[[Event], Awaitable[None]],
        event: Event,
    ) -> None:
        """Run an async handler safely."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Async handler error: {e}")
            raise

    async def _run_sync_handler(
        self,
        handler: Callable[[Event], None],
        event: Event,
    ) -> None:
        """Run a sync handler in thread pool."""
        try:
            await asyncio.to_thread(handler, event)
        except Exception as e:
            logger.error(f"Sync handler error: {e}")
            raise

    def subscriber_count(self, event_type: type[Event]) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))
