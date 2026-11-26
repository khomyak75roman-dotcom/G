# VIDEO COMBINE AI — Security Architecture

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Policy | Keyless by default; no credential in code, docs, CI, logs, or API responses |

---

## 1. Threat model

| Threat | Mitigation |
|---|---|
| Accidental key commit | `.env` gitignored; only `.env.example` with placeholders tracked; CI secret scan + `git diff --check` |
| Key leakage via logs/API | Central redaction of key/token/proxy patterns in `studio/api/errors.py` and event bridge |
| Paid call without consent | `budget_policy: keyless`; Tier 4 disabled by default; explicit opt-in + budget cap |
| Malicious media filename/path | Path confinement to `projects/<id>/`; MIME/size validation; no shell interpolation |
| Prompt injection via skill/source text | Skill text treated as data; no `eval`/shell; schemas validated; provenance untrusted |
| SSRF via source URL | Allowlisted source domains; no arbitrary internal addresses; timeouts |
| Supply-chain risk | Minimal dependencies, pinned via requirements; reference-only repos never imported |
| Metadata deception / rights evasion | Rights gate + accurate metadata rules (see copyright doc) |

## 2. Credential policy

1. **No manually entered API keys are required for the core path.** Tier 1 and Tier 2 work without any credential.
2. No key value is hardcoded, printed, echoed in errors, written to artifacts, or stored in the DB.
3. Only a local, gitignored `.env` may hold opt-in credentials on a user's own machine; the repository tracks only `.env.example` placeholders.
4. OAuth/browser sessions (Tier 3) are held by the user's browser/session store, never by this repository.
5. If a credential is ever exposed, revoke it first, then rotate — history rewriting is not a substitute for revocation.

## 3. Network policy

- Allowed: standard `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` environment variables, reported with credentials redacted via `--network-check`.
- Forbidden: VPN clients, DPI bypass, proxy pools, Telegram transit, or any mechanism to evade network restrictions or platform controls.
- Default sources are open archives (Wikimedia, NASA, Archive.org) with a User-Agent header. `loc.gov` currently returns Cloudflare 403 and is not a default.
- All network operations have timeouts, retries with backoff, and a documented offline fallback.
- The `ci` profile disables sockets in tests via a network guard so no test can reach the internet.

## 4. Application controls

| Area | Control |
|---|---|
| Subprocesses | `ffmpeg`/`ffprobe` invoked with argument lists; no `shell=True`; no user string in a command template |
| Uploads | MIME allowlist, size cap, extension normalization, storage under project workspace only |
| Schemas | All envelopes and artifacts validated against JSON Schema before persistence |
| Gates | G1/G2/G3/G4/G5 are first-class DB states; a gated stage cannot be marked complete without approval |
| Budget | Every Tier 4 call declares max cost; exceeding the cap aborts and emits a redacted error |
| Events | `audit_log` records decisions and gate transitions; secret patterns are scrubbed before SSE |
| Skills | Versioned instruction files parsed as text; no executable directives; injection strings are ignored |

## 5. Mistral browser authentication (development only)

- Preferred **where supported for development**, never a production dependency.
- Requires explicit user consent and an interactive browser session; no key is typed into the app.
- Not available in restricted/sandbox environments; features depending on it must degrade to Tier 1/2 paths.
- Not part of Phase 1 implementation; separate approval required before any integration.

## 6. CI and review checklist

- `make lint`, `make test`, frontend tests green before merge.
- Secret scan on every PR; no diff line containing a high-entropy token.
- `git diff --check` clean.
- No new provider is enabled by default; a new Tier 4 adapter requires a documented opt-in and budget entry.
- All new endpoints have authz assumptions documented and redaction tests.

## 7. Known limitations

- Repository history contains references to previously leaked credentials from the upstream import; the owner chose revocation instead of history rewriting. Current tree shows no live key values.
- Cloudflare blocks some endpoints; cloud key live validation could not be performed in this environment.
- No hardware security module or secret manager is assumed; production deployment should add one.
