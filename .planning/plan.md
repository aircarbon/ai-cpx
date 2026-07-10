# Plan: Replace MinIO with SeaweedFS (SaaS path)

**Status:** Planning
**Date:** 2026-07-10
**Context:** AI CPX is a SaaS product. MinIO AGPLv3 is only acceptable for pure internal VPS use. For SaaS we replace MinIO with SeaweedFS **before** implementation/deployment work that depends on object storage.

---

## 1. Decision

| Option | License | SaaS fit | Decision |
|--------|---------|----------|----------|
| MinIO | AGPL-3.0 (community archived / commercial push) | Poor — AGPL + SaaS is a legal risk | **Reject for SaaS** |
| SeaweedFS | Apache 2.0 | Good — permissive, S3 API, production-proven | **Adopt** |
| Managed S3 (AWS/GCS) | N/A (vendor) | Good long-term multi-tenant | Optional later |

**Decision:** Use **SeaweedFS** as the self-hosted S3-compatible object store for SaaS (and preferred default for all non-internal-only deploys). Keep the app on **boto3 S3 API** so the app code stays storage-agnostic.

---

## 2. Goals & non-goals

### Goals
- Drop MinIO from SaaS topology and docs so we never ship AGPL object storage with the product.
- Keep existing app contract: `app/core/s3_client.py` + env vars (`S3_ENDPOINT`, `S3_PUBLIC_ENDPOINT`, `S3_BUCKET_NAME`, `S3_ROOT_USER`, `S3_ROOT_PASSWORD`).
- Provide a one-command (or compose) local/dev SeaweedFS setup equivalent to today’s MinIO README path.
- Support document layout: first-level folder = project, PDF keys under `{project}/{file}.pdf`.
- Align with deployment constraints already agreed:
  - **API must not be publicly exposed** (internal network / private ingress only).
  - **Risk calculator CronJob starts suspended**; enable only after a verified manual run (OpenAI cost control).

### Non-goals (this plan)
- Multi-region SeaweedFS cluster HA design (phase 2).
- Migrating live production MinIO data (none assumed yet; document path if needed).
- Replacing managed cloud S3 if a tenant later prefers AWS/GCS.
- Changing PDF parsing, risk pipeline, or Mongo models.

---

## 3. Why SeaweedFS (SaaS-relevant)

- **Apache 2.0** — safe to run under a commercial SaaS without AGPL copyleft exposure.
- **S3-compatible API** — `boto3` client in `app/core/s3_client.py` needs endpoint + access key + secret + bucket only.
- **Simple bootstrap** — `weed mini` / Docker one-liner can start S3 on port **8333** with credentials and a pre-created bucket.
- **Active project** — practical MinIO replacement after MinIO community stagnation / license pressure.
- **Scale path** — master + volume + filer/S3 gateway later without changing app code.

App surface that depends on S3 (no MinIO-specific SDK):

| Area | File | Ops used |
|------|------|----------|
| List PDFs by project folder | `app/core/s3_client.py` | `list_objects_v2` |
| Download PDF | `app/core/s3_client.py` | `download_fileobj` |
| Existence check | `app/core/s3_client.py` | `head_object` |
| Public-style URL string | `app/core/s3_client.py` | string build from `S3_PUBLIC_ENDPOINT` |
| Ingestion worker | `app/services/doc_parser/*` | list + download |
| URL redaction in API | `app/services/api/routers/risk.py` | `AI_CPX_PUBLIC_DOCUMENT_URLS` |

**Compatibility requirement:** SeaweedFS S3 must support those four boto3 calls for PDF keys. No multipart, versioning, or object-lock needed for v1.

---

## 4. Target architecture (SaaS)

```
                    ┌─────────────────────────────────────────┐
                    │  Private network (no public AI CPX API) │
                    │                                         │
  Operators only ──►│  API :8001  (ClusterIP / private LB)    │
                    │  doc-parser (Deployment)                │
                    │  risk-calculator (CronJob, suspended)   │
                    │         │                │              │
                    │         ▼                ▼              │
                    │     MongoDB          SeaweedFS S3       │
                    │                      :8333              │
                    └─────────────────────────────────────────┘
                              │
                    OpenAI / Langfuse (egress only)
```

### Network / security rules
1. **API:** not on public internet. Internal DNS or VPN/bastion only. No `0.0.0.0` NodePort/LoadBalancer without auth in front (API has **no auth today** — see risks).
2. **SeaweedFS S3:** internal only for app services. Optional separate public doc endpoint only if product later requires browser PDF links; default `AI_CPX_PUBLIC_DOCUMENT_URLS=false`.
3. **SeaweedFS admin/master UI ports:** never public.
4. **Credentials:** strong access/secret keys; no `minioadmin` defaults in SaaS envs.
5. **Risk calculator:** CronJob `suspend: true` until first manual Job succeeds and cost is reviewed.

