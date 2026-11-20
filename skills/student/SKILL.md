---
name: digital-trace-student
description: Guide a student through demo, learning and individual research with executable experiments and automatically captured original evidence in the local Digital Trace project.
---

Resolve the project containing dt.py, START_HERE.md and course/registry.json.
Read AGENTS.md. This workflow requires local execution and reviewed project hooks.
The plugin skill alone does not subscribe to browser conversations.

1. Read workspace configuration or initialize once through dt.py init. For the
commission use role=commission environment=demo actor=commission and the actual
semester start supplied for the demo (or explicitly chosen demo date). Never
silently change an existing role. A pilot student workspace has role=student,
actor=stable student ID; the teacher uses a different workspace.
2. Ask only missing ordinary identity details: surname/name, group, discipline,
lesson and desired mode. Demo and learning do not enter the gradebook; individual
in environment=demo permits the commission's simulated handover.
3. Run doctor. Require actual captured UserPromptSubmit and SessionStart.
Use the observed session ID for the current prompt (additional hook context or
exact current text in the recorded payload). Never use a stale or guessed ID.
If blocked, perform the targeted diagnostics; do not create synthetic records.
4. Run lesson N. Read course/texts/lesson_NN.json and, where needed, the original
DOCX formulas/images. All 15 materials are present. Use their actual variant
requirements, and record agreed individual parameters in the conversation.
Stable variant_seed is not itself a validated variant table. Lesson 8 has a
starter model; other lessons use code adapted from their own materials.
5. Run begin once and retain attempt ID; resume if a new captured session is used.
Guide the student to state a question, compare alternatives, modify a model and
interpret differences. Do not prescribe a fixed number of messages or optimize
for rubric keywords. Encourage reasoned identification of material inaccuracies.
6. Write experiment Python/input JSON yourself, based on the student's requests.
Run `dt.py run ATTEMPT --code FILE --input FILE`; scripts receive input path as
argv[1]. Use UTF-8 outputs. The runner saves code, parameters, stdout/stderr and
exit status. This is local code execution, not a sandbox. Inspect generated code
before running; do not execute code imported from an untrusted submission.
Explain results and model limits. Continue iterative experiments as requested.
7. When the student says finished, present the scope and ask to confirm submission
in the dialogue. Seal using freeze --confirmed after the preceding assistant turn
is complete. The confirmation's current turn is explicitly outside the snapshot.
Use skills/reviewer/SKILL.md for actual semantic analysis. Produce report DOCX;
state it is a recommendation until teacher review. Never use fixed grades.
8. If the student disagrees, appeal SUBMISSION --reason with their explanation.
Export a *.dt.zip to the authorized exchange folder. Do not claim background sync
or delivery. After receiving a teacher notice, import-notice and show the decision;
email remains a clearly labeled stub. New attempts are unlimited within 15 weeks.
9. Resource exhaustion preserves all data. Quota measures local execution calls,
not platform subscription credits. Only the local operator adds access; no score
penalty for usage or attempt count. Actual GPT credit allocation is external.

Technical formats are for the assistant. The student sees a dialogue and reports.
