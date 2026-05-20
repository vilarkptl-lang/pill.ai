//! Tauri backend for the pill.ai Orb.
//!
//! Commands:
//!   - chat          → POST /chat to Python backend (localhost:7842)
//!   - resize_window → resize the transparent window
//!   - start_drag    → native OS drag
//!   - check_update  → poll relay /version, return update info if newer

use tauri::Manager;

/// Poll relay /version and return update info if a newer version exists.
#[tauri::command]
async fn check_update(relay_url: String) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(6))
        .build()
        .map_err(|e| e.to_string())?;

    let data: serde_json::Value = client
        .get(format!("{}/version", relay_url.trim_end_matches('/')))
        .send()
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())?;

    Ok(data)
}

/// Forward a chat message to the Python backend and return the assistant reply.
#[tauri::command]
async fn chat(message: String) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(120))
        .build()
        .map_err(|e| e.to_string())?;

    let resp = client
        .post("http://127.0.0.1:7842/chat")
        .json(&serde_json::json!({ "message": message }))
        .send()
        .await
        .map_err(|e| format!("Backend no disponible — ¿corriste 'pillai orb'? ({e})"))?;

    if !resp.status().is_success() {
        return Err(format!("Backend error: {}", resp.status()));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data["content"].as_str().unwrap_or("").to_string())
}

/// Resize the orb window (collapse ↔ expand).
#[tauri::command]
async fn resize_window(app: tauri::AppHandle, width: f64, height: f64) -> Result<(), String> {
    if let Some(win) = app.get_webview_window("orb") {
        win.set_size(tauri::LogicalSize::new(width, height))
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Initiate native OS window drag from the current cursor position.
#[tauri::command]
async fn start_drag(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(win) = app.get_webview_window("orb") {
        win.start_dragging().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            chat,
            resize_window,
            start_drag,
            check_update,
        ])
        .run(tauri::generate_context!())
        .expect("error while running pill.ai orb");
}