---

## 5. SeaweedFS deployment shapes

### 5.1 Dev / single-node (replace MinIO docker run)

Prefer SeaweedFS mini (all-in-one S3):

```bash
# Example — ports/env align with .env
docker run -d --name seaweedfs \
  --network internal \
  -p ${S3_API_PORT:-8333}:8333 \
  -e AWS_ACCESS_KEY_ID=${S3_ROOT_USER} \
  -e AWS_SECRET_ACCESS_KEY=${S3_ROOT_PASSWORD} \
  -e S3_BUCKET=${S3_BUCKET_NAME} \
  -v seaweedfs-data:/data \
  chrislusf/seaweedfs
```

**Notes:**
- S3 endpoint becomes `http://seaweedfs:8333` (in-cluster) / `http://localhost:8333` (host).
- Bucket is created via `S3_BUCKET` env on mini.
- No `mc anonymous set download` step required for private SaaS; keep objects private by default.

### 5.2 SaaS / VPS compose (recommended v1)

Add optional `docker/docker-compose.seaweedfs.yml` (or infra repo) with mini first; split master/volume/filer later if needed.

Services remain:

| Service | Image / command | Notes |
|---------|-----------------|-------|
| seaweedfs | `chrislusf/seaweedfs` mini or `server -s3` | Persistent volume |
| api | existing `Dockerfile.api` | private network only |
| docparser | same image | polls S3 folders |
| risk-calculator | same image | **manual first**, then CronJob |

Mongo stays external (Atlas or separate container), same as today.

### 5.3 Kubernetes (later)

- SeaweedFS Helm/operator or single StatefulSet mini for early SaaS.
- App Deployment + CronJob (risk-calculator suspended).
- NetworkPolicy: deny ingress to API from outside namespace; allow only internal clients.

---

## 6. Configuration changes

### 6.1 `.env.example` (rename section MinIO → S3-compatible)

Proposed defaults for SaaS/dev with SeaweedFS:

```env
# === S3-compatible object storage (SeaweedFS) ===
# In-cluster / Docker network endpoint used by app services
S3_ENDPOINT=http://seaweedfs:8333
# Host-reachable endpoint for URL generation / local tools
S3_PUBLIC_ENDPOINT=http://localhost:8333
S3_BUCKET_NAME=aicpx-documents
S3_ROOT_USER=aicpx_s3_access
S3_ROOT_PASSWORD=change-me-strong-secret

# Local SeaweedFS publish ports (host)
S3_API_PORT=8333
# Optional: remove MinIO console ports; SeaweedFS has different admin surfaces
# S3_CONSOLE_PORT=  (unused for SeaweedFS mini)
```

Keep variable **names** (`S3_ROOT_USER` / `S3_ROOT_PASSWORD`) so `s3_client.py` stays unchanged.

### 6.2 App code

| Change | Priority | Detail |
|--------|----------|--------|
| Comments / log strings “MinIO” → “S3” or “SeaweedFS” | Low | Docs clarity only |
| `s3_client.py` pagination for `list_objects_v2` | Medium | Existing bug; fix while validating SeaweedFS |
| Path-style addressing | Verify | SeaweedFS often needs path-style; boto3 may need `Config(s3={'addressing_style': 'path'})` if virtual-host fails on custom endpoints |
| Signature / region | Verify | Keep `region_name="us-east-1"` unless SeaweedFS config requires otherwise |

**Likely only code change:** ensure boto3 client works with SeaweedFS path-style endpoints. Everything else is env + ops.

### 6.3 Docs / AGENTS

Update:
- `README.md` MinIO section → SeaweedFS setup
- `AGENTS.md` “share the same MinIO instance” → SeaweedFS
- `.planning/codebase/*` references when re-scanned

---

## 7. Implementation phases

### Phase 0 — Preconditions (before any storage-dependent deploy)
- [ ] Confirm SaaS legal stance: **no MinIO in product stack**.
- [ ] Confirm API remains private (network policy / no public Service).
- [ ] Confirm risk-calculator starts **suspended** / manual-only until verified.

### Phase 1 — Spike (½–1 day)
- [ ] Run SeaweedFS mini with credentials + bucket.
- [ ] Point local `.env` at SeaweedFS.
- [ ] Verify with AWS CLI or boto3:
  - create/list bucket (if not pre-created)
  - `put` sample PDF under `DemoProject/sample.pdf`
  - `list_objects_v2` returns key
  - `head_object` / `download_fileobj` succeed
- [ ] Run `docparser` once; confirm Project + SourceDocument created.
- [ ] Note any boto3 addressing/signature quirks → patch `get_s3_client()`.

