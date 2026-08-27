"""Test layout.

The tests come in two kinds, and they run in different places.

``tests/core`` and ``tests/agents`` are unit tests. Each runs inside the
virtualenv of the thing it tests, because that is the only environment where
that thing can be imported at all. ``scripts/run_tests.sh`` does this for you.

``tests/network`` are integration tests. They run in the core virtualenv and
talk to the running network the way any other client would, over A2A and MCP.
They skip themselves when nothing is listening.
"""
