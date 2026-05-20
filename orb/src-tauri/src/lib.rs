use tauri::Manager;

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

#[tauri::command]
async fn resize_window(app: tauri::AppHandle, width: f64, height: f64) -> Result<(), String> {
    if let Some(win) = app.get_webview_window("orb") {
        win.set_size(tauri::LogicalSize::new(width, height))
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

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
