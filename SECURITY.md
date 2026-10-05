# Security policy

## Reporting a vulnerability

Please **do not open a public issue**. Open a private security advisory instead:
GitHub → this repository → **Security** → **Report a vulnerability**.

Include what you found, how to reproduce it, and what an attacker could do with it. You'll get an
answer in the advisory thread; fixes are released before details are made public.

## Supported versions

Only the latest commit on `main` is supported. There are no maintained release branches: update
to the current `main` (and rebuild the image) to get security fixes.

## Hardening checklist for operators

- **HTTPS.** Set `SITE_ADDRESS` to a domain name pointing at the server. Caddy then gets a
  certificate automatically and accepts only TLS 1.2 and 1.3. Plain HTTP (`:80`) is only for a
  closed office network.
- **Firewall.** Open only 443 (and 80, which Caddy uses to redirect to HTTPS and to obtain the
  certificate). Never expose the gateway's port 8080: it trusts the client address Caddy reports,
  so anyone who can reach it directly from a private address can claim to be inside the office.
- **Behind another load balancer** (cloud load balancer, CDN, a second proxy): every visitor then
  arrives from that balancer's private address. Set `PUBLIC_DEPLOY=1`, so "private address" no
  longer means "inside the office" and the admin page always asks for `ADMIN_PASSWORD`.
- **Open access** (`OPEN_ACCESS=1`) lets anyone inside pick any name. Turn it off once real users
  exist.
- **Backups.** Everything the gateway writes is in the data volume (`/data`: database, its
  encryption key file, backups). Encrypt backups of it, and keep a copy of the key file **separately**
  from the database backups: without the key the encrypted data can't be read, and with both in one
  place the encryption protects nothing.
- **Disk encryption** of the server (LUKS, BitLocker, cloud-volume encryption) is optional but adds a
  layer if a disk or snapshot leaks.
- **Provider keys.** Rotate the AI provider API keys periodically and immediately if `.env` may have
  leaked. Give each key a spending limit at the provider.
- **Cloud permissions.** The server's cloud identity needs no rights beyond running itself: no
  storage-wide, IAM or billing permissions.
- **Network segmentation.** The gateway needs outbound access only to the AI providers
  (`api.anthropic.com`, `api.openai.com`, `generativelanguage.googleapis.com`) and to the company MCP
  servers it is configured to use. Block everything else outbound at the firewall, and keep it off
  networks it has no reason to reach.
- **Updates.** Rebuild the image regularly (`docker compose build --pull && docker compose up -d`):
  base image and Python packages are pinned by digest and hash, and Dependabot proposes updates.

## Build integrity

- Python packages are installed from `requirements.txt` with exact versions and SHA-256 hashes
  (`pip install --require-hashes`); a tampered or substituted package fails the build.
- The base image is pinned by digest; GitHub Actions are pinned by full commit SHA.
- CI runs the tests, `pip-audit` (known vulnerabilities in dependencies) and `gitleaks` (secrets in
  git history). The Docker workflow builds the image, scans it with Trivy (fails on fixable CRITICAL
  issues) and uploads an SBOM (list of everything in the image) as a build artifact.
- The image is not published to any registry yet. When it is, sign it with
  [cosign](https://github.com/sigstore/cosign) keyless signing so users can verify it came from this
  repository's workflow: give the publishing job `permissions: id-token: write` and
  `packages: write`, push, then run `cosign sign --yes <registry>/<image>@<digest>` and attach the
  SBOM with `cosign attest --yes --type spdxjson --predicate firegate-sbom.spdx.json <image>@<digest>`.
  Users verify with `cosign verify <image>@<digest> --certificate-identity-regexp
  'https://github.com/tomerdamari/firegate/' --certificate-oidc-issuer https://token.actions.githubusercontent.com`.
