# realtime/event_bus.py

from collections import defaultdict

class EventBus:
    """A simple publish-subscribe event bus for decoupling system components."""
    def __init__(self):
        self._listeners = defaultdict(list)

    def subscribe(self, event_type: str, listener):
        """Register a listener for a specific event type."""
        self._listeners[event_type].append(listener)
        print(f"Listener {listener.__name__} subscribed to '{event_type}'")

    def unsubscribe(self, event_type: str, listener):
        """Remove a listener from an event type."""
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            print(f"Listener {listener.__name__} unsubscribed from '{event_type}'")

    def publish(self, event_type: str, *args, **kwargs):
        """Publish an event, calling all subscribed listeners."""
        print(f"Publishing event '{event_type}' with args: {args} kwargs: {kwargs}")
        for listener in self._listeners[event_type]:
            try:
                listener(*args, **kwargs)
            except Exception as e:
                print(f"Error in listener {listener.__name__} for event '{event_type}': {e}")

# Singleton instance to be used across the application
event_bus = EventBus()
