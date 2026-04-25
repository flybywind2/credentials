from enum import Enum


class StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Role(StringEnum):
    admin = "ADMIN"
    inputter = "INPUTTER"
    approver = "APPROVER"


class OrgType(StringEnum):
    normal = "NORMAL"
    team_direct = "TEAM_DIRECT"
    div_direct = "DIV_DIRECT"


class EntryStatus(StringEnum):
    draft = "DRAFT"
    submitted = "SUBMITTED"
    approved = "APPROVED"
    rejected = "REJECTED"
