# Onyx supervised paid-pilot scope

## Offer

Onyx helps an office administrator see which company devices need attention, assign the required work, and verify that the work was completed.

The initial deployment is one customer, one isolated Onyx service and database, one administrator group, and 10–25 authorized Windows 10/11 devices. It is read-only: inventory, evidence collection, findings, recommendations, and human-reviewed reports. Endpoint response controls remain disabled.

## Data and operation

- Collected fields: endpoint ID, hostname, platform/version, agent version, last heartbeat, approved network relationships, Microsoft Defender event metadata, imported vulnerability findings, and remediation evidence.
- Default retention proposal: 30 days for raw telemetry and 12 months for audit and remediation outcomes. The customer must approve or change this before installation.
- Support proposal: business hours in the customer's agreed timezone, with a named escalation contact and a one-business-day response target during the pilot.
- Uninstall must remove the scheduled task/service, local Onyx files and credentials, and any Onyx-created firewall rules. The administrator verifies removal from both device and console.

## Success measures

- At least 95% of authorized devices enroll successfully without reusable credentials in the installer.
- At least 95% of enrolled devices report within the agreed freshness window during business hours.
- Onyx reduces the administrator's measured weekly triage and follow-up time.
- Each accepted action has an owner and due date; completed actions obtain new evidence or authorized human verification.
- Recommendations are tracked as accepted, rejected, incorrect, or unverifiable.
- The customer makes an explicit renewal or purchase decision at the end of the paid pilot.

## Exclusions

The pilot does not promise antivirus, EDR, MDM, autonomous response, autonomous patching, zero-day discovery, 24/7 incident response, calibrated breach probability, or blockchain functionality. Attack simulation is a separate research feature using synthetic environments.

No employee device should be enrolled until the launch checklist in `ONYX_REMEDIATION_PLAN.md` passes and the customer has approved collected fields, retention, support, and uninstall procedures.
