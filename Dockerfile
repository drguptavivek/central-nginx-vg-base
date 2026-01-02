ARG BASE_IMAGE=jonasal/nginx-certbot:6.0.1
FROM ${BASE_IMAGE}

# VG base image: drop-in replacement for jonasal/nginx-certbot with
# ModSecurity + headers-more dynamic modules baked in.
#
# Notes:
# - Requires prebuilt artifacts in the build context under:
#   ./vg-modules/linux-amd64/... and ./vg-modules/linux-arm64/...
# - CRS is baked in at build time from a pinned git tag.

ARG TARGETARCH
ARG CRS_TAG=v4.21.0

RUN mkdir -p /usr/lib/nginx/modules /etc/modsecurity /etc/modsecurity/crs

# Dynamic modules + libmodsecurity from prebuilt artifacts.
COPY vg-modules/linux-${TARGETARCH}/out-headers-more/out/ngx_http_headers_more_filter_module.so /usr/lib/nginx/modules/
COPY vg-modules/linux-${TARGETARCH}/out-modsecurity/out/modules/ngx_http_modsecurity_module.so /usr/lib/nginx/modules/
COPY vg-modules/linux-${TARGETARCH}/out-modsecurity/out/lib/libmodsecurity.so* /usr/local/lib/

# ModSecurity recommended base config + unicode mapping (CRS rules are added below).
COPY vg-modules/linux-${TARGETARCH}/out-modsecurity/out/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf-recommended
COPY vg-modules/linux-${TARGETARCH}/out-modsecurity/out/modsecurity/unicode.mapping /etc/modsecurity/unicode.mapping

# Runtime deps for libmodsecurity + module loading.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        libcurl4 \
        libgeoip1 \
        liblmdb0 \
        libpcre2-8-0 \
        libxml2 \
        libyajl2 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

# Bake OWASP CRS from a pinned git tag.
RUN git clone --depth 1 --branch "${CRS_TAG}" https://github.com/coreruleset/coreruleset.git /tmp/coreruleset \
    && cp -R /tmp/coreruleset/rules /etc/modsecurity/crs/owasp-crs-rules \
    && cp /tmp/coreruleset/crs-setup.conf.example /etc/modsecurity/crs/owasp-crs-setup.conf \
    && rm -rf /tmp/coreruleset

