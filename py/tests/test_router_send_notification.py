# test_router_send_notification.py
# Tests for InternetRouter.send_notification() — the migration from
# legacy bbsengine6.notify to the message system.

import asyncio
from unittest.mock import MagicMock, patch


from bbsengine6.net.router import InternetRouter


class TestSendNotification:
    """send_notification must route through message.store_message.

    Pre-migration this method called ``bbsengine6.notify.notify(...)``
    which no longer exists. Each recipient should receive one message
    with the body as content and the subject as channel.
    """

    def _run(self, coro):
        return asyncio.run(coro)

    def test_routes_each_recipient_via_message_store(self):
        router = InternetRouter(local_machine="local")
        with patch("bbsengine6.message.store_message") as mock_store:
            results = self._run(
                router.send_notification(
                    {
                        "subject": "system.alert",
                        "body": "Hello!",
                        "priority": "normal",
                    },
                    ["alice", "bob"],
                )
            )

        assert results == {"alice": "ok", "bob": "ok"}
        assert mock_store.call_count == 2
        # Every call uses the same channel and body; recipients differ.
        for call in mock_store.call_args_list:
            kwargs = call.kwargs
            assert kwargs["channel"] == "system.alert"
            assert kwargs["content"] == "Hello!"
            assert kwargs["sender_moniker"] is None
            assert len(kwargs["recipient_monikers"]) == 1

    def test_priority_maps_to_urgency(self):
        router = InternetRouter()
        with patch("bbsengine6.message.store_message") as mock_store:
            self._run(
                router.send_notification(
                    {"subject": "x", "body": "b", "priority": "urgent"},
                    ["alice"],
                )
            )
        assert mock_store.call_args.kwargs["urgency"] == "URGENT"

    def test_default_urgency_is_routine(self):
        router = InternetRouter()
        with patch("bbsengine6.message.store_message") as mock_store:
            self._run(
                router.send_notification(
                    {"subject": "x", "body": "b"},
                    ["alice"],
                )
            )
        assert mock_store.call_args.kwargs["urgency"] == "ROUTINE"

    def test_unknown_priority_falls_back_to_routine(self):
        router = InternetRouter()
        with patch("bbsengine6.message.store_message") as mock_store:
            self._run(
                router.send_notification(
                    {"subject": "x", "body": "b", "priority": "bogus"},
                    ["alice"],
                )
            )
        assert mock_store.call_args.kwargs["urgency"] == "ROUTINE"

    def test_missing_subject_uses_default_channel(self):
        router = InternetRouter()
        with patch("bbsengine6.message.store_message") as mock_store:
            self._run(
                router.send_notification(
                    {"body": "no subject"},
                    ["alice"],
                )
            )
        assert mock_store.call_args.kwargs["channel"] == "system:direct"

    def test_per_recipient_failure_does_not_stop_others(self):
        router = InternetRouter()

        call_count = {"n": 0}

        def side_effect(*_a, **_kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("db is down")
            return 1

        with patch(
            "bbsengine6.message.store_message",
            side_effect=side_effect,
        ):
            results = self._run(
                router.send_notification(
                    {"subject": "x", "body": "b"},
                    ["alice", "bob"],
                )
            )

        assert "db is down" in results["alice"]
        assert results["bob"] == "ok"

    def test_all_priorities_are_mapped(self):
        router = InternetRouter()
        for priority, expected in [
            ("low", "ROUTINE"),
            ("normal", "ROUTINE"),
            ("high", "IMPORTANT"),
            ("urgent", "URGENT"),
            ("critical", "CRITICAL"),
        ]:
            with patch("bbsengine6.message.store_message") as mock_store:
                self._run(
                    router.send_notification(
                        {"subject": "x", "body": "b", "priority": priority},
                        ["alice"],
                    )
                )
            assert mock_store.call_args.kwargs["urgency"] == expected, (
                f"priority={priority} -> urgency={expected}"
            )

    def test_legacy_notify_is_no_longer_called(self):
        """Regression: ensure the deleted notify module is not imported."""
        router = InternetRouter()
        with patch("bbsengine6.message.store_message") as mock_store:
            with patch.dict("sys.modules", {"bbsengine6.notify": MagicMock()}):
                # Even if a stale notify module is somehow importable,
                # the router must not call it.
                with patch("bbsengine6.notify.notify") as mock_legacy_notify:
                    self._run(
                        router.send_notification(
                            {"subject": "x", "body": "b"},
                            ["alice"],
                        )
                    )
                    mock_legacy_notify.assert_not_called()
        assert mock_store.call_count == 1
