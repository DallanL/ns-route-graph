from unittest.mock import AsyncMock, MagicMock

import pytest

from graph_builder import GraphBuilder
from models import NodeData, NSPhoneNumber, NSUser
from ns_client import NSClient


@pytest.mark.asyncio
async def test_special_patterns():
    mock_client = MagicMock(spec=NSClient)
    mock_client.get_users = AsyncMock(
        return_value=[
            NSUser(
                user="400",
                domain="test.com",
                name_first_name="User",
                name_last_name="400",
            )
        ]
    )
    mock_client.get_domain_timeframes = AsyncMock(return_value=[])

    # DIDs with special patterns
    mock_client.get_dids = AsyncMock(
        return_value=[
            NSPhoneNumber(
                phonenumber="16262553901",
                domain="test.com",
                dest="16262553901_callqueue_400",
            ),
            NSPhoneNumber(
                phonenumber="16262553902",
                domain="test.com",
                dest="16262553902_attendant_400",
            ),
            NSPhoneNumber(
                phonenumber="16262553903",
                domain="test.com",
                dest="16262553901_pstn_12135551212",
            ),
        ]
    )

    mock_client.get_answer_rules = AsyncMock(return_value=[])
    mock_client.get_auto_attendant_prompts = AsyncMock(return_value=None)
    mock_client.get_call_queue_agents = AsyncMock(return_value=[])

    builder = GraphBuilder(mock_client, "test.com")
    elements = await builder.build()

    # 1. Check for callqueue_400
    queue_node = next(
        (
            e
            for e in elements
            if isinstance(e.data, NodeData) and e.data.type == "call_queue"
        ),
        None,
    )
    assert queue_node is not None, "Call queue node not found"
    assert isinstance(queue_node.data, NodeData)
    assert queue_node.data.label == "Queue: 400"
    assert queue_node.data.parent == "user_400"

    # 2. Check for attendant_400
    user_node = next(
        (
            e
            for e in elements
            if isinstance(e.data, NodeData) and e.data.id == "user_400"
        ),
        None,
    )
    assert user_node is not None, "User 400 node not found"

    # 3. Check for pstn_12135551212
    offnet_node = next(
        (
            e
            for e in elements
            if isinstance(e.data, NodeData)
            and e.data.type == "offnet"
            and e.data.id == "offnet_12135551212"
        ),
        None,
    )
    assert offnet_node is not None, "Offnet node not found"
