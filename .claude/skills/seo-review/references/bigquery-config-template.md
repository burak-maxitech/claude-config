# BigQuery Config Template — `.seo-data/gsc/config.yaml`

Loaded by the orchestrator (Step 1.6) to resolve BigQuery connection params before invoking any query from `bigquery-queries.md`. Defines:

- The **flat YAML schema** users edit by hand (per Plan-agent A3 — nested keys explicitly rejected)
- Required vs optional keys + defaults
- The auto-written template the orchestrator drops on first detection of a fresh `.seo-data/gsc/` folder
- The setup walkthrough that ships in `gsc-setup-readme-template.md` (BigQuery section — kept in sync with this file)

For column inventory, see `bigquery-schema.md`. For SQL templates that consume these params, see `bigquery-queries.md`.

---

## Why flat keys only

The orchestrator parses `config.yaml` with a single `Grep` over the line pattern `^([a-z_]+):\s*(.+)$` — no YAML library available in `allowed-tools`. Nested keys would silently misparse:

```yaml
# BROKEN — flat parser reads "bigquery:" as key with empty value
bigquery:
  project_id: my-project
```

…vs the supported form:

```yaml
# WORKS
project_id: my-project
dataset_id: searchconsole
```

Validation rule: any line matching `^\s+[a-z_]+:` (leading whitespace before key) triggers `Config error: nested keys not supported. Use flat top-level keys only. See .seo-data/gsc/README.md for an example.` and falls through to the CSV path.

---

## Schema

| Key | Required? | Type | Default | Description |
|---|---|---|---|---|
| `project_id` | **yes** | string | — | GCP project ID hosting the GSC export dataset. ADC has no default project; this is the explicit binding. |
| `dataset_id` | **yes** | string | — | BigQuery dataset name (conventional: `searchconsole`). |
| `location` | **yes** | string | — | BigQuery location for the dataset. Typical values: `US`, `EU`, `asia-northeast1`. Found in BigQuery Console under the dataset's Details tab > Data location. Required because `bq query` defaults to multi-region US which will fail for non-US datasets. |
| `site_url` | **yes for API path / no for BQ path** | string | first `site_url` value in the data (BQ only) | **v3.x**: required when using the Search Console API path (Path 1) — identifies the property to query via `searchanalytics.query` / `urlInspection.index.inspect`. **v3 BQ path**: optional — used only when the BQ dataset exports multiple properties. If `site_url` is present alongside BQ keys, the API path wins per precedence (API > BQ > CSV). To force BQ-only behavior, omit `site_url`. See `gsc-api-schema.md` for the canonical API contract. |
| `lookback_days` | no | integer | `90` | Days back from `CURRENT_DATE()`. Range 7-365. Lower = faster + less data; higher = more signal + more bytes scanned. 90 matches GSC UI default. |

**Unknown keys are warned + ignored**: `Config warning: unknown key '<name>' in config.yaml — ignored. Supported keys: project_id, dataset_id, location, site_url, lookback_days.`

---

## Example config (matches a real user setup)

```yaml
# .seo-data/gsc/config.yaml
# BigQuery connection for /seo-review GSC Performance ingestion.
# See bigquery-config-template.md (in skill references) for full schema.

project_id: burakarik
dataset_id: searchconsole
location: US

# Optional — uncomment to override:
# site_url: sc-domain:example.com
# lookback_days: 90
```

---

## Auto-written template

When the orchestrator detects `.seo-data/gsc/` exists but `config.yaml` is missing AND BigQuery setup banner has not been suppressed, the template emitted is:

```yaml
# .seo-data/gsc/config.yaml
# BigQuery connection for /seo-review GSC Performance ingestion.
#
# Required: project_id, dataset_id, location
# Fill these in and re-run /seo-review.
#
# Don't have a BigQuery export yet? Skip this file — /seo-review will
# fall back to GSC CSV exports (drop them in .seo-data/gsc/performance/).
# See .seo-data/gsc/README.md for the CSV path.

project_id:        # <— your GCP project ID
dataset_id:        # <— BigQuery dataset (typically: searchconsole)
location:          # <— US / EU / asia-northeast1 / etc.

# Optional:
# site_url:        sc-domain:example.com    # only if dataset has multiple properties
# lookback_days:   90                       # 7-365, default 90
```

