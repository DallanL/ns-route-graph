import pytest
from unittest.mock import AsyncMock, MagicMock
from ns_client import NSClient
from graph_builder import GraphBuilder
from models import (
    NSPhoneNumber,
    NSAutoAttendantResponse,
    NSAutoAttendantOption,
    EdgeData,
)


@pytest.mark.asyncio
async def test_intro_greeting_structure():
    # Mock the NSClient
    mock_client = MagicMock(spec=NSClient)

    mock_client.get_users = AsyncMock(return_value=[])
    mock_client.get_domain_timeframes = AsyncMock(return_value=[])

    # DID points to the Intro Greeting (Announce_1003)
    mock_client.get_dids = AsyncMock(
        return_value=[
            NSPhoneNumber(
                phonenumber="5550001000",
                domain="test.domain.com",
                dest="101:Announce_1003",
                application="auto-attendant",
            )
        ]
    )

    # Mock AA response (Prompt_1001 containing Intro Greeting 1003)
    # The graph crawler fetches for "101:Announce_1003" and gets this.
    mock_client.get_auto_attendant_prompts = AsyncMock(
        side_effect=lambda domain, owner, prompt: NSAutoAttendantResponse(
            attendant_name="Main AA",
            user="101",
            starting_prompt="Prompt_1001",
            auto_attendant={
                "option-1": NSAutoAttendantOption(
                    description="Test",
                    destination_application="to-user",
                    destination_user="999",
                )
            },
            intro_greetings=[
                {
                    "time-frame": "Holidays",
                    "audio": {
                        "filename": "greeting-1003.wav",
                        "ordinal-order": 1003,
                        "file-script-text": "Holidays Greeting Script",
                    },
                }
            ],
        )
    )

    builder = GraphBuilder(mock_client, "test.domain.com")
    elements = await builder.build()

    # 1. Verify Intro Greeting Node
    greeting_node_id = "auto_attendant_101_Announce_1003"
    greeting_node = next((e for e in elements if e.data.id == greeting_node_id), None)

    assert greeting_node is not None, "Intro Greeting Node not found"
    assert "Intro Greeting: Holidays (1003)" in greeting_node.data.label

    # 2. Verify Parenting (Intro Greeting -> Main AA ID)
    # Main AA ID should be auto_attendant_101_Prompt_1001
    main_aa_id = "auto_attendant_101_Prompt_1001"
    assert (
        greeting_node.data.parent == main_aa_id
    ), f"Expected parent {main_aa_id}, got {greeting_node.data.parent}"

    # 3. Verify Edge: Greeting -> Main AA (The 'Next' step)
    next_edge = next(
        (
            e
            for e in elements
            if isinstance(e.data, EdgeData)
            and e.data.source == greeting_node_id
            and e.data.target == main_aa_id
        ),
        None,
    )

    assert next_edge is not None, "Edge from Greeting to Main AA not found"
    assert next_edge.data.label == "Next"

    # 4. Verify Main AA Node Exists
    main_aa_node = next((e for e in elements if e.data.id == main_aa_id), None)
    assert main_aa_node is not None, "Main AA Node not found"
    assert "Main AA" in main_aa_node.data.label

    # 5. Verify Main AA has children (options) but Greeting does NOT have options
    # Greeting should ONLY go to Main AA.
    greeting_edges = [
        e
        for e in elements
        if isinstance(e.data, EdgeData) and e.data.source == greeting_node_id
    ]
    assert (
        len(greeting_edges) == 1
    ), f"Greeting should have exactly 1 outgoing edge, found {len(greeting_edges)}"

    # Main AA should have edge to User 999 (Option 1)
    main_aa_edges = [
        e
        for e in elements
        if isinstance(e.data, EdgeData) and e.data.source == main_aa_id
    ]
    assert any(
        e.data.label == "Press 1" for e in main_aa_edges
    ), "Main AA should have 'Press 1' edge"
