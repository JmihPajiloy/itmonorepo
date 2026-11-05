FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
RUN apt-get update && apt-get install -y --no-install-recommends \
    tcpdump iproute2 iputils-ping traceroute dnsutils dnsmasq isc-dhcp-client curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pyftpdlib==2.1.0
WORKDIR /lab
CMD ["sleep", "infinity"]
