//! Tauri backend for the pill.ai Orb.
//!
//! All LLM work happens in the Python sidecar (pill_ai/orb.py running on
//! localhost:7842).  This crate only owns three thin commands:
//!   - chat        → POST /chat to the Python backend
//!   - resize_window → resize the transparent Tauri window
//!   - start_drag  → native OS window drag

use tauri::Manager;

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
        .invoke_handler(tauri::generate_handler![chat, resize_window, start_drag])
        .run(tauri::generate_context!())
        .expect("error while running pill.ai orb");
}
