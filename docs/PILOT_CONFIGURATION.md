# Pilot configuration

Use a separate service instance, database file, hostname, secrets, and artifact directory for each customer. Onyx does not currently support a shared multi-tenant deployment.

Required environment values for a supervised pilot:

```text
ONYX_ORGANIZATION_ID=<stable-customer-id>
ONYX_ADMIN_API_KEY=<random-admin-api-secret>
ONYX_TELEMETRY_INGEST_API_KEY=<scanner-ingest-secret>
ONYX_ALLOW_LEGACY_SHARED_AGENT_KEY=false
ONYX_EXPECTED_DEVICE_COUNT=<approved-device-count>
ONYX_MINIMUM_COVERAGE=0.80
ONYX_HEARTBEAT_FRESH_SECONDS=300
ONYX_HEARTBEAT_STALE_SECONDS=86400
ONYX_RESPONSE_CONTROLS_ENABLED=false
```

The response flag must remain false for the read-only pilot. `ONYX_ENABLE_TRAINED_AGENT` also defaults to false so a stale or incompatible checkpoint cannot silently change customer output.

`ONYX_ADMIN_API_KEY` protects remediation workflow writes and exports. It is an interim isolated-pilot control, not the planned OIDC implementation. Put the API behind authenticated HTTPS and do not expose FastAPI directly to the internet.

Issue one short-lived enrollment token per device through `POST /api/device-enrollment/tokens`, then exchange it once through `POST /api/device-enrollment/exchange`. Only a hash of the resulting device credential is stored. The credential is bound to one endpoint ID and can be revoked through `POST /api/devices/{endpoint_id}/revoke`.

Secret rotation, Windows protected secret storage, signed packages, tested backup/restore, and OIDC remain mandatory before the pilot launch checklist can be approved.

On Windows PowerShell installations that block `npx.ps1`, use the command shims directly:

```powershell
cd web
.\node_modules\.bin\tsc.cmd --noEmit
npm.cmd run lint
npm.cmd run build
```

For the repository's validated local Python environment, use `.runtime-python310\python.exe`. Recreate it with CPython 3.10 if it is absent; the checked-in `.venv` path must not be assumed valid.
