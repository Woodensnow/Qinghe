# Testing and evaluation

## User stories: functional regression suite

The suite `tests/test_user_journeys.py` follows complete traveller/provider workflows through real HTTP requests. It adds no production validation, fallback logic or business features. Assertions check the results users rely on, such as the actual quotation, saved itinerary, counterpart identity and message contents, rather than only successful response codes.

Run just these stories:

```bash
python -m unittest discover -s tests -p test_user_journeys.py -v
```

| Story | Behaviour checked |
| --- | --- |
| First weekend in Suzhou | Combined search → details → booking → real provider reply → saved itinerary and emoji note |
| Bilingual food walk on a budget | City, language, service and price filters work together; relaxing the filters gives the expected alternatives in both price orders |
| Coffee in another language | Uppercase English keyword finds a mixed Chinese/English introduction |
| A friend joins the group | Three packages × 4 / 5 / 8 travellers, with nine explicit expected totals |
| Rain changes the plan | Cancel and rebook the same slot with another package; retain the cancelled order |
| Guide takes a break | Pause hides discovery, preserves existing bookings and chat, resume accepts a new traveller |
| Return to the same conversation | Reopening reuses the conversation and does not duplicate the preset greeting |
| Two travellers, one guide | Family and photography plans stay in their own threads; reading one leaves the other unread |
| Latest reply rises to the top | Latest-message preview, ordering, aggregate unread count and per-conversation reading semantics |
| New avatar and nickname | Existing services and both conversation views reflect current identity; avatar removal also propagates |
| Curated photo wall | Remove the middle photo, append a new one, and retain order and cover after storage reload |
| Preview polish, then accept | Polishing preserves supplied facts, leaves saved bio unchanged, and becomes persistent only on explicit save |
| Publish a first local route | Upload custom cover, polish guide introduction, publish, and see the exact assets/text in public details and own services |
| Two trip diaries | After logout, JSON reload and login, each traveller sees their own itinerary, notes and conversation |

Each story starts from independent temporary demo data and registers its own actors. Shared `ApiFixture` only provides the local HTTP service, isolated files and request helper; it has no tests of its own, so reusing it does not rerun inherited test methods. The only mocked behaviour is the clock in the inbox-ordering story, to establish a deterministic message order without sleeps. Storage reload explicitly clears the cache and reads the JSON file; it is not described as a full process restart.

These are API-level user-feature tests, not browser click automation: visual layout, image rendering, client-side favourites, modal behaviour and navigation still require browser checks. All new requests are ordinary supported interactions; the pre-existing input/security checks remain in the original test suite.

## Automated checks

Run from the project root with Python 3.10+:

```bash
python -m unittest discover -s tests -v
```

Tests require permission to connect to loopback TCP ports. They use temporary data beneath `tmp/`, ephemeral HTTP ports and isolated upload folders. They do not reset or write the project's actual `server/data.json` or current uploaded images.

| Test group | Purpose |
| --- | --- |
| CLI boundaries and entry point | Valid pricing boundaries; invalid counts; invalid choices; EOF; argument conflicts |
| Authentication / persistence | Original Node scrypt compatibility; login/logout; duplicate registration; profile updates; reload |
| Booking | Filter by city; price calculation; duplicate protection; cancellation ownership; invalid calendar date |
| Chat / provider | Publish and pause a guide; block self-chat; send both ways; unread clearing; deny outsiders |
| Images / polish | Upload/delete each profile image type; avatar propagation; invalid file signatures; bounded polish output |
| Static / metadata | SPA fallback, JavaScript delivery, traversal rejection, missing asset, HEAD, security headers |
| Concurrency | Sixteen concurrent chat sends are all present after storage reload |
| AI polish providers | Config parsing and key rules; registering a fake provider; output cleaning and limits; OpenAI-compatible and Anthropic requests against local stub servers; timeouts, bad responses and fallback; a slow model does not block other requests (`tests/test_polish_providers.py`) |
| Launcher / reset | Fresh project copy initializes, resets only its own uploads, serves health and refuses reset while running |

