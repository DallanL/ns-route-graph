import pytest
from unittest.mock import AsyncMock, MagicMock
from ns_client import NSClient
from graph_builder import GraphBuilder
from models import NSPhoneNumber, NSAutoAttendantResponse


@pytest.mark.asyncio
async def test_conference_detection():
    mock_client = MagicMock(spec=NSClient)

    # Mock data
    mock_client.get_users = AsyncMock(return_value=[])
    mock_client.get_domain_timeframes = AsyncMock(return_value=[])

    # DID points to the AA
    mock_client.get_dids = AsyncMock(
        return_value=[
            NSPhoneNumber(
                phonenumber="5550001000",
                domain="test.domain.com",
                dest="001:Prompt_Conf",
            )
        ]
    )

    # AA with Conference Option
    aa_data = {
        "attendant-name": "Conference AA",
        "user": "001",
        "starting-prompt": "Prompt_Conf",
        "time-frame": "*",
        "auto-attendant": {
            "option-4": {
                "description": "AA designer: press 4 for conference test (3333)",
                "destination-application": "to-single-device",
                "destination-user": "3333.1234567890.com",
            }
        },
    }

    ns_aa_resp = NSAutoAttendantResponse.model_validate(aa_data)

    mock_client.get_auto_attendant_prompts = AsyncMock(return_value=ns_aa_resp)

    # Build
    builder = GraphBuilder(mock_client, "test.domain.com")
    elements = await builder.build()

    # Helper
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

    def get_edges(source_id):
        return [
            e.data
            for e in elements
            if hasattr(e.data, "source") and e.data.source == source_id
        ]

    main_aa_id = "auto_attendant_001_Prompt_Conf"

    # Find edge for option 4
    edges = get_edges(main_aa_id)
    opt4 = next((e for e in edges if e.label == "Press 4"), None)
    assert opt4 is not None, "Press 4 edge missing"

    # Target should be the conference ID "3333"
    target_id = opt4.target
    # ID construction for conference: "conference_3333"
    assert target_id == "conference_3333"

    # Check Node
    conf_node = get_node(target_id)
    assert conf_node is not None
    assert conf_node.type == "conference"
    assert conf_node.label == "Conference Bridge: 3333"
    assert conf_node.bg == "#EE82EE"
    assert conf_node.link == "/portal/conferences"
