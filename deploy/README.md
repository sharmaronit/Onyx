# Onyx cloud deployment

This deployment exposes one stable HTTPS hostname through Caddy. FastAPI stays on the private Docker network; only Caddy binds public ports. Caddy obtains and renews the TLS certificate after the domain points at the VM.

1. Create an Ubuntu VM and allow inbound TCP 22 from administrator IPs, plus TCP 80/443 and UDP 443 from the internet.
2. Install Docker Engine and its Compose plugin. Clone this repository to `/opt/onyx`.
3. Copy `.env.example` to `.env`, then set the domain, customer organization ID, and a generated administrator key.
4. Run `docker compose --env-file .env -f compose.yaml up -d --build` from this directory.
5. Verify `https://your-domain/api/health/ready`, then create a 15-minute enrollment token through the authenticated administrator API.
6. Schedule `backup.sh` daily, copy encrypted backups off the VM, and test a restore before the pilot.

Use one VM and data volume per pilot customer. The current SQLite store is suitable for the initial 10–25 device pilot on durable storage. Do not run several API replicas against this file. PostgreSQL remains a required migration before scaling beyond a single API process.