The file `.github/workflows/tests.yml` configures GitHub Actions for Python 3.10 / 3.12 on Linux / Windows. Configuration is not a successful CI run; attach actual job results after pushing to a group-owned repository.

## Manual usability acceptance

Record real results instead of marking these passed without trying them:

| Scenario | Steps | Expected result | Actual result / tester |
| --- | --- | --- | --- |
| First use | Start `python main.py`, query a city, enter an invalid option | Clear guidance and return to menu | To be recorded |
| Estimate | Choose a guide/package; quote 4 then 5 people; try text instead of a number | Fifth person adds CNY 60; invalid input gives feedback | To be recorded |
| New traveller | Register, search, open details, create a future booking | Consistent form feedback and order record | To be recorded |
| Provider | Publish, pause, resume, open traveller chat | Correct visibility and participant role | To be recorded |
| Mobile | Try a narrow viewport, chat and booking controls | Readable layout and usable controls | To be recorded |
| Upload | Try a real JPG, 15+ MB original, a non-image file | Compression/validation and meaningful errors | To be recorded |
| Offline / failure | Stop server while a page is open and submit an action | Clear network error | To be recorded |
| Fresh submission | Extract ZIP into an empty folder; start CLI and tests | No dependency on old runtime/data | To be recorded |

For responsiveness, use the same device/browser, record elapsed time for search, booking and photo upload, and distinguish chat polling latency from server processing. No performance measurements or user-study results are invented in this repository.

## Evidence record

Optimization verified on 2026-11-05, Windows, Python 3.12.14 / PyTorch 2.15.0+cpu: **43 tests passed**, no skips, in 26.100 seconds, with the selected three-member v3 ensemble loaded. Six additional evaluation tests cover actor/template separation, teacher-label independence from phrase parsing, NDCG ordering, both directional and mutual metrics, observed compatibility inputs without hidden labels, and saving the actual best validation checkpoint. The headless Edge workflow check also passed against the upgraded model. The separate synthetic confirmation and in-process timing measurements are documented in `OPTIMIZATION.md`; no real-user effect is claimed.

Transformer/heterogeneous-graph expansion verified on 2026-11-05, Windows, project Python 3.12.14 / PyTorch 2.15.0+cpu: **37 tests passed**, no skips, in 25.012 seconds. The 11 added matching tests include trainability, text/graph contribution checks, typed relations, reciprocal scores, scheduling and both user journeys. A separate headless Edge browser smoke check passed provider preference editing, traveller matching, a five-person CNY 260 quote, 390px mobile layout without horizontal overflow, booking prefill and provider-initiated contact, with no page errors. Desktop/mobile result cards were also visually inspected. These checks do not establish real-world recommendation quality; see `MATCHING.md` for the synthetic-data evaluation.

User-feature expansion verified on 2026-11-05 (Asia/Shanghai), Windows, Python 3.12.14: the **14 new user stories passed** in 12.285 seconds; the complete suite then ran **26 tests, all passed**, in 18.261 seconds. Nine pricing examples run as subtests within one story, not nine separately counted test methods. Full local output is in `tmp/test-results.txt` (temporary evidence, excluded from the submission ZIP). No production code was changed in this expansion.

Verified in this workspace on 2026-11-05 (Asia/Shanghai), Windows, Python 3.12.14: `python -X utf8 -m unittest discover -s tests -v` ran **12 tests, all passed**, in approximately 6.08 seconds. This includes an archive-content check and a CLI query after fresh extraction. Local loopback access required execution permission. No GitHub Actions run, Linux run, Python 3.10 run or manual usability study is claimed by this result.

For each actual run record date, operating system, `python --version`, command, total tests, failures, and follow-up fixes. Preserve screenshots or terminal output in your own submission evidence. Locally verified results appear in the accompanying chat; rerun on the group's target machine before submitting.
