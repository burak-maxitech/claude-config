# GSC Setup README Template

This is the **template content** that the `/seo-review` orchestrator auto-writes to `.seo-data/gsc/README.md` on first detection (when `.seo-data/gsc/` exists but `README.md` inside it doesn't).

It's written verbatim — no variable substitution. The target audience is the **human user** who's about to configure GSC API access, not Claude.

---

## Template content (begin)

```markdown
# Google Search Console — API Configuration

This folder configures `/seo-review`'s Search Console API integration.
Drop a `config.yaml` here (template below) and the next `/seo-review` run
will produce traffic-aware recommendations from your GSC data.

## What does the skill do with this data?

- Identifies high-impressions, low-CTR pages (title/meta rewrite targets)
- Surfaces queries where you rank at position 5-20 (highest-leverage band
  for on-page optimization)
- Catalogs pages Google crawled-but-didn't-index (content quality signals)
- Detects 404 clusters that match recent code renames (auto-flags bulk
  redirect opportunities)
- Reranks all findings by traffic impact (impressions-weighted)

The /100 score does **not** change based on this data — GSC is informational.
Your `docs/seo-history.md` stays comparable across runs whether GSC is
configured or not.

## Setup (one-time, ~5 minutes)

### Prerequisites

1. **A GCP project.** Any GCP project will do — the Search Console API is
   free within quota (1,200 QPM Performance / 2,000 URLs/day for URL
   Inspection). List existing projects with `gcloud projects list`, or
   create one at https://console.cloud.google.com/ if you don't have one.
2. **`gcloud` CLI installed.** Install: https://cloud.google.com/sdk/docs/install.
   On Windows, the installer adds `gcloud` to PATH.
3. **Google account with verified GSC property access.** The Google
   account you sign in with during `gcloud auth` must be the same one
   that has the GSC property registered + verified.

### Enable the API on your project

4. Enable Search Console API on the project that will track quota:
   ```
   gcloud services enable searchconsole.googleapis.com --project=<your-gcp-project-id>
   ```

   This is required even though Search Console API is free — Google Cloud's
   quota infrastructure needs the API explicitly enabled on the billable
   project. Skipping this step returns HTTP 403 SERVICE_DISABLED on first call.

### Authenticate

5. Run once (opens browser for OAuth):
   ```
   gcloud auth application-default login \
     --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform
   ```

   The explicit `--scopes` flag is important — Search Console API often
   accepts default `cloud-platform` scope, but this is undocumented and
   has broken in the past. Explicit `webmasters.readonly` is durable.

6. **Set quota project (required, not optional):**
   ```
   gcloud auth application-default set-quota-project <your-gcp-project-id>
   ```

   Google Cloud APIs called via user-credential ADC require a quota project
   to bill against. The skill reads this value and sends it on every API call
   via the `x-goog-user-project` header. Without it, all calls return
   HTTP 403 SERVICE_DISABLED — even when auth is otherwise valid.

### Configure `/seo-review`

7. Create `.seo-data/gsc/config.yaml`:

   ```yaml
   site_url: sc-domain:example.com    # or "https://example.com/" for URL-prefix properties

   # Optional:
   # lookback_days: 90                # 7-365, default 90
   ```

   The exact `site_url` format must match what's registered in GSC.
   Check at https://search.google.com/search-console > Settings > Property settings.
   - Domain properties look like: `sc-domain:example.com`
   - URL-prefix properties look like: `https://example.com/` (with trailing slash)

8. Run `/seo-review`. The "Detected:" line should now say
   `Mode: heuristic + GSC (Search Console API — ...)`.

### Quick verification (optional)

You can sanity-check auth + quota project before running the skill. PowerShell:

```powershell
$TOKEN = gcloud auth application-default print-access-token
$QUOTA = (Get-Content "$env:APPDATA\gcloud\application_default_credentials.json" | ConvertFrom-Json).quota_project_id
Invoke-RestMethod -Method Get `
  -Uri "https://www.googleapis.com/webmasters/v3/sites" `
  -Headers @{Authorization = "Bearer $TOKEN"; "x-goog-user-project" = $QUOTA} | `
  ConvertTo-Json -Depth 5
```

Bash:

```bash
TOKEN=$(gcloud auth application-default print-access-token)
ADC_DIR=$(gcloud info --format="value(config.paths.global_config_dir)")
QUOTA=$(jq -r '.quota_project_id' "$ADC_DIR/application_default_credentials.json")
curl -s -H "Authorization: Bearer $TOKEN" \
     -H "x-goog-user-project: $QUOTA" \
     "https://www.googleapis.com/webmasters/v3/sites" | jq
```

Expected: a JSON object with a `siteEntry` array listing every GSC property
your account can read. Empty array means no properties on this account.

### Verify the first run

- API auth probe: `gcloud auth application-default print-access-token` should print a token. The skill calls `GET /webmasters/v3/sites` at start of each run to verify access; failures surface in footer with specific remediation.
- Performance: 3 `searchanalytics.query` calls per run (queries digest, pages digest, url_impressions_map).
- Indexing: up to 100 `urlInspection.index.inspect` calls per run, prioritizing high-impression URLs + sitemap probe failures + recently-changed paths. Well under the 2,000/day per-property quota.

## Privacy

This folder is **automatically added to `.gitignore`** the first time the
skill detects it. `config.yaml` contains `site_url` which is property-
identifying (not secret, but worth keeping private by default). If you
want to commit anyway (e.g., team-shared config), remove the
`.seo-data/gsc/` line from `.gitignore`.

## Folder layout

```
.seo-data/gsc/
├── README.md         (this file)
└── config.yaml       (API configuration — site_url + optional lookback_days)
```

Nothing else is needed.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Mode says "heuristic-only" despite `config.yaml` filled in | `gcloud` CLI not installed | Install gcloud SDK: https://cloud.google.com/sdk/docs/install |
| Same, with `gcloud` available | ADC not configured | Run `gcloud auth application-default login --scopes=...` (see Authenticate above) |
| Footer says `ADC quota project not set` | Skipped step 6 above | Run `gcloud auth application-default set-quota-project <your-gcp-project>` |
| Footer says `Search Console API not enabled on quota project '<X>'` | Skipped step 4 above | Run `gcloud services enable searchconsole.googleapis.com --project=<X>` |
| Footer says `Search Console API auth failed: 401 UNAUTHENTICATED` | OAuth scope insufficient | Re-run `gcloud auth application-default login` with the `--scopes=https://www.googleapis.com/auth/webmasters.readonly,...` flag |
| Footer says `403 PERMISSION_DENIED` with `SERVICE_DISABLED` in details | API not enabled OR `x-goog-user-project` header missing (skill bug) | Run `gcloud services enable searchconsole.googleapis.com --project=<your-gcp-project>` and `gcloud auth application-default set-quota-project <your-gcp-project>` |
| Footer says `Search Console API access denied: 403 PERMISSION_DENIED` (no SERVICE_DISABLED) | The Google account isn't verified on this GSC property | Verify property ownership in https://search.google.com/search-console > Settings, or switch ADC to an account that owns the property |
| Footer says `site_url '<X>' not in your verified properties` | `site_url` value doesn't match what's registered in GSC | Check exact format at https://search.google.com/search-console > Settings > Property settings. `sc-domain:example.com` for Domain properties; `https://example.com/` (with trailing slash) for URL-prefix |
| Footer says `Config error: nested keys not supported` | `config.yaml` has indented keys | Use flat single-level keys only (`site_url: x` not `gsc:\n  site_url: x`) |
| Footer says `URL Inspection quota exhausted` | Hit 2,000/day per-property cap | Re-run tomorrow — graceful degrade kept the run going |
| First run takes 10-15 seconds | Normal — up to 100 parallel URL inspections + 3 Performance queries | No action needed |

## Removing GSC integration

To go back to heuristic-only mode: delete the `.seo-data/gsc/` folder
(or just `config.yaml`). The next `/seo-review` will note "Mode:
heuristic" and behave exactly as it did before any GSC config was
added.
```

## Template content (end)

---

## Implementation note for the orchestrator

The orchestrator writes this content **once**, on the first detection of `.seo-data/gsc/` without a `README.md` inside it. Subsequent runs do NOT overwrite the README — the user may have edited it (e.g., added project-specific notes). Idempotency check: `Read` the file; if it exists, skip the write.

The template above is the canonical baseline. If this reference file is updated, existing `.seo-data/gsc/README.md` files in user projects do NOT auto-update — they're treated as user-owned content. To force a refresh, the user can delete their README and re-run.
