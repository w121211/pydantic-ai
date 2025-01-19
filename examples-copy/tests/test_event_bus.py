import asyncio
from datetime import datetime

import pytest

from playground.event_bus import EventBus

from .type_defs import BaseEvent, EventType


# Helper Event classes for testing
class TestEvent(BaseEvent):
    type: EventType = EventType.TASK_CREATED_EVENT
    task_id: str = 'test_task'


class TestEvent2(BaseEvent):
    type: EventType = EventType.TASK_LOADED_EVENT
    task_id: str = 'test_task'


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def test_event():
    return TestEvent(timestamp=datetime.now())


@pytest.fixture
def test_event2():
    return TestEvent2(timestamp=datetime.now())


async def test_subscribe_and_publish_sync_handler(event_bus, test_event):
    received_events = []

    def handler(event):
        received_events.append(event)

    event_bus.subscribe(EventType.TASK_CREATED_EVENT, handler)
    await event_bus.publish(test_event)

    # Give event loop a chance to process
    await asyncio.sleep(0)

    assert len(received_events) == 1
    assert received_events[0] == test_event


async def test_subscribe_and_publish_async_handler(event_bus, test_event):
    received_events = []

    async def handler(event):
        received_events.append(event)

    event_bus.subscribe_async(EventType.TASK_CREATED_EVENT, handler)
    await event_bus.publish(test_event)

    # Give event loop a chance to process
    await asyncio.sleep(0)

    assert len(received_events) == 1
    assert received_events[0] == test_event


async def test_multiple_handlers_receive_events(event_bus, test_event):
    received_sync = []
    received_async = []

    def sync_handler(event):
        received_sync.append(event)

    async def async_handler(event):
        received_async.append(event)

    event_bus.subscribe(EventType.TASK_CREATED_EVENT, sync_handler)
    event_bus.subscribe_async(EventType.TASK_CREATED_EVENT, async_handler)

    await event_bus.publish(test_event)
    await asyncio.sleep(0)

    assert len(received_sync) == 1
    assert len(received_async) == 1
    assert received_sync[0] == test_event
    assert received_async[0] == test_event


async def test_unsubscribe_sync_handler(event_bus, test_event):
    received_events = []

    def handler(event):
        received_events.append(event)

    event_bus.subscribe(EventType.TASK_CREATED_EVENT, handler)
    event_bus.unsubscribe(EventType.TASK_CREATED_EVENT, handler)

    await event_bus.publish(test_event)
    await asyncio.sleep(0)

    assert len(received_events) == 0


async def test_unsubscribe_async_handler(event_bus, test_event):
    received_events = []

    async def handler(event):
        received_events.append(event)

    event_bus.subscribe_async(EventType.TASK_CREATED_EVENT, handler)
    event_bus.unsubscribe(EventType.TASK_CREATED_EVENT, handler)

    await event_bus.publish(test_event)
    await asyncio.sleep(0)

    assert len(received_events) == 0


async def test_handlers_receive_only_subscribed_events(
    event_bus, test_event, test_event2
):
    received_events = []

    def handler(event):
        received_events.append(event)

    event_bus.subscribe(EventType.TASK_CREATED_EVENT, handler)

    # Publish both events
    await event_bus.publish(test_event)  # Should be received
    await event_bus.publish(test_event2)  # Should not be received

    await asyncio.sleep(0)

    assert len(received_events) == 1
    assert received_events[0] == test_event


async def test_handler_exception_does_not_block_other_handlers(event_bus, test_event):
    received_events = []

    def failing_handler(event):
        raise Exception('Test exception')

    def working_handler(event):
        received_events.append(event)

    event_bus.subscribe(EventType.TASK_CREATED_EVENT, failing_handler)
    event_bus.subscribe(EventType.TASK_CREATED_EVENT, working_handler)

    await event_bus.publish(test_event)
    await asyncio.sleep(0)

    assert len(received_events) == 1
    assert received_events[0] == test_event
