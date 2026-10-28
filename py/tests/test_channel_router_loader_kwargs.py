"""The channel router accepts the sub-router kwargs zoid6's loader sends, and keeps session_registry.

zoid6 builds each sub-router with session_registry, secret, token_store, instance_id, clock and
config. A TypeError on the first attempt makes the loader fall back to a bare constructor and drop
session_registry, which left the channel handler unable to see the logged-in member.
"""

import argparse

from bbsengine6.channel.api.handler import MessageRouter


def test_router_accepts_the_loader_kwargs_and_keeps_session_registry():
    registry = object()
    router = MessageRouter(
        argparse.Namespace(),
        session_registry=registry,
        secret=None,
        token_store=None,
        instance_id=None,
        clock=None,
        config={},
    )
    assert router.sessions is registry


def test_router_without_session_registry_keeps_a_private_store():
    router = MessageRouter(argparse.Namespace(), config={})
    assert router.sessions is not None
