import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from ns_client import NSClient
from graph_builder import GraphBuilder
import pytest
from models import NSUser, NSPhoneNumber, NSAnswerRule, NSForwardingLogic, NodeData


@pytest.mark.asyncio
async def test_offnet_graph():
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

    # Mock GET /answerrules for 101 - Points to External Number
    mock_client.get_answer_rules = AsyncMock(
        side_effect=lambda domain, user: {
            "101": [
                NSAnswerRule(
                    domain="test.domain.com",
                    user="101",
                    time_frame="*",
                    priority=1,
                    forward_always=NSForwardingLogic(
                        enabled="yes", parameters=["19095551234"]
                    ),
                )
            ]
        }.get(user, [])
    )

    # Mock AA prompts (None)
    mock_client.get_auto_attendant_prompts = AsyncMock(return_value=None)

    builder = GraphBuilder(mock_client, "test.domain.com")
    elements = await builder.build()

    # Verify we have an offnet node
    nodes = [e for e in elements if isinstance(e.data, NodeData)]
    off_node = next((n for n in nodes if n.data.type == "offnet"), None)

    assert off_node is not None
    assert off_node.data.bg == "#90EE90"
    assert "(909) 555-1234" in off_node.data.label

    print("Offnet node verified successfully.")
    print(json.dumps([e.model_dump() for e in elements], indent=2))


if __name__ == "__main__":
    asyncio.run(test_offnet_graph())
