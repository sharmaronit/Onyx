use serde_json::{json, Value};
use std::io::{Read, Write};
use tauri::{menu::{Menu, MenuItem}, tray::TrayIconBuilder, Manager};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};

fn local_request(request: &Value) -> Result<Value, String> {
    let mut payload = serde_json::to_vec(request).map_err(|e| e.to_string())?;
    payload.push(b'\n');
    #[cfg(windows)]
    let mut stream = std::fs::OpenOptions::new().read(true).write(true).open(r"\\.\pipe\onyx-agent-v1").map_err(|e| format!("Onyx background service is unavailable: {e}"))?;
    #[cfg(unix)]
    let mut stream = std::os::unix::net::UnixStream::connect("/var/run/onyx-agent-v1.sock").map_err(|e| format!("Onyx background service is unavailable: {e}"))?;
    stream.write_all(&payload).map_err(|e| e.to_string())?;
    let mut response = Vec::new();
    stream.take(1024 * 1024).read_to_end(&mut response).map_err(|e| e.to_string())?;
    serde_json::from_slice(&response).map_err(|e| format!("Invalid response from Onyx service: {e}"))
}

#[tauri::command]
fn agent_request(request: Value) -> Result<Value, String> { local_request(&request) }

#[tauri::command]
fn export_diagnostics() -> Result<Option<String>, String> {
    let reply = local_request(&json!({"command": "diagnostics"}))?;
    if !reply.get("ok").and_then(Value::as_bool).unwrap_or(false) {
        return Err(reply.get("error").and_then(Value::as_str).unwrap_or("Diagnostics unavailable").to_string());
    }
    let Some(path) = rfd::FileDialog::new().set_file_name("onyx-agent-diagnostics.json").save_file() else { return Ok(None); };
    let content = serde_json::to_string_pretty(reply.get("diagnostics").unwrap_or(&Value::Null)).map_err(|e| e.to_string())?;
    std::fs::write(&path, content).map_err(|e| e.to_string())?;
    Ok(Some(path.to_string_lossy().into_owned()))
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, None))
        .setup(|app| {
            let show = MenuItem::with_id(app, "show", "Open Onyx", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;
            let mut builder = TrayIconBuilder::new().menu(&menu).show_menu_on_left_click(false);
            if let Some(icon) = app.default_window_icon() { builder = builder.icon(icon.clone()); }
            builder.on_menu_event(|app, event| match event.id.as_ref() {
                "show" => { if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); } },
                "quit" => app.exit(0),
                _ => {}
            }).build(app)?;
            let _ = app.autolaunch().enable();
            Ok(())
        })
        .on_window_event(|window, event| if let tauri::WindowEvent::CloseRequested { api, .. } = event { api.prevent_close(); let _ = window.hide(); })
        .invoke_handler(tauri::generate_handler![agent_request, export_diagnostics])
        .run(tauri::generate_context!())
        .expect("error while running Onyx desktop application");
}
