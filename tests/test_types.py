"""Tests for pykour.types module."""

from collections.abc import Callable, MutableMapping
from typing import Any, get_args, get_origin

from pykour.types import ASGIApp, Message, Receive, Scope, Send


class TestTypeDefinitions:
    """Test that type aliases are correctly defined."""

    def test_scope_is_mutable_mapping(self) -> None:
        """Scope should be a MutableMapping[str, Any]."""
        assert get_origin(Scope) is MutableMapping
        args = get_args(Scope)
        assert args == (str, Any)

    def test_message_is_mutable_mapping(self) -> None:
        """Message should be a MutableMapping[str, Any]."""
        assert get_origin(Message) is MutableMapping
        args = get_args(Message)
        assert args == (str, Any)

    def test_receive_is_callable(self) -> None:
        """Receive should be a Callable returning Awaitable[Message]."""
        assert get_origin(Receive) is Callable

    def test_send_is_callable(self) -> None:
        """Send should be a Callable returning Awaitable[None]."""
        assert get_origin(Send) is Callable

    def test_asgi_app_is_callable(self) -> None:
        """ASGIApp should be a Callable."""
        assert get_origin(ASGIApp) is Callable
