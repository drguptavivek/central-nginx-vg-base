# Custom Nginx Builds (VG)

This repo includes VG-specific Dockerfiles to build and package custom Nginx
dynamic modules for multiple platforms (currently `linux/arm64` and
`linux/amd64`).

## What gets built

- `ngx_http_modsecurity_module.so` (ModSecurity-nginx dynamic module)
- `ngx_http_headers_more_filter_module.so` (headers-more dynamic module)

Modules are built as **dynamic modules** and then copied into a runtime image
that installs the required shared-library dependencies.

## Nginx base image compile-time modules (non-default)

The upstream `jonasal/nginx-certbot` image used as `BASE_IMAGE` includes Nginx
compiled with a number of non-default modules (from `nginx -V` configure args).
These are useful building blocks even before VG modules are loaded.

HTTP modules:

- `http_addition`: Adds content before/after responses.
- `http_auth_request`: Subrequest-based auth (external auth service).
- `http_dav`: WebDAV methods (PUT/DELETE/MKCOL) support.
- `http_flv`: FLV pseudo-streaming support.
- `http_gunzip`: Decompress upstream gzipped responses for clients that can’t.
- `http_gzip_static`: Serve precompressed `.gz` files when present.
- `http_mp4`: MP4 pseudo-streaming support.
- `http_random_index`: Random directory index selection.
- `http_realip`: Replace client IP based on trusted proxy headers.
- `http_secure_link`: Secure links via hash/timestamp validation.
- `http_slice`: Split range requests into subrequests (large file caching).
- `http_ssl`: TLS/HTTPS support (enables `ssl` directives).
- `http_stub_status`: Exposes Nginx internal metrics via `stub_status`.
- `http_sub`: Response body substitution (string replace).
- `http_v2`: HTTP/2 support.
- `http_v3`: HTTP/3 (QUIC) support.

Mail modules:

- `mail`: IMAP/POP3/SMTP proxy module.
- `mail_ssl`: TLS support for the mail proxy.

Stream (TCP/UDP) modules:

- `stream`: Generic TCP/UDP proxying and load balancing.
- `stream_realip`: Preserve/restore client IP information in stream contexts.
- `stream_ssl`: TLS termination and passthrough helpers for stream.
- `stream_ssl_preread`: Route based on SNI/ALPN without terminating TLS.

## Build the module artifacts (local export)

The `nginx.vg-base.dockerfile` contains `scratch` “out-*” stages that export
artifacts under `/out/...`. When using `--output type=local`, Buildx will create
a local directory that includes an `out/` folder at its root.

### arm64

```bash
docker buildx build --no-cache --platform linux/arm64 \
  -f nginx.vg-base.dockerfile \
  --target out-modsecurity \
  --output type=local,dest=./vg-modules/linux-arm64/out-modsecurity \
  .

docker buildx build --no-cache --platform linux/arm64 \
  -f nginx.vg-base.dockerfile \
  --target out-headers-more \
  --output type=local,dest=./vg-modules/linux-arm64/out-headers-more \
  .
```

### amd64

```bash
docker buildx build --no-cache --platform linux/amd64 \
  -f nginx.vg-base.dockerfile \
  --target out-modsecurity \
  --output type=local,dest=./vg-modules/linux-amd64/out-modsecurity \
  .

docker buildx build --no-cache --platform linux/amd64 \
  -f nginx.vg-base.dockerfile \
  --target out-headers-more \
  --output type=local,dest=./vg-modules/linux-amd64/out-headers-more \
  .
```

### Expected local layout

```text
vg-modules/
  linux-arm64/
    out-modsecurity/
      out/
        modules/ngx_http_modsecurity_module.so
        lib/libmodsecurity.so*
    out-headers-more/
      out/
        modules/ngx_http_headers_more_filter_module.so
  linux-amd64/
    ...
```

`vg-modules/` is intentionally ignored by git (see `.gitignore`). These are
local build artifacts and can be very large.

## Build the runtime image

The runtime images copy the exported artifacts and install the shared-library
dependencies required for module loading.

### arm64 runtime image

```bash
docker buildx build --platform linux/arm64 \
  -f nginx.vg-base.linux-arm64.dockerfile \
  -t vg-nginx:base-arm64 \
  .
```

### amd64 runtime image

```bash
docker buildx build --platform linux/amd64 \
  -f nginx.vg-base.linux-amd64.dockerfile \
  -t vg-nginx:base-amd64 \
  .
```

## Validate modules load in the image

Create a minimal config that loads the modules and run `nginx -t`.

```bash
cat > /tmp/vg-nginx-module-test.conf <<'CONF'
load_module /usr/lib/nginx/modules/ngx_http_headers_more_filter_module.so;
load_module /usr/lib/nginx/modules/ngx_http_modsecurity_module.so;

events {}
http { server { listen 8080; return 200 "ok\n"; } }
CONF

docker run --rm \
  -v /tmp/vg-nginx-module-test.conf:/tmp/nginx.conf:ro \
  vg-nginx:base-arm64 nginx -t -c /tmp/nginx.conf

docker run --rm --platform linux/amd64 \
  -v /tmp/vg-nginx-module-test.conf:/tmp/nginx.conf:ro \
  vg-nginx:base-amd64 nginx -t -c /tmp/nginx.conf
```

If successful, Nginx prints `test is successful`. The ModSecurity module also
prints its version banner during config test.

## Logging in the base image

The `BASE_IMAGE` (`jonasal/nginx-certbot:6.0.1`) configures Nginx to log to
`/var/log/nginx/*` by default:

- Access log: `/var/log/nginx/access.log` using `log_format main ...`
- Error log: `/var/log/nginx/error.log` at `notice` level

However, in this base image those log files are symlinked to stdout/stderr:

- `/var/log/nginx/access.log -> /dev/stdout`
- `/var/log/nginx/error.log -> /dev/stderr`

This is convenient for `docker logs`, but it means logs are not persisted as
normal files unless you reconfigure them.

### Persist logs to a shared volume (recommended)

For cross-platform deployments (macOS/Windows dev + Ubuntu deploy) and for tools
that need to tail log files (CrowdSec/Fall2ban, debugging, audits), configure
Nginx and ModSecurity to write to a real directory and mount it as a named
volume in Docker Compose.

Current VG convention:

- One shared volume mounted at `/var/log/odk`
  - Nginx logs: `/var/log/odk/nginx/access.log`, `/var/log/odk/nginx/error.log`
  - ModSecurity audit log: `/var/log/odk/modsecurity/audit.log`

The config lives in `/etc/nginx/nginx.conf` and includes `/etc/nginx/conf.d/*.conf`
(the image ships with `/etc/nginx/conf.d/redirector.conf` for HTTP→HTTPS redirect
and ACME challenge handling).

## Troubleshooting

### `ngx_http_modsecurity_module requires the ModSecurity library`

This usually means the build stage that compiles the Nginx module can’t find
`libmodsecurity` headers/libs during `./configure`. Ensure the module build
stage includes the ModSecurity install and that `ldconfig` has been run.

### `dlopen() ... libcurl.so.4: cannot open shared object file`

This indicates the runtime image is missing shared-library dependencies required
by `libmodsecurity`. Install the required runtime libs in the runtime Dockerfile
and run `ldconfig`.

### Can we just `apt install libmodsecurity3`?

Not with the current `BASE_IMAGE` (`jonasal/nginx-certbot:6.0.1`): the Debian
repositories available inside that image do not provide `libmodsecurity3`
(`apt-cache policy libmodsecurity3` shows `Candidate: (none)`). For now, the
runtime image must copy `libmodsecurity.so*` from the build artifacts (and
install its shared-library dependencies).

### CrowdSec / Fail2ban integration notes (Docker Compose)

Bundling host-style intrusion prevention (Fail2ban / CrowdSec bouncers) directly
into the Nginx runtime image is not currently practical with this base image:

- No firewall tooling in the base image (`ufw`, `iptables`, `nft` are not present
  by default).
- The CrowdSec Nginx bouncer relies on Nginx Lua support (`libnginx-mod-http-lua`)
  which is not installable alongside the Nginx version shipped in
  `jonasal/nginx-certbot:6.0.1` due to ABI/version constraints.

Recommended approach:

- Keep the Nginx runtime image focused on Nginx + modules.
- Run CrowdSec (and any bouncers) as separate services in Docker Compose, and
  enforce decisions at the edge (cloud/LB) or on the host (firewall bouncer),
  rather than inside the Nginx container.

### Cross-platform notes

- Nginx and modules must match architecture (`linux/arm64` vs `linux/amd64`).
- Use `--platform` consistently for both artifact build and runtime build.
