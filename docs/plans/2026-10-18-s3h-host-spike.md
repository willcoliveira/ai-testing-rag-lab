---
stage: S3h
name: host-spike
nodes: [S3h]
date: 2026-10-18
status: draft (not approved)
---

# S3h: Host evaluation spike

Part of the main plan (phase P1, release v0.1). Branch: `feat/s3h-host-spike`. No build project
step: this stage picks where the fake-model container lives, from measurements, and records the
choice in `docs/decisions/ADR-001-host.md`.

Go message: **not yet given.** No account is created, no card is added and nothing is deployed
until your go is quoted here verbatim.

## Goal

- Deploy the **same** S3 container image, with the fake model and the baked-in bge-small ONNX
  embedder, to two or three hosts.
- Measure what the docs can't settle: cold start, memory at idle and after the first `/ask`,
  deploy time, and what the host's proxy puts in the forwarded-IP headers (S10's per-IP limit
  depends on it).
- Compare the hosts on cost at scale to zero, secrets, logs, deploy from Actions, registry,
  region and spending controls.
- Keep one host, tear the others down, and record why in ADR-001.

## Out of scope

| Item | Where it goes |
|---|---|
| A real model on the host, keys, rate limit, budget, kill switch | S10 |
| Persisted demo budget (SQLite on a volume or the host's KV) | S10; the ADR only records what each host offers |
| A custom domain | later, if you want one; the spike uses the host's own URL. The ADR records each host's option |
| trivy image scan and SBOM | S11 and release |
| The path to prod on AWS | S10 (doc only) |
| Changes to the S3 API beyond the optional lab probe (see choices) | not in this stage |

## Prerequisites

1. **S3 merged.** The container (`deploy/Dockerfile`, digest-pinned Python 3.13 slim, non-root,
   embedder baked in with its sha256 checked, `/healthz`, `/version`) exists on `main`. S3h
   starts from that commit.
2. **Your go, quoted here,** naming the hosts to sign up for, card or no card, and regions (see
   "Decisions needed"). Sign-ups, cards, billing accounts and CLI logins are your actions. I
   don't create accounts or add payment methods.
3. **Docker** running on your Mac for the local baseline (the same image under `docker stats`).
4. **The GitHub plan question** (decision D4) answered, because it decides whether the deploy job
   can have required reviewers.

## Candidates (facts fetched 2026-10-18)

Every price, limit and claim below comes from the source named in its cell, fetched on
2026-10-18. "Vendor claim" marks a vendor's own statement about its performance. "Unconfirmed"
means no fetched source settles it; the spike measures it or the ADR says so.

| | Render (free web service) | Fly.io | Google Cloud Run |
|---|---|---|---|
| Free tier | Free instance $0/month [R2]; 750 free instance hours per workspace per month, spun-down services don't use them [R1] | **No free tier** for new organizations; a trial of 2 VM hours or 7 days, whichever comes first, trial Machines auto-stop after 5 minutes [F1, F2] | Request-based billing: first 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests free per month, applied as a Tier 1-priced discount [G1, G2] |
| Card on file | Not needed for Free; without a payment method, overages suspend Free services instead of billing [R1] | "You don't need a credit card to start the trial" [F1]; "All organizations (except for Linked Organizations) require a credit card on file" [F1]; a card is needed "to do things like deploying multiple apps and deploying public images" [F3] | A Cloud Billing account is needed to use the Free Tier [G2]; the Free Trial signup needs a card or other payment method [G2] |
| Cost when idle | $0 (Free) | Stopped or suspended Machine: $0.15/GB/month of rootfs only [F1] | Idle instances that are not minimum instances are not charged [G1]; Artifact Registry storage free to 0.5 GiB, then $0.000136986 per GiB-hour [G16] |
| Memory and CPU | Free: 512 MB RAM, "Less than 1 CPU" [R2]. The first tier with ≥1 GB is 2 GB / 1 CPU at $25/month [R2], and spin-down is described only for Free [R1] | shared-cpu-1x 1 GB: $6.70/month in iad, $7.73/month in fra, billed per second while running [F1]; additional RAM $6.00/GB/month [F1]. lhr price unconfirmed | Default 512 MiB, maximum 32 GiB [G3]. 1 GiB needs ≥0.5 vCPU; below 1 vCPU, concurrency must be 1, billing request-based and the execution environment first generation; 1 vCPU allows up to 4 GiB [G3, G4]. Request-based rates in the page's default view (the region selection is not readable in the fetched page; treated as Tier 1): $0.000024 per vCPU-second and $0.0000025 per GiB-second active, $0.40 per million requests [G1]; Tier 2 rates (London, Frankfurt) unconfirmed |
| Does ~1 GB fit? | Only if the image fits in 512 MB, unconfirmed until measured; otherwise $25/month always on | Yes, 1 GB preset | Yes, 1 GiB at 0.5 or 1 vCPU. The writable filesystem is in memory, so anything written at start counts against the limit [G5] |
| Sleep and cold start | Spins down after 15 minutes without inbound traffic; spin-up "takes about one minute" (vendor claim) [R1]. Free services "might restart ... at any time"; filesystem is ephemeral [R1] | Fly Proxy autostop/autostart, scale to zero with `min_machines_running = 0`; "a cold start takes about 2 seconds or more for common apps" (vendor claim); suspend resumes in "a few hundred milliseconds" (vendor claim), needs ≤2 GB, and every deploy discards the snapshot [F6, F7] | Scales to zero by default; no cold-start figure found. Requests wait up to 3.5 times the average startup time or 10 seconds, whichever is greater; startup CPU boost is available [G12]. Unconfirmed: idle time before scale-in |
| At most one instance | Free can't scale beyond one instance [R1] | Autostop never creates Machines; the maximum is the Machines you created [F6] | Maximum instances can be set, but "can be exceeded for a brief period" [G13] |
| Secrets | Environment variables and secret files (at `/etc/secrets/<file>`, 1 MB total) set in the dashboard; storage encryption not stated [R8] | `fly secrets set`; an encrypted vault the API can only write to, injected as env vars at boot [F11] | Secret Manager, as an env var or a mounted volume [G8]; free tier 6 active secret versions and 10,000 access operations a month [G2] |
| Logs | Hobby retention 7 days; log streams to a third party [R9] | `fly logs` live tail; Grafana log search keeps 7 days; Log Shipper to export [F12] | Request, container and system logs go to Cloud Logging [G9]; first 50 GiB per project per month free [G2]; retention period unconfirmed |
| Deploy from Actions | **No inbound OIDC.** Render's OIDC is outbound (services to AWS, Anthropic, OpenAI) and needs a Pro workspace [R6]. Lab path: the service's secret deploy hook URL, with `imgURL` set to a tag or digest [R3]. Avoid the API key: "An API key provides access to all workspaces you belong to" [R5] | **No inbound OIDC.** Fly's OIDC gives Machines tokens for AWS, Azure or GCP [F15]. Lab path: an app-scoped deploy token, `fly tokens create deploy --expiry <duration>` (default validity 20 years) [F9], stored as `FLY_API_TOKEN` [F10] | **OIDC:** `google-github-actions/auth@v3` with Direct Workload Identity Federation, "obviates the need to export a long-lived credential", workflow needs `id-token: write` [G14]; `deploy-cloudrun@v3` deploys an image [G15] |
| Registry | Pulls public images from any reachable registry; private from Docker Hub, GHCR, GitLab, Google Artifact Registry, ECR with a credential; image must be `linux/amd64`; tag or digest [R4]. Unconfirmed: whether Free accepts an image-backed service | `registry.fly.io/<app>` or public registries [F14]; private third-party registries unconfirmed; architecture requirement unconfirmed | Artifact Registry, or public Docker Hub and GHCR images; private GHCR through an Artifact Registry remote repository [G7]; a multi-arch manifest must include `linux/amd64` [G5] |
| Forwarded IP | Not in Render's docs. A feedback thread has a staff reply (2021): "we set the first IP in the list to the real client IP", and a later user report that Render appends to a client-sent `X-Forwarded-For` without clearing it [R11]. Unconfirmed | `Fly-Client-IP` is the client as Fly Proxy sees it; in `X-Forwarded-For` the rightmost address is the app's own IP and the header "must be treated with caution to avoid spoofing" [F8] | Not documented on the Cloud Run pages fetched. Unconfirmed |
| Regions near UK/EU | Frankfurt is the only EU region (others: Oregon, Ohio, Virginia, Singapore) [R7] | lhr London, ams, arn, cdg, fra [F5] | europe-west2 London and europe-west3 Frankfurt are Tier 2; europe-west1 Belgium and europe-west4 Netherlands are Tier 1 [G1] |
| Custom domain and TLS | Supported on Free; certificates created and renewed automatically; Hobby includes 2 domains [R1, R10] | Let's Encrypt certificates; first 10 single-hostname certificates free [F1, F13] | Domain mapping is Preview and "not production-ready", only in some regions (europe-west1 and europe-west4 yes, europe-west2 no); otherwise a load balancer or Firebase Hosting [G6] |
| Spending controls | Free needs none. A spend limit is mentioned for build-minute overages [R1]; a compute spend cap is unconfirmed | "We don't support billing alerts (yet)"; free allowances "don't cap your bill" [F4] | Alerts-only budgets don't cap spending [G10]. **Spend cap budgets** cover Cloud Run (`run.googleapis.com`): usage is paused when cost passes the cap until you lift it; one project and one service per cap; enforcement isn't instant, so overages are still billed [G11] |

**Considered and not added.** Hugging Face Spaces: CPU Basic has 16 GB and no hourly cost, but
Docker Spaces "require a paid plan to create" [O1]. Koyeb: its pricing page lists no free compute
instance [O2]. Neither fits better than the three above.

**What the table means.** On paper, Cloud Run is the only candidate with OIDC from Actions, free
scale to zero at 1 GiB and a hard spend cap; it needs a billing account. Render Free is the
card-free control, but 512 MB may not hold the embedder. Fly has the best-documented client-IP
header and a cheap 1 GB Machine, but no free tier and no billing alerts. The measurements decide.

## Measurement method

All measurements run from your Mac with `curl` and the host's own metrics, against the same image
digest. Raw values go in `docs/decisions/ADR-001-host-measurements.csv` with these columns: host,
region, instance size, image digest, UTC time, client location, measure, value, unit, how it was
read. Provenance is `hosted` for host runs and `local` for the Mac baseline. The ADR copies its
numbers from that file and states n; with n = 10 it gives the median and the maximum, and no
interval.

1. **Cold start, n = 10 per host.** A sample is cold only if the host's log shows uvicorn's
   startup line inside the sample's window; otherwise it is discarded and repeated.
   - Render: wait over 15 minutes with no traffic, then request.
   - Fly: `fly machine stop`, then request (cold from stopped). If `suspend` is tried, it is a
     separate arm and never stands in for a cold start.
   - Cloud Run: wait for scale-in, confirmed by the instance count metric reaching zero, then
     request.
   - Measure: `curl -w '%{time_starttransfer}'` on `/healthz` (time to first byte), plus the
     first `/ask` straight after (the embedder's first load).
2. **Warm latency, n = 20:** `/healthz` and one fixed `/ask`, median and maximum, for context only.
3. **Memory:** at idle after start, and after the first `/ask`. Read from the source chosen
   under "Choices" (the lab probe, or host metrics), with `docker stats` of the same image on the
   Mac as the baseline.
4. **Deploy time:** the Actions deploy job, from its start to `/version` returning the built
   SHA, for three deploys per host.
5. **Image:** the digest and compressed size each registry reports.
6. **Forwarded IP:** two requests per host, one plain and one with
   `X-Forwarded-For: 203.0.113.9` (a documentation address). Record the forwarded-IP headers the
   app received, the client IP the host logged, and your Mac's public IP. The ADR says which
   header S10 should trust on the chosen host, and how a spoofed value shows up.
7. **Spend:** each host's billing page at the end of the spike, set against the spike budget.

## Choices I made (you can change them)

| Item | Choice | Why |
|---|---|---|
| One image | built once in Actions for `linux/amd64` from the S3 Dockerfile, pushed to GHCR, then copied by digest to Artifact Registry and `registry.fly.io` (a manifest copy keeps the digest). The build turns off provenance and SBOM attestations so it pushes one plain single-platform manifest, not an index | "the same container" is checkable: AC2 compares digests, and an attestation index would change them for reasons unrelated to the hosts. Your Mac builds arm64, so the build is in Actions |
| Lab probe | a lab-only route `/_lab/probe`, mounted only when `RAGLAB_LAB_PROBE=1`, returning the forwarded-IP family of headers and the process's resident memory (stdlib, `/proc/self/status`). Off by default, with a test that it is 404 when unset; off on the kept host before the ZAP scan | one comparable memory number and the raw headers on every host. Alternative: host metrics and logs only, with no code change, but memory is then read differently on each host and the headers are not visible |
| Deploy auth | Cloud Run: OIDC (Workload Identity Federation, no key). Fly: app-scoped deploy token with a 30-day expiry, its expiry date in the ledger and rotated before it lapses if Fly is kept. Render: the deploy hook URL. All stored as GitHub secrets. Labelled **lab** where production would use OIDC everywhere | the narrowest credential each host offers |
| Render pull credential | a GHCR read-only package credential stored in Render, revoked at teardown | the image stays private while the repo is |
| Instance shape | Render Free (512 MB). Fly shared-cpu-1x 1 GB, `auto_stop_machines = "stop"`, `min_machines_running = 0`, one Machine. Cloud Run two arms: 1 GiB / 0.5 vCPU (first generation, concurrency 1) and 1 GiB / 1 vCPU; max instances 1. Each host is told the container listens on 8000 (Cloud Run's container port, Fly's `internal_port`, Render's port setting), so the image is not changed | the smallest shape that should hold the embedder, plus Render's free shape as the control |
| Workflow | `.github/workflows/deploy-host.yml`, `workflow_dispatch` plus push to `main`, one job per host; actions pinned by SHA, `contents: read` at the top, `id-token: write` only on the Cloud Run job, `persist-credentials: false`, timeouts | the S0 hardening rules; zizmor and `test_workflow_rules.py` check it |
| ZAP | `zaproxy/action-baseline` pinned by SHA, in the deploy workflow after the chosen host deploys, reusing `deploy/zap/` from S3 | the main plan's DAST row: "then against the host chosen in S3h" |
| Spike budget | $10 of hosted spend in total, checked on each billing page | a ceiling for a few days of tests; the real figure goes in the ledger |
| Judge | Fable 5.1, plus a `/security-review` pass, because the stage adds a deploy credential and a public URL | the main plan's rule for security-relevant stages |

## Acceptance criteria

**[CI]** marks criteria proven by a workflow run on the PR or on `main`. **[hosted]** marks
evidence that needs the accounts from your go. **[post-merge]** marks evidence that exists only
after you merge.

| # | Criterion | Evidence |
|---|---|---|
| AC1 | Your go is quoted verbatim in this plan before any sign-up: hosts, card or not, regions, GitHub plan answer | this file |
| AC2 | One image, built in Actions for `linux/amd64` from the S3 Dockerfile; the digest running on every host is recorded and they match (or the ADR says why not) | [CI] build job log; the measurements file; each host's deploy record |
| AC3 | The same fake-model container is deployed to the 2–3 hosts in your go, with the fake model config, scale to zero, at most one instance, in the approved region; `/healthz` answers 200 and `/version` returns the SHA the image was built from, on each host | [hosted] `curl` output per host in the ledger |
| AC4 | Deploy from Actions: Cloud Run with OIDC and no service-account key; Fly with an app-scoped deploy token with an expiry; Render with its deploy hook. No credential in the repo; the workflow passes zizmor and `test_workflow_rules.py` (SHA pins, `contents: read`, `id-token: write` only where used, `persist-credentials: false`, timeouts) | [CI] workflow run; `make check`; gitleaks |
| AC5 | The deploy job runs in a GitHub Environment with required reviewers. If the repo is still private on a plan where GitHub offers required reviewers only for public repositories [GH1], the criterion is recorded as **blocked while private**: the job uses an Environment where the plan allows one, otherwise repository secrets, and the blocked note and GO-PUBLIC.md item 8 name what go-public or a plan change unlocks and the reviewers to add | repo settings; a run waiting for approval, or the blocked note |
| AC6 | Measurements per the method: cold start n = 10, warm latency n = 20, memory at idle and after the first `/ask`, deploy time over 3 deploys, image size, for every host, with the Mac baseline; every row has its provenance | `docs/decisions/ADR-001-host-measurements.csv`; ledger |
| AC7 | Forwarded IP: on each host, the headers received for a plain request and for a spoofed `X-Forwarded-For` are recorded, and the ADR names the header S10 trusts on the chosen host and how a spoof appears | measurements file; ADR section "Client IP" |
| AC8 | `docs/decisions/ADR-001-host.md`: context, options, the comparison with sources and dates, the measured numbers copied from the measurements file, the decision, consequences for S10 (client-IP header, persisted budget option, spend cap) and S11, monthly cost at the expected use with its arithmetic, and the teardown record | review; the judge re-reads every number against the measurements file |
| AC9 | The chosen host is kept: scale to zero, at most one instance, the spend cap or alert the host offers is set (or the ADR says there is none), the lab probe is off, and after merge the deploy from `main` serves `/version` with the merged SHA | [hosted] settings in the ledger; [post-merge] `curl` of `/version` recorded in the ledger by the developer after you merge |
| AC10 | The other hosts are torn down: no services or apps left, images deleted from their registries, deploy tokens and hooks revoked, Workload Identity pool removed or the project deleted, their GitHub secrets deleted, and each billing page shows no further charges | [hosted] the listing or screenshot text per host in the ledger |
| AC11 | ZAP baseline against the chosen host, with the probe off: no FAIL; each WARN fixed or listed in `deploy/zap/` with its reason. Before the first scan, the host's policy on security testing of your own service is read and quoted in the ledger | [CI] ZAP report summary; ledger |
| AC12 | The spike's real hosted spend is recorded per host against the $10 budget and the main plan's cost estimate; the main plan's infrastructure rows ("Cloud Run free tier: UNCONFIRMED", the 1–2 GB machine price) are replaced with the sourced figures | ledger; main plan diff |
| AC13 | If the lab probe is chosen: it is mounted only when `RAGLAB_LAB_PROBE=1`, is 404 by default, and is off in every config file; the S3 API tests still pass | `test_lab_probe.py`; **break:** mount it unconditionally and the test fails |
| AC14 | Docs: ARCHITECTURE and README mark S3h done; a CHANGELOG line; `deploy/HOSTS.md` with the bootstrap steps for the kept host; the ledger; `make check` passes | `test_diagram.py`; `make check`; review |

## How it will run

1. **Bootstrap (you):** the sign-ups and billing set-up in your go, then the one-time host set-up
   from `deploy/HOSTS.md` (Fly app, Workload Identity pool, Render service), in your browser or
   CLIs you install.
2. **Build (developer, Opus 5.5):** the image job, the deploy workflow, the probe if chosen, and
   the host config in `deploy/`. Then the measurements, the ADR and the teardown.
3. **Judge (Fable 5.1, separate clone):** re-runs AC3, AC6 (a few cold starts per host) and AC7,
   checks every ADR number against the measurements file, tries to break AC4 (an unpinned action,
   `id-token: write` at the top) and AC13, then restores them. Adds a `/security-review` pass.
4. **Fix rounds:** at most two. Product choices come back to you.

**Hosted spend:** only the hosts in your go, within the spike budget. No model provider calls.

## Cost and teardown risks

- **Fly bills without alerts.** Stopped Machines still bill rootfs, volumes bill while detached,
  and managed services outlive deleted apps [F1, F4]. The spike creates no volume or managed
  service, and teardown checks the dashboard.
- **Cloud Run leftovers.** Deleting the service leaves Artifact Registry images (billed above
  0.5 GiB [G16]), secrets and the Workload Identity pool. Teardown deletes the project if Cloud
  Run is not chosen. The spend cap pauses only Cloud Run, not registry storage, logging or
  egress, and enforcement lags [G11].
- **Cloud Run max instances can be exceeded briefly** [G13], so "one instance" is a setting, not
  a guarantee.
- **Render Free can restart at any time** and is suspended when the 750 hours or the bandwidth
  run out without a payment method [R1]. If the image does not fit in 512 MB, Render's next
  option is $25/month always on [R2].
- **Fly trial limits** (2 VM hours, 7 days, auto-stop after 5 minutes) may end mid-spike [F2];
  the apps then stop until a card is added.
- **Credential sprawl.** Three hosts mean a deploy hook, a deploy token, a GHCR pull credential
  and a Workload Identity pool. Each is listed in the ledger when created and checked as revoked
  in AC10.
- **Security testing policy.** ZAP baseline is a passive scan, but each host's policy is read
  before the first scan (AC11).
- **Public URL.** The fake model answers from the planted corpus only, with the input guards
  from S3. Nothing secret is served, but the URL is public until teardown.

## Decisions needed

| # | Decision | Options | My recommendation |
|---|---|---|---|
| D1 | Which hosts to sign up for | any 2 or 3 of Render Free, Fly.io, Cloud Run | **all three:** Cloud Run (the likely keeper on paper), Render Free (the card-free control) and Fly in its trial |
| D2 | Card on file | Cloud Run needs a billing account; Fly needs a card after the trial or if kept; Render Free needs none | a card for Cloud Run only, with a Cloud Run spend cap budget; Fly stays card-free in its trial, and a card is added only if Fly is chosen |
| D3 | Regions | Cloud Run: europe-west1 Belgium or europe-west4 Netherlands (Tier 1, domain mapping available) or europe-west2 London (Tier 2, no domain mapping). Fly: lhr, ams or fra. Render: Frankfurt (the only EU region) | Cloud Run europe-west1, Fly lhr, Render Frankfurt |
| D4 | Required reviewers while private | (a) make the repo public before the deploy job lands (GO-PUBLIC.md first); (b) keep it private and mark AC5 blocked until go-public; (c) a GitHub plan that offers required reviewers on private repositories. Also: which GitHub plan is the account on? Environment secrets on a private repository need a paid plan [GH1] | (b), unless go-public is near |
| D5 | Lab probe | the probe route (AC13), or host metrics and logs only | the probe |
| D6 | Spike budget | $10, or another figure | $10 |
| D7 | The plan | approve, or changes first | — |

## Sources (all fetched 2026-10-18)

- [R1] Render, Free instances: https://render.com/docs/free
- [R2] Render, pricing: https://render.com/pricing
- [R3] Render, deploy hooks: https://render.com/docs/deploy-hooks
- [R4] Render, deploying an image: https://render.com/docs/deploying-an-image
- [R5] Render API, authentication: https://api-docs.render.com/reference/authentication
- [R6] Render, OpenID Connect: https://render.com/docs/oidc
- [R7] Render, regions: https://render.com/docs/regions
- [R8] Render, environment variables and secrets: https://render.com/docs/configure-environment-variables
- [R9] Render, logging: https://render.com/docs/logging
- [R10] Render, custom domains: https://render.com/docs/custom-domains
- [R11] Render feedback thread (community, not docs): https://feedback.render.com/features/p/send-the-correct-xforwardedfor
- [F1] Fly.io, resource pricing: https://docs.fly.io/about/pricing
- [F2] Fly.io, free trial: https://docs.fly.io/about/free-trial
- [F3] Fly.io, billing: https://docs.fly.io/about/billing
- [F4] Fly.io, cost management: https://docs.fly.io/about/cost-management
- [F5] Fly.io, regions: https://docs.fly.io/reference/regions
- [F6] Fly.io, autostop/autostart: https://docs.fly.io/launch/autostop-autostart
- [F7] Fly.io, suspend and resume: https://docs.fly.io/reference/suspend-resume
- [F8] Fly.io, request headers: https://docs.fly.io/networking/request-headers
- [F9] Fly.io, access tokens: https://docs.fly.io/security/tokens
- [F10] Fly.io, continuous deployment with GitHub Actions: https://docs.fly.io/launch/continuous-deployment-with-github-actions
- [F11] Fly.io, secrets: https://docs.fly.io/apps/secrets
- [F12] Fly.io, logging overview: https://docs.fly.io/monitoring/logging-overview
- [F13] Fly.io, custom domains: https://docs.fly.io/networking/custom-domain
- [F14] Fly.io, using the Fly Docker registry: https://docs.fly.io/blueprints/using-the-fly-docker-registry
- [F15] Fly.io, OpenID Connect: https://docs.fly.io/reference/openid-connect
- [G1] Cloud Run pricing: https://cloud.google.com/run/pricing
- [G2] Google Cloud Free Tier and Free Trial: https://cloud.google.com/free/docs/free-cloud-features
- [G3] Cloud Run, memory limits: https://cloud.google.com/run/docs/configuring/services/memory-limits
- [G4] Cloud Run, CPU limits: https://cloud.google.com/run/docs/configuring/services/cpu
- [G5] Cloud Run, container runtime contract: https://cloud.google.com/run/docs/container-contract
- [G6] Cloud Run, mapping custom domains: https://cloud.google.com/run/docs/mapping-custom-domains
- [G7] Cloud Run, deploying container images: https://cloud.google.com/run/docs/deploying
- [G8] Cloud Run, secrets: https://cloud.google.com/run/docs/configuring/services/secrets
- [G9] Cloud Run, logging: https://cloud.google.com/run/docs/logging
- [G10] Cloud Billing, budgets: https://docs.cloud.google.com/billing/docs/how-to/budgets
- [G11] Cloud Billing, spend cap budgets: https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps
- [G12] Cloud Run, general tips: https://cloud.google.com/run/docs/tips/general
- [G13] Cloud Run, maximum instances: https://cloud.google.com/run/docs/configuring/max-instances
- [G14] google-github-actions/auth: https://github.com/google-github-actions/auth
- [G15] google-github-actions/deploy-cloudrun: https://github.com/google-github-actions/deploy-cloudrun
- [G16] Artifact Registry pricing: https://cloud.google.com/artifact-registry/pricing
- [GH1] GitHub, deployments and environments: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- [O1] Hugging Face, Spaces overview: https://huggingface.co/docs/hub/spaces-overview
- [O2] Koyeb, pricing: https://www.koyeb.com/pricing
