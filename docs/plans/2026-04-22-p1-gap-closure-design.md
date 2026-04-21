# P1 Gap Closure Design

## Scope

Close the remaining P1 gaps found during the PRD/SPEC/TRD audit.

## Design

S05 preview keeps the existing modal and validation flow, but adds row-level selection for valid rows. Error rows remain visible and disabled. The modal exposes two actions: save selected valid rows and save all valid rows. Clipboard preview keeps the editable TSV textarea, so users can correct errors and re-run preview before saving all rows.

API compatibility is implemented as aliases over the existing behavior. `POST /api/tasks/bulk` accepts a list of task payloads and creates them through the same validation and permission path as single task creation. Deadline admin compatibility adds `GET /api/admin/deadline` and `POST /api/admin/deadline` alongside the existing `/api/admin/settings/deadline`. Export accepts `approval_status` as an alias for the current `status` filter.

## Testing

Add backend tests for the compatibility API paths and frontend tests for row selection/rendering in preview UI. Run targeted tests first, then full backend and frontend suites.
