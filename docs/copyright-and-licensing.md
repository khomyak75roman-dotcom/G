# VIDEO COMBINE AI — Copyright and Licensing Policy

| Field | Value |
|---|---|
| Status | **DRAFT — awaiting approval** |
| Version | 1.0.0 |
| Rule | Authorized sources only; accurate attribution; no metadata deception |

---

## 1. Core principles

1. The platform respects YouTube's Terms of Service, copyright law, and platform policies.
2. Only user-owned uploads, explicitly authorized sources, or properly licensed media may be processed.
3. Metadata must describe the **actual new editorial content** accurately and name source material where required.
4. No metadata modification is used to conceal the original source, mislead viewers, or evade Content ID or any copyright detection system.
5. Transformation (new commentary, narration, structure) does not automatically create a license or a fair-use claim; authorization is still recorded.

## 2. Rights gate (G3)

Every external source must have a `RightsRecord` before analysis or extraction:

```json
{
  "source_ref": "url-or-file",
  "claimed_owner": "name or channel",
  "license": "CC-BY-4.0 | public-domain | user-owned | written-permission | unknown",
  "permission_proof": "reference to user-provided proof",
  "user_uploaded": true,
  "intended_use": "transformative-clip | full-reuse | reference",
  "verified": true,
  "attribution_text": "Source: ..., License: ..., Link: ...",
  "restrictions": []
}
```

`verified=false` blocks the Analysis and Clip agents. Missing proof is never inferred from a URL.

## 3. Source categories

| Category | Allowed use | Required action |
|---|---|---|
| User-owned upload | Full pipeline | User declares ownership; record in rights gate |
| Written permission | Full pipeline within scope | Store permission reference; respect scope/expiry |
| CC BY / CC BY-SA | Use with attribution and share-alike where applicable | Include author, title, license, link; check derivative terms |
| CC0 / public domain (NASA, etc.) | Broad use | Record source; verify no third-party rights in image |
| Archive.org items | Varies by item | Check item license field; do not assume public domain |
| Stock with API terms (Pexels, Pixabay) | Per provider license | Attribute where required; no key added by default |
| Third-party YouTube video without permission | **Reference only, no extraction** | Do not download, analyze, or republish; may discuss at a high level |

## 4. Attribution template

```
Source: <author / channel>, "<title>", <URL>.
License: <license or permission>. Changes: <new narration, commentary, cuts, reframing>.
```

Attribution is stored in the provenance ledger, embedded in `seo.json`, and copied into the final description. QC checks its presence.

## 5. Prohibited metadata practices

- Removing, altering, or obfuscating source identifiers to hide origin.
- Mislabeling re-uploaded material as wholly original.
- Adding tags/keywords to misleadingly associate content with unrelated owners or trends.
- Changing copyright/ownership fields to claim someone else's work.
- Any technique intended to evade Content ID, fingerprinting, or takedown systems.
- Chapters, titles, or descriptions that contradict the actual content.

## 6. Content ID and claims

- A claim is handled transparently: surface it to the user with the rights record and options (license, edit, dispute with evidence, or remove).
- The system never automatically contests a claim on the user's behalf and never alters metadata to bypass detection.

## 7. Code licensing

- The existing repository `LICENSE` is **unchanged**; no new project license is selected without explicit approval.
- Repositories catalogued as `reference-only` (benchmarks, competitor implementations, GPL/AGPL or proprietary code) are read for methodology only; no source is copied into the product.
- Generated assets inherit terms from their source licenses and are recorded per artifact.
- Model weights follow their own licenses; downloading a model does not grant rights to its outputs beyond its terms.

## 8. Record keeping

For each run, persist: source URL, owner, license, permission proof reference, attribution text, restrictions, transformation description, and QC verdict. Records are append-only and included in the run artifact bundle.

## 9. Known limitations

- Automated license detection is unreliable; human confirmation via G3 is mandatory.
- Platform terms change; this policy is a design baseline, not legal advice.
- No legal review has been performed for specific jurisdictions.
