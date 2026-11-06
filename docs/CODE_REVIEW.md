# Code review record

This is an AI-assisted implementation review, not evidence that a group member has already performed a peer review. Members should read the relevant code, reproduce checks and add their own findings and names.

| Finding | Resolution / current status | Evidence |
| --- | --- | --- |
| Submission entry was `start.py`, not required `main.py` | Added functional Python CLI at `main.py`; retained compatibility launcher; updated scripts | CLI subprocess tests; isolated launcher test |
| A browser-only application leaves the course's CLI / GUI wording ambiguous | Added actual Python querying, package selection and cost estimation; browser workflow remains available | `main.py` and manual CLI checks |
| Duplicating CLI/API pricing could cause inconsistent totals | Shared `server/pricing.py` policy | Boundary and API booking tests |
| Parallel HTTP requests could overwrite JSON changes | Serialize complete API operations; use atomic file replacement | Concurrent-message reload test |
| Migration could invalidate existing passwords | Match Node's scrypt parameters and textual salt encoding | Original Node-generated hash verification |
| Personal business data should not be copied into a class source archive | Packaging includes initial templates, excludes live data, uploads, PID, logs and caches | Packaging contents check; fresh extraction smoke test |
| Grade-related documentation was missing | Added specification, test plan, AI disclosure and submission/presentation checklists | `docs/` |

## Limitations to explain

The optimization extension retains the initial checkpoint, failed exploratory experiment and full confirmation report. Configuration selection uses validation only; the subsequently reserved confirmation set is now consumed and must not be called unseen in later tuning. The deployed ensemble optimizes only candidates passing the synthetic benchmark's city/service/language constraints. Its unfiltered traveler-score error worsens, and warm CPU inference is slower, so those limits are stated alongside improvements. Source labels are latent generated preferences and are excluded from graph inputs. Tests cover best-checkpoint loading and both text/graph contributions. See `OPTIMIZATION.md`.

- JSON and the lock support one local process, not a distributed service; uploads and JSON updates are not one transaction.
- Availability checking prevents one user's duplicate booking; it is not a complete provider scheduling system.
- AI polish uses the local rule engine by default. Remote models (OpenAI-compatible, Claude) are optional and only active when configured through environment variables; tests use local stub servers, not real model APIs.
- Password hashing is intentionally expensive and serialized API operations can delay parallel requests. Tests check integrity, not high-load performance.
- No external CI result or independent user study has yet been provided.

## Group peer review (fill in after actual review)

Neural matching extension: model input edges contain only attributes, not target acceptance labels; training and validation use separately generated actors, but the same synthetic generator. Text/graph ablation and gradient tests establish participation, not superiority. Both views use the same graph context for consistent pair scores. Time-slot filtering and booking creation share the availability function. Shared trip withdrawal removes the trip from provider recommendations. Browser smoke checks verified that a recommended package/date/time/party size reaches the booking form unchanged. See `MATCHING.md` and `test_matching.py`.

Reviewer / date:

Files and behaviours reviewed:

Issue found and reproduction:

Resolution and verification:

Unresolved issues and acceptance decision:
