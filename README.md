# central-nginx-vg-base

Drop-in replacement base image for `jonasal/nginx-certbot`, intended to be used
as the `FROM` image for ODK Central’s `nginx` build.

## What’s included

- Nginx dynamic module: headers-more
- Nginx dynamic module: ModSecurity-nginx (v3)
- `libmodsecurity` runtime library + shared-library dependencies
- OWASP CRS baked into the image at `/etc/modsecurity/crs` (pinned by `CRS_TAG`)

This image does **not** enable ModSecurity by default. Downstream Nginx config
must `load_module` and set `modsecurity on;` + `modsecurity_rules_file ...;`.

## Build artifacts (modules)

This repo builds the module artifacts first (host export), then bakes them into
the final image.

### Versioning via `.env`

Copy `./.env.example` to `./.env` and set:

- `BASE_IMAGE` (e.g. `jonasal/nginx-certbot:6.0.1`)
- `CRS_TAG` (e.g. `v4.21.0`)
- `IMAGE` and `TAG`
- `PLATFORMS`

```bash
python3 ./scripts/build_artifacts.py
```

Artifacts are exported under `./vg-modules/` and are intentionally untracked.

## Build (and optionally push) the base image

```bash
# local build
IMAGE=drguptavivek/central-nginx-vg-base TAG=6.0.1 PLATFORMS=linux/arm64 python3 ./scripts/build_image.py

# build + push multi-arch
IMAGE=drguptavivek/central-nginx-vg-base TAG=6.0.1 PUSH=1 python3 ./scripts/build_image.py
```

## Using in ODK Central

In Central’s `nginx.dockerfile`, replace:

```dockerfile
FROM jonasal/nginx-certbot:6.0.1
```

with:

```dockerfile
ARG BASE_IMAGE=drguptavivek/central-nginx-vg-base:6.0.1
FROM ${BASE_IMAGE}
```

## Updating CRS

Bake a different CRS tag by building with:

```bash
CRS_TAG=v4.21.0 TAG=6.0.1 python3 ./scripts/build_image.py
```

You can also override CRS at runtime by bind-mounting a directory over
`/etc/modsecurity/crs` (downstream compose/config).

