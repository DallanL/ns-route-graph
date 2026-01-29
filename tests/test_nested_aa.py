from unittest.mock import AsyncMock, MagicMock

import pytest

from graph_builder import GraphBuilder
from models import NSAutoAttendantResponse, NSPhoneNumber, NSUser
from ns_client import NSClient


@pytest.mark.asyncio
async def test_nested_aa_structure():
    mock_client = MagicMock(spec=NSClient)

    # Mock data
    mock_client.get_users = AsyncMock(
        return_value=[
            NSUser(user="101", domain="test.domain.com"),
            NSUser(user="103", domain="test.domain.com"),
        ]
    )
    mock_client.get_domain_timeframes = AsyncMock(return_value=[])

    # DID points to the AA
    did_dest = "001:Prompt_1001"
    mock_client.get_dids = AsyncMock(
        return_value=[
            NSPhoneNumber(
                phonenumber="5550001000", domain="test.domain.com", dest=did_dest
            )
        ]
    )

    # The complex AA response
    aa_data = {
        "attendant-name": "after hours auto attendant",
        "user": "001",
        "starting-prompt": "Prompt_1001",
        "time-frame": "*",
        "audio": [],
        "auto-attendant": {
            "3-digit-dial-by-extension": "yes",
            "4-digit-dial-by-extension": "yes",
            "5-digit-dial-by-extension": "no",
            "no-key-press": "repeat",
            "unassigned-key-press": "repeat",
            "option-1": {
                "description": "AA designer: press 1 for user 101",
                "destination-application": "to-user",
                "destination-user": "101",
            },
            "option-2": {
                "description": "AA designer: press 2 for Company Directory",
                "destination-application": "sip:start@directory",
                "destination-user": "1003",
            },
            "option-3": {
                "description": "AA designer: press 3 for tier More options",
                "auto-attendant": {
                    "option-1": {
                        "description": "AA designer: press 1 for user 103",
                        "destination-application": "to-user",
                        "destination-user": "103",
                    }
                },
                "audio": [],
            },
        },
    }

    ns_aa_resp = NSAutoAttendantResponse.model_validate(aa_data)

    # Mock get_auto_attendant_prompts to return our object ONLY for the main prompt
    # For the nested prompt (synthetic), it should hit the cache and NOT call this.
    mock_client.get_auto_attendant_prompts = AsyncMock(
        side_effect=lambda d, u, p: ns_aa_resp if p == "Prompt_1001" else None
    )

    # Builders
    builder = GraphBuilder(mock_client, "test.domain.com")
    elements = await builder.build()

    # Helper to find node by ID
    def get_node(id):
        return next(
            (
                e.data
                for e in elements
                if hasattr(e.data, "id")
                and e.data.id == id
                and not hasattr(e.data, "source")
            ),
            None,
        )

    # Helper to find edges from source
    def get_edges(source_id):
        return [
            e.data
            for e in elements
            if hasattr(e.data, "source") and e.data.source == source_id
        ]

    # 1. Main AA Node
    # ID is constructed as: auto_attendant_{owner}_{prompt}
    # owner=001, prompt=Prompt_1001 -> auto_attendant_001_Prompt_1001
    main_aa_id = "auto_attendant_001_Prompt_1001"
    main_node = get_node(main_aa_id)
    assert main_node is not None, "Main AA node not found"

    # 2. Edges from Main AA
    edges = get_edges(main_aa_id)
    print(f"Edges from Main AA: {[e.label for e in edges]}")

    # Check for "no-key-press" edge (should loop back to self)
    no_key = next((e for e in edges if e.label == "No Input"), None)
    assert no_key is not None, "No Input edge missing"
    assert no_key.target == main_aa_id, "No Input should loop back"

    # Check for Option 1 -> User 101
    opt1 = next((e for e in edges if e.label == "Press 1"), None)
    assert opt1 is not None, "Press 1 edge missing"
    assert opt1.target == "user_101"

    # Check for Option 2 -> Company Directory
    opt2 = next((e for e in edges if e.label == "Press 2"), None)
    assert opt2 is not None, "Press 2 edge missing"
    dir_node_id = opt2.target
    dir_node = get_node(dir_node_id)
    assert dir_node.type == "directory"
    assert dir_node.label == "Directory"
    assert dir_node.bg == "#DA70D6"

    # Check for Option 3 -> Nested AA
    opt3 = next((e for e in edges if e.label == "Press 3"), None)
    assert opt3 is not None, "Press 3 edge missing"
    nested_aa_id = opt3.target
    print(f"Nested AA ID: {nested_aa_id}")
    assert "nested_option-3" in nested_aa_id
    nested_node = get_node(nested_aa_id)
    assert nested_node.type == "auto_attendant"
    assert "Nested Press 3" in nested_node.label

    # NEW: Verify Parent Relationship
    # The nested AA should be a child of the Main AA
    assert (
        nested_node.parent == main_aa_id
    ), f"Expected parent {main_aa_id}, got {nested_node.parent}"

    # 3. Check Nested AA Expansion
    nested_edges = get_edges(nested_aa_id)
    print(f"Edges from Nested AA: {[e.label for e in nested_edges]}")
    nested_opt1 = next((e for e in nested_edges if e.label == "Press 1"), None)
    assert nested_opt1 is not None, "Nested Press 1 edge missing"
    assert nested_opt1.target == "user_103"
