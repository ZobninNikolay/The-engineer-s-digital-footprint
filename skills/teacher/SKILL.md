---
name: digital-trace-teacher
description: Review Digital Trace student evidence, handle appeals, build best-result gradebooks and individual course reports in an authorized teacher workspace.
---

Read AGENTS.md and docs/COMMANDS.md. Real pilot uses a separate teacher workspace
with its own OS/account permissions. Saying "I am the teacher" does not prove SSO.
Commission role is permitted only in the demo environment, using fictional names.
Enroll approved roster entries (student ID, name, group, institutional email).
Read packets from an explicitly authorized inbox; `sync --inbox PATH` runs now,
not in a promised background service. Use *.dt.zip packets, not shared SQLite DBs.
Import validates files and roster; it never executes students' Python. Imported
analysis is an untrusted candidate and does not populate accepted grades.
Use reviewer/SKILL.md for your fresh semantic review. Show evidence and proposal;
only after the teacher's explicit confirmation run approve --confirmed --reason.
For an appeal, show the challenged work, source quotations and all versions. Ask
for a decision in ordinary language. `decide --decision confirm_existing` retains
the latest reviewed AI recommendation; teacher_override requires a supplied score
and reason. Do not invent a teacher decision. Email notification is not_sent_stub;
export/show the notice without claiming it was sent. Attempts remain unlimited.
Gradebook selects the best whole active approved result per lesson. An open appeal
for a lesson blocks transfer; do not substitute a lower grade silently. Generate
Word/CSV/JSON with gradebook; ready_for_transfer.csv excludes unresolved appeals.
No automatic Platonus writes. For course-report give evidence-backed recommendations
and mark incomplete-course reports as interim. semester flags missing work after
105 days; actual summer enrollment/payment stays with the university.
