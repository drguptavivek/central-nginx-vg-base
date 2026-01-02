# Changelog

All notable changes to this project are documented in this file.

## 6.0.1 (2026-01-02)

### Added

- Base image `drguptavivek/central-nginx-vg-base:6.0.1` (multi-arch: `linux/amd64`, `linux/arm64`)
- Dynamic modules baked into `/usr/lib/nginx/modules/`:
  - `ngx_http_headers_more_filter_module.so`
  - `ngx_http_modsecurity_module.so`
- ModSecurity runtime library baked into `/usr/local/lib/`:
  - `libmodsecurity.so*` (from ModSecurity v3.0.14 build artifacts)
- OWASP CRS baked into `/etc/modsecurity/crs` (tag: `v4.21.0`)

### Notes

- Module source pinning is not yet enforced in `Dockerfile.modules` (uses latest `HEAD` from upstream repos at build time).

