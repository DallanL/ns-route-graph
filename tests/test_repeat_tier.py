from unittest.mock import AsyncMock, MagicMock

import pytest

from graph_builder import GraphBuilder
from models import NSAutoAttendantOption, NSAutoAttendantResponse, NSPhoneNumber
from ns_client import NSClient


@pytest.mark.asyncio
async def test_repeat_tier_self_loop():
    # Mock the NSClient
    mock_client = MagicMock(spec=NSClient)

    # Mock global data
    mock_client.get_users = AsyncMock(return_value=[])
    mock_client.get_domain_timeframes = AsyncMock(return_value=[])

    # Mock DID -> AA
    mock_client.get_dids = AsyncMock(
        return_value=[
            NSPhoneNumber(
                phonenumber="5551234567",
                domain="test.domain.com",
                dest="101:Prompt_Repeat",
                application="auto-attendant",
            )
        ]
    )

    # Mock AA with repeat-tier
    mock_client.get_auto_attendant_prompts = AsyncMock(
        return_value=NSAutoAttendantResponse(
            attendant_name="Repeat AA",
            user="101",
            starting_prompt="Prompt_Repeat",
            auto_attendant={
                "option-1": NSAutoAttendantOption(
                    description="Repeat Logic", destination_application="repeat-tier"
                ),
                "option-2": NSAutoAttendantOption(
                    description="End", destination_application="hangup"
                ),
            },
        )
    )

    builder = GraphBuilder(mock_client, "test.domain.com")
    elements = await builder.build()

    # Identify the AA node ID
    # Based on graph_builder logic: auto_attendant_101_Prompt_Repeat
    aa_node_id = "auto_attendant_101_Prompt_Repeat"

    aa_node = next((e for e in elements if e.data.id == aa_node_id), None)
    assert aa_node is not None, "AA Node not created"

    # Look for an edge where source == target == aa_node_id
    from models import EdgeData

    self_loop_edge = next(
        (
            e
            for e in elements
            if isinstance(e.data, EdgeData)
            and e.data.source == aa_node_id
            and e.data.target == aa_node_id
        ),
        None,
    )

    assert self_loop_edge is not None, "Self-loop edge for repeat-tier not found"
    assert (
        self_loop_edge.data.label == "Press 1"
    ), f"Expected label 'Press 1', got '{self_loop_edge.data.label}'"
