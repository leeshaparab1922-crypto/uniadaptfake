# ADR-0007: Section timetable slot types are CLASS and LAB only

- **Status:** Accepted
- **Date:** 2026-09-27
- **Affects:** Phase 1 (timetable), Phase 7 (planner availability)
- **SRS refs:** Section 3 constraints, FR-ADM-007, Section 31.1 SectionTimetableSlot ("class/lab")

## Decision
`section_timetable_slots.type` allows exactly `CLASS` and `LAB`, because the SRS
names only those two.

## Consequences
Adding a type later (for example `TUTORIAL`) is an ordinary migration under
ADR-0009 and needs a new ADR stating its basis in the SRS.
