"""Type aliases for aggregate and entity identifiers across bounded contexts."""

from typing import NewType

AccountId = NewType("AccountId", str)
StakeholderId = NewType("StakeholderId", str)
SequenceId = NewType("SequenceId", str)
MessageId = NewType("MessageId", str)
DeckId = NewType("DeckId", str)
CRMRecordId = NewType("CRMRecordId", str)
