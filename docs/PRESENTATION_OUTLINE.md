# Presentation preparation

This is an outline, not a finished PowerPoint or recorded video. Replace all roles with actual contributors. Required PPT filename: `groupN_presentation.pptx`, where N is the real group number.

## 15-minute submitted video

| Time | Content | Demonstration / evidence |
| --- | --- | --- |
| 0:00–2:00 | Problem and intended users | Visitor uncertainty, provider discovery and transparent package costs; avoid invented survey numbers |
| 2:00–4:00 | Scope and user flow | CLI query → price estimate → browser booking → private chat |
| 4:00–7:00 | Live core workflow | Start `python main.py`; query city; estimate 4 and 5 people; show invalid input |
| 7:00–10:00 | Live authenticated workflow | Traveller booking, duplicate rejection, provider reply, unread update and cancellation |
| 10:00–13:00 | Python design and quality | Modules, Handler class, file persistence, shared formula, auth and ownership; selected real tests and actual CI evidence if available |
| 13:00–15:00 | Evaluation and conclusion | Real usability feedback, limitations, AI collaboration, contributions, lessons and next steps |

Prepare demo state in a separate copy; never reset important user data for recording. Run through the exact scenario before recording. Seed greetings are simulated; identify them honestly. Explain any recording cuts rather than implying an uninterrupted live run.

## Classroom technical briefing: at most 5 slides / 5 minutes

1. **Problem and working application** (45 sec): two user roles, practical use, scope and distinct design choices.
2. **Python architecture** (60 sec): main.py → CLI / HTTP Handler → pricing, authentication, JSON storage; distinguish browser JavaScript from Python business logic.
3. **Input, calculation and modularity** (60 sec): package selection, formula `price + max(0, people - 4) × 60`, invalid inputs and class/function boundaries.
4. **Specification, tests and review** (75 sec): trace one requirement through code and test; demonstrate price boundary and denied cross-user access; explain concurrency protection.
5. **Results, AI use and limitations** (60 sec): actual test result, actual human contribution, AI assistance, JSON limitations and planned improvements.

## Questions to rehearse

- Why Python standard library rather than a framework? What does this simplify, and what becomes harder?
- How is CLI pricing kept consistent with the booking API?
- Why is the storage lock necessary even when file replacement is atomic?
- How do you stop a user reading another person's conversation or cancelling their booking?
- Which tests detect incorrect behaviour rather than merely repeating the implementation?
- Which parts did AI generate, and what did each member inspect/change/test?
- What is genuinely original in the group's work? Where did the original prototype and photographs come from?

Every member must participate in the required peer assessment. Check Moodle for the actual submission deadline and video upload method.