### Phase 2 — Repo integration (1 day)
- [ ] Update `.env.example` for SeaweedFS defaults.
- [ ] Replace README MinIO block with SeaweedFS.
- [ ] Add `just seaweedfs` (or compose snippet) for local bootstrap.
- [ ] Optional: `docker/docker-compose.seaweedfs.yml` external dependency file.
- [ ] If needed: path-style config in `app/core/s3_client.py`.
- [ ] Fix `list_objects_v2` pagination while touching the client.

### Phase 3 — SaaS deploy wiring (ops)
- [ ] Deploy SeaweedFS with persistent disk + secrets for access/secret keys.
- [ ] Wire `S3_*` env for api, docparser, risk-calculator.
- [ ] Ensure SeaweedFS and API are **not** public.
- [ ] Seed buckets + upload test project PDFs.
- [ ] Run docparser → verify Mongo docs.
- [ ] **Manual** risk-calculator Job once; review OpenAI cost.
- [ ] Only then unsuspend CronJob (if schedule desired).

### Phase 4 — Cleanup
- [ ] Remove MinIO docker examples from README.
- [ ] Grep for `minio` / `MinIO` / `9100` / `mc anonymous` and purge SaaS docs.
- [ ] Document “internal VPS may still use MinIO if legal accepts AGPL” as **out of band** only — not the default path.

---

## 8. Migration notes (if MinIO data already exists)

If a prior MinIO volume has PDFs:

```bash
# Example with rclone between two S3-compatible endpoints
rclone sync minio:test-bucket seaweedfs:aicpx-documents \
  --s3-provider=Other \
  --progress
```

Then flip `S3_ENDPOINT` / credentials and re-run docparser (idempotent by filename today — known cross-project filename bug remains separate).

Fresh SaaS: skip migration; upload PDFs directly to SeaweedFS.

---

## 9. Validation checklist

| Check | Pass criteria |
|-------|----------------|
| License | No MinIO binary/image in SaaS compose/k8s |
| S3 list | Folders under bucket appear as projects |
| S3 get | PDF downloads and parses |
| API private | External curl to API fails / not routed |
| Doc URLs | With `AI_CPX_PUBLIC_DOCUMENT_URLS=false`, top-evidence returns `null` URLs |
| Risk cost | First run is manual; CronJob still suspended until sign-off |
| Secrets | No default `minioadmin` / weak passwords in SaaS env |

---

## 10. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| boto3 virtual-host addressing fails on SeaweedFS | Force path-style in client config during Phase 1 |
| S3 API edge differences | Only use list/get/head; avoid advanced S3 features |
| Accidental public API (no auth) | Network isolation is mandatory until auth is built |
| Accidental public objects | Do **not** set anonymous download; keep `AI_CPX_PUBLIC_DOCUMENT_URLS=false` |
| OpenAI cost blow-up | Suspended CronJob + DEV caps + manual first run |
| SeaweedFS mini not enough for multi-tenant scale | Phase 2: split master/volume/filer or move to managed S3; app unchanged |
| MinIO leftover in developer muscle memory | Docs + `just` recipes + CI grep for `minio` images |

---

## 11. Related product constraints (carry into deploy plan)

These are **not** SeaweedFS-specific but gate go-live:

1. **AI CPX API is internal-only** — SaaS frontends or partner systems must not hit a public unauthenticated FastAPI. Add gateway auth later; network lock first.
2. **Risk calculator CronJob starts suspended** — enable after one successful manual run and cost review.
3. **Object storage for SaaS = SeaweedFS (Apache 2.0)** — MinIO only if a pure internal VPS deployment explicitly accepts AGPL (not this track).

---

## 12. Suggested file touch list

| File | Action |
|------|--------|
| `.planning/plan.md` | This document |
| `.env.example` | SeaweedFS endpoints/ports/comments |
| `README.md` | Replace MinIO setup with SeaweedFS |
| `AGENTS.md` / `CLAUDE.md` | Storage naming |
| `app/core/s3_client.py` | Path-style + pagination if needed; comment cleanup |
| `justfile` | `seaweedfs` recipe |
| `docker/docker-compose.seaweedfs.yml` | Optional external storage compose |
| Future k8s manifests | SeaweedFS + private API + suspended CronJob |

---

## 13. Exit criteria

Plan is **done for implementation** when:

1. Local SeaweedFS serves the bucket and docparser ingests a sample project.
2. Repo docs and env examples no longer prescribe MinIO for SaaS.
3. Deploy runbook states: private API, SeaweedFS credentials, suspended risk CronJob, manual first risk run.

**Next step after plan approval:** execute Phase 1 spike (SeaweedFS mini + boto3 smoke tests), then Phase 2 repo updates.
