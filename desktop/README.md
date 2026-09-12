# Onyx desktop companion

This Tauri application is the employee-facing status and enrollment UI. It talks only to the privileged Onyx background service through `\\.\pipe\onyx-agent-v1` on Windows or `/var/run/onyx-agent-v1.sock` on macOS. The device credential is never returned to the UI.

For frontend development, run `npm install` and `npm run dev`. A complete desktop build also requires the Rust toolchain and the Tauri platform prerequisites, then `npm run tauri build`.
