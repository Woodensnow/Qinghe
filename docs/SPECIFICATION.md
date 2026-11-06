# 青禾 / Qinghe — Software Specification

## 1. Problem and scope

Visitors need an understandable way to find local companions, compare packages, estimate costs and coordinate a visit. Local service providers need a simple way to publish or pause a service and answer enquiries. This prototype demonstrates those workflows locally, without real payments or identity verification.

The required Python entry is `main.py`. The CLI can query guides, estimate package costs, launch the browser service and run tests. The browser interface supports authenticated transactions. This document describes implemented behaviour, not future promises.

## 2. Functional requirements and acceptance criteria

| ID | Requirement | Acceptance criterion | Automated evidence |
| --- | --- | --- | --- |
| FR-01 | Clear CLI navigation | Invalid menu choices show a message; EOF exits successfully | `CliTests.test_invalid_menu_and_eof` |
| FR-02 | Guide discovery | Only published services are shown; city, service, language, keyword, price and sort parameters filter the API results | User stories cover combined city/service/language/price/keyword filters, both price orders and English keyword matching; other sort modes still need checks |
| FR-03 | Price estimation | For 1–4 people use the package price; for 5–8 add CNY 60 per person above four; reject other counts | `CliTests.test_price_boundaries`; API price check |
| FR-04 | Authentication | Register, reject duplicate emails, log in, fetch current user and log out; do not expose password hashes | `ApiTests.test_auth_persistence_and_legacy_scrypt` |
| FR-05 | Booking | Require login, valid package, real calendar date within 180 days, permitted time and 1–8 people; prevent same-user duplicate active bookings | `ApiTests.test_booking_filters_price_and_cancellation` covers pricing, duplicate and invalid date |
| FR-06 | Booking cancellation | Only its owner can cancel a pending or confirmed booking | Booking test includes another user's denied attempt |
| FR-07 | Service publication | Validate fields; owner may pause / resume; paused services are hidden from other users | `ApiTests.test_guide_and_two_way_chat_permissions` |
| FR-08 | Private conversations | Only participants may view/send messages; expose role and unread counts; reading clears that participant's unread count | Same two-way chat test |
| FR-09 | Profile and photos | Update profile; accept JPEG/PNG/WebP with size and signature checks; avatar changes propagate to owned services | Auth and photo tests |
| FR-10 | Text polish | Require login and scene-specific text limits; use the local engine (`engine: local`) unless a model provider is configured; report `provider` / `model`, fall back to local on provider failure | `ApiTests.test_photo_upload_validation_and_polish`, `tests/test_polish_providers.py` |
| FR-11 | Durable storage | Preserve data after reload; serialize writes to avoid lost concurrent messages | Auth reload test; `test_concurrent_messages_are_saved` |
| FR-12 | Clean startup and reset | Serve via Python; explicit reset regenerates demo data and removes uploads; refuse reset while PID file exists | `test_launcher_and_reset_in_isolated_project` |

## 3. Architecture and data

`main.py` coordinates the CLI. `server/server.py` uses `Handler` and `ThreadingHTTPServer` for HTTP requests. `pricing.py` is the single pricing rule shared by CLI and API. `auth_utils.py` handles scrypt and random credentials. `store.py` owns JSON loading, initialization and atomic replacement. `ai_polish.py` handles local text transformation; `polish_providers.py` defines the provider interface, configuration and optional remote model providers. `public/js/` implements browser pages and calls the Python API.

`catalog.json` contains allowed cities, services, languages and covers. `seed-data.json` contains demo templates; initialization generates a fresh password salt and relative booking/chat dates. `data.json` stores users, sessions, guides, bookings, conversations and messages. Uploaded images are separate files under `public/uploads`.

Key relationships: guide.ownerId → user.id; booking.userId → user.id; booking.guideId → guide.id; conversation.travelerId and guideOwnerId → user.id; message.conversationId → conversation.id. Preset guides have no real owner, so a greeting is generated for demonstration.

## 4. Non-functional requirements

- Python 3.10+ standard library; no external service, Node runtime or package installation needed.
- Run one server process per data directory. An in-process lock covers each API transaction; atomic replacement protects file updates. This does not provide multi-process database transactions.
- Local requests return meaningful status codes and Chinese error messages. Body size is limited to 8 MB; image content to 5 MB; read timeout is 30 seconds.
- Passwords use salted scrypt. Tokens are random and expire after seven days. Private endpoints check identity and conversation/order ownership. Public responses omit password material and guide owner IDs.
- Static paths must stay under `public`; content security and MIME headers are sent. Responsive browser layout is retained.
- No measured response-time SLA is claimed. Manual evaluation should record device, scenario, timings and observed delays. Chat currently polls every four seconds.

## 5. Out of scope and evaluation limits

Real payments/refunds, identity checks, remote deployment and production moderation are not implemented. The local polish feature is rule-based. Existing sample reviews are demonstration data. Originality must be supported by the group's own design reasoning and documented provenance; software tests alone cannot establish it.

## 6. Bilateral neural recommendation extension

`/matching` collects a traveller's explicit shared trip and a provider's explicit preferences. The optional PyTorch model uses an ensemble of three small models, each with a one-layer Transformer, one relation-specific heterogeneous GNN layer, explicit compatibility features and independent directional heads; averaged scores use a harmonic mean. Candidate constraints include date/time overlap and whole-group budget. Both views score against the same graph context. See `MATCHING.md` for the complete model, API/data fields, training provenance, metrics and limitations. This is a synthetic-data teaching model and is distinct from the rule-based text-polish feature.
