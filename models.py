from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union, Dict, Any

# --- Cytoscape Elements ---


class NodeData(BaseModel):
    id: str
    label: str
    type: str  # ingress, user, auto_attendant, queue, voicemail, offnet, hangup, conference, device, other
    bg: Optional[str] = None
    link: Optional[str] = None
    parent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class EdgeData(BaseModel):
    id: Optional[str] = None
    source: str
    target: str
    label: Optional[str] = None
    link: Optional[str] = None
    timeframe: Optional[str] = None
    priority: Optional[int] = None
    time_range_data: Optional[List[Dict[str, Any]]] = None  # Raw timeframe logic


class CytoscapeElement(BaseModel):
    # This allows either a node or an edge structure
    data: Union[NodeData, EdgeData]


# --- NetSapiens API Models ---


class NSUser(BaseModel):
    user: str = Field(..., alias="user")
    domain: str
    name_first_name: Optional[str] = Field(None, alias="name-first-name")
    name_last_name: Optional[str] = Field(None, alias="name-last-name")
    email: Optional[str] = Field(None, alias="email-address")
    department: Optional[str] = Field(None, alias="department")
    site: Optional[str] = Field(None, alias="site")
    status_message: Optional[str] = Field(None, alias="status-message")
    model_config = ConfigDict(populate_by_name=True)


class NSPhoneNumber(BaseModel):
    phonenumber: str
    domain: str
    dest: Optional[str] = Field(None, alias="dial-rule-translation-destination-user")
    application: Optional[str] = Field(None, alias="dial-rule-application")
    model_config = ConfigDict(populate_by_name=True)


class NSTimeframe(BaseModel):
    frame: str = Field(..., alias="timeframe-name")
    domain: str
    model_config = ConfigDict(populate_by_name=True)


class NSForwardingLogic(BaseModel):
    enabled: str  # "yes" or "no"
    parameters: List[Union[str, int]] = []
    model_config = ConfigDict(populate_by_name=True)


class NSAnswerRule(BaseModel):
    domain: str
    user: str
    time_frame: str = Field(..., alias="time-frame")
    priority: int = Field(0, alias="ordinal-priority")
    time_range_data: Optional[List[Dict[str, Any]]] = Field(
        None, alias="time_range_data"
    )

    # Nested logic
    simultaneous_ring: Optional[NSForwardingLogic] = Field(
        None, alias="simultaneous-ring"
    )
    forward_always: Optional[NSForwardingLogic] = Field(None, alias="forward-always")
    forward_on_busy: Optional[NSForwardingLogic] = Field(None, alias="forward-on-busy")
    forward_no_answer: Optional[NSForwardingLogic] = Field(
        None, alias="forward-no-answer"
    )
    forward_when_unregistered: Optional[NSForwardingLogic] = Field(
        None, alias="forward-when-unregistered"
    )

    model_config = ConfigDict(populate_by_name=True)

    @property
    def rule(self) -> str:
        return self.time_frame


class NSAutoAttendantOption(BaseModel):

    description: Optional[str] = None

    destination_application: Optional[str] = Field(
        None, alias="destination-application"
    )

    destination_user: Optional[str] = Field(None, alias="destination-user")

    nested_aa: Optional[Dict[str, Any]] = Field(None, alias="auto-attendant")

    model_config = ConfigDict(populate_by_name=True)


class NSAutoAttendantResponse(BaseModel):

    attendant_name: Optional[str] = Field(None, alias="attendant-name")

    user: str

    starting_prompt: str = Field(..., alias="starting-prompt")

    # The 'auto-attendant' field contains dynamic keys like 'option-1', 'option-2'
    auto_attendant: Dict[str, Union[str, NSAutoAttendantOption]] = Field(
        ..., alias="auto-attendant"
    )

    intro_greetings: Optional[List[Dict[str, Any]]] = Field(
        None, alias="intro-greetings"
    )

    model_config = ConfigDict(populate_by_name=True)


class NSCallQueueAgent(BaseModel):
    user: str = Field(..., alias="callqueue-agent-id")
    order: Optional[int] = Field(None, alias="callqueue-agent-dispatch-order-ordinal")
    full_name: Optional[str] = Field(None, alias="name-full-name")
    model_config = ConfigDict(populate_by_name=True)
