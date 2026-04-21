from enum import StrEnum


class Role(StrEnum):
    admin = "ADMIN"
    inputter = "INPUTTER"
    approver = "APPROVER"


class OrgType(StrEnum):
    normal = "NORMAL"
    team_direct = "TEAM_DIRECT"
    div_direct = "DIV_DIRECT"


class EntryStatus(StrEnum):
    draft = "DRAFT"
    submitted = "SUBMITTED"
    approved = "APPROVED"
    rejected = "REJECTED"
