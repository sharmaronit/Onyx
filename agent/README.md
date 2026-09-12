# Onyx Endpoint Agent

The Onyx Endpoint Agent is a collection-only Windows and macOS service. It reports five-minute heartbeats and a narrow security-event set over HTTPS. It has no remote command polling, firewall changes, quarantine action, Sysmon installation, or TLS-bypass option.

An administrator creates a one-use, 15-minute enrollment token through the Onyx API. On the laptop, run `onyx-agent enroll --server-url https://api.example.com`; the token is entered with masked input. The agent uses a generated UUID endpoint ID, stores its device credential with Windows DPAPI or the macOS System Keychain, and encrypts the on-disk retry queue.

Windows collects Defender Operational event IDs 1116 and 1117. macOS reports an allowlisted Unified Logging subset as `apple_security_log`; it is not presented as Microsoft Defender or complete endpoint detection.

Unsigned builds are only for owned development machines. Employee deployment requires Windows code signing plus Apple Developer ID signing and notarization.
