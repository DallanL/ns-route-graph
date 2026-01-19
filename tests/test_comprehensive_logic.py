import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from ns_client import NSClient
from graph_builder import GraphBuilder
from models import NSUser, NSPhoneNumber, NSAnswerRule, NSForwardingLogic, NodeData


@pytest.mark.asyncio
async def test_comprehensive_logic():
    # Mock the NSClient
    mock_client = MagicMock(spec=NSClient)

    # Mock GET /users
    mock_client.get_users = AsyncMock(
        return_value=[
            NSUser(
                user="101",
                domain="test.domain.com",
                name_first_name="Alice",
                name_last_name="Smith",
            )
        ]
    )

    # Mock GET /timeframes
    mock_client.get_domain_timeframes = AsyncMock(return_value=[])

    # Mock GET /phonenumbers (DIDs)
    mock_client.get_dids = AsyncMock(
        return_value=[
            NSPhoneNumber(
                phonenumber="5550001000", domain="test.domain.com", dest="101"
            )
        ]
    )

    # Mock GET /answerrules for 101 - Points to variety of targets
    mock_client.get_answer_rules = AsyncMock(
        side_effect=lambda domain, user: {
            "101": [
                NSAnswerRule(
                    domain="test.domain.com",
                    user="101",
                    time_frame="*",
                    priority=1,
                    forward_always=NSForwardingLogic(
                        enabled="yes", parameters=["phone_mac123"]
                    ),  # Device
                    forward_on_busy=NSForwardingLogic(
                        enabled="yes", parameters=["hangup"]
                    ),  # Hangup
                    simultaneous_ring=NSForwardingLogic(
                        enabled="yes", parameters=["unknown_target"]
                    ),  # Other
                )
            ]
        }.get(user, [])
    )

    # Mock AA prompts (None)
    mock_client.get_auto_attendant_prompts = AsyncMock(return_value=None)

    builder = GraphBuilder(mock_client, "test.domain.com")
    elements = await builder.build()

    # Verify Device Node
    dev_node = next(
        (
            e
            for e in elements
            if isinstance(e.data, NodeData) and e.data.type == "device"
        ),
        None,
    )
    assert dev_node is not None
    assert dev_node.data.label == "Device: mac123"

    # Verify Hangup Node
    hang_node = next(
        (
            e
            for e in elements
            if isinstance(e.data, NodeData) and e.data.type == "hangup"
        ),
        None,
    )
    assert hang_node is not None
    assert hang_node.data.label == "Hangup"

    # Verify Other Node
    other_node = next(
        (
            e
            for e in elements
            if isinstance(e.data, NodeData) and e.data.type == "other"
        ),
        None,
    )
    assert other_node is not None
    assert other_node.data.label == "Other: unknown_target"

    print("Comprehensive logic verified successfully.")
    print(json.dumps([e.model_dump() for e in elements], indent=2))


if __name__ == "__main__":
    asyncio.run(test_comprehensive_logic())