Orchestrator detects "unfilled template" via the heuristic: `project_id:` or `dataset_id:` or `location:` followed only by whitespace → emit warning `config.yaml present but project_id/dataset_id/location not filled in — see .seo-data/gsc/README.md for setup walkthrough` and fall through to CSV.

---

## Setup walkthrough (mirrored in `gsc-setup-readme-template.md`)

The README template written into `.seo-data/gsc/README.md` includes this walkthrough verbatim, formatted as a numbered checklist.

### Prerequisites

1. **A GCP project with BigQuery API enabled.** Create one at https://console.cloud.google.com/ if you don't have one. The free tier includes 1 TB of query processing per month — far more than `/seo-review` will ever use.
2. **`gcloud` CLI installed** with `bq` component. Install: https://cloud.google.com/sdk/docs/install. On Windows, the installer adds both `gcloud` and `bq` (as `gcloud.cmd` / `bq.cmd`) to PATH.
3. **Application Default Credentials configured.** Run once: `gcloud auth application-default login`. Browser-based OAuth; produces ADC at `~/.config/gcloud/application_default_credentials.json`.
4. **IAM role on the dataset** (or project): at minimum `roles/bigquery.dataViewer` on the dataset + `roles/bigquery.jobUser` on the project. If you own the project, you already have these via `roles/owner`.

### Configure GSC Bulk Data Export

5. In Google Search Console, open your property → **Settings** → **Bulk data export** → **Configure**.
6. Set the destination project + dataset name. Conventional dataset name: `searchconsole`. **You must use a dataset that doesn't already exist** — GSC creates it on first export. If the dataset already exists, GSC will refuse.
7. Click Continue. GSC validates IAM (your account needs `roles/bigquery.dataEditor` to create the dataset + write to it). On success, the export starts.
8. **Wait ~2 days.** First export takes 24-48 hours. Subsequent exports run daily and lag ~2 days behind real-time.
9. Verify the export landed: `bq ls <your-project>:searchconsole` should list `searchdata_url_impression` (and `searchdata_site_impression`, possibly `ExportLog`).

### Configure `/seo-review`

10. Create `.seo-data/gsc/config.yaml` (template above; orchestrator auto-creates an unfilled template on first run when the folder exists but config doesn't).
11. Fill in `project_id`, `dataset_id`, `location`. Save.
12. Run `/seo-review`. The orchestrator's Step 0 "Detected:" line should now read `gsc_mode: enabled (bigquery)` or similar.

### Verify the first run

13. Watch the report footer for `bytes_processed: <N> MB` per BigQuery query — should be well under 1 GB total for typical sites.
14. Score row in `docs/seo-history.md` carries `[gsc]` prefix on priorities when GSC is active.
15. Section 3 "GSC Insights" should populate with traffic-weighted findings.

---

## Failure modes the walkthrough doesn't cover

These surface in the report footer / Section 1 banner, not the README:

- `bq: command not found` → install link in setup banner; fall back to CSV.
- `gcloud auth application-default print-access-token` returns empty → setup banner with `gcloud auth application-default login` command; fall back to CSV.
- BigQuery `Access Denied` on the dataset → IAM step missed; surface the role required (`roles/bigquery.dataViewer`).
- Dataset doesn't exist → "wait for GSC's first export (~2 days)" + link to GSC Settings > Bulk data export.
- Table missing (`searchdata_url_impression`) → same as dataset-missing UX.
- Query exceeds `--maximum_bytes_billed=1000000000` → BigQuery aborts; surface bytes-estimated; suggest reducing `lookback_days`.

All non-blocking — the orchestrator falls through to CSV if configured, or heuristic-only otherwise (Section 1 banner per the 4-state matrix).
