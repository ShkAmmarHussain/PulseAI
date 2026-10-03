#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{
    CustomMenuItem, Manager, PhysicalPosition, SystemTray, SystemTrayEvent, SystemTrayMenu,
    SystemTrayMenuItem, WindowEvent,
};

struct BackendChild(Mutex<Option<std::process::Child>>);

fn tray_menu() -> SystemTrayMenu {
    SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("open_main", "Open Jarvis"))
        .add_item(CustomMenuItem::new("open_settings", "Settings"))
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(CustomMenuItem::new("toggle_pet", "Show / Hide Pet"))
        .add_item(CustomMenuItem::new("quit", "Quit"))
}

fn show_window(app: &tauri::AppHandle, label: &str) {
    if let Some(w) = app.get_window(label) {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
}

fn open_main_tab(app: &tauri::AppHandle, tab: &str) {
    show_window(app, "main");
    if let Some(w) = app.get_window("main") {
        let _ = w.eval(&format!("window.showTab && window.showTab(\"{}\")", tab));
    }
}

fn position_pet(tauri_app: &tauri::App) {
    if let Some(w) = tauri_app.get_window("pet") {
        if let Ok(Some(mon)) = w.primary_monitor() {
            let scale = mon.scale_factor();
            let size = mon.size();
            let pos = mon.position();
            let win_w = (300.0 * scale) as i32;
            let win_h = (240.0 * scale) as i32;
            let margin_x = (20.0 * scale) as i32;
            let margin_y = (44.0 * scale) as i32;
            let x = pos.x + (size.width as i32) - win_w - margin_x;
            let y = pos.y + (size.height as i32) - win_h - margin_y;
            let _ = w.set_position(PhysicalPosition::new(x, y));
        }
    }
}

fn main() {
    tauri::Builder::default()
        .manage(BackendChild(Mutex::new(None)))
        .system_tray(SystemTray::new().with_menu(tray_menu()))
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "open_main" => open_main_tab(app, "chat"),
                "open_settings" => open_main_tab(app, "settings"),
                "toggle_pet" => {
                    if let Some(w) = app.get_window("main") {
                        let _ = w.eval("window.togglePetFromTray && window.togglePetFromTray()");
                    }
                }
                "quit" => std::process::exit(0),
                _ => {}
            },
            SystemTrayEvent::LeftClick { .. } => open_main_tab(app, "chat"),
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![open_chat, open_settings, set_pet])
        .setup(|app| {
            if let Ok(exe) = std::env::current_exe() {
                if let Some(dir) = exe.parent() {
                    let backend = dir.join("jarvis-backend.exe");
                    if backend.exists() {
                        match std::process::Command::new(&backend).current_dir(dir).spawn() {
                            Ok(child) => {
                                *app.state::<BackendChild>().0.lock().unwrap() = Some(child);
                            }
                            Err(e) => eprintln!("backend spawn failed: {}", e),
                        }
                    }
                }
            }
            position_pet(app);
            Ok(())
        })
        .on_window_event(|event| {
            if let WindowEvent::CloseRequested { api, .. } = event.event() {
                let label = event.window().label();
                if label == "main" || label == "pet" {
                    api.prevent_close();
                    let _ = event.window().hide();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error running tauri app");
}

#[tauri::command]
fn open_chat(app: tauri::AppHandle) {
    open_main_tab(&app, "chat");
}

#[tauri::command]
fn open_settings(app: tauri::AppHandle) {
    open_main_tab(&app, "settings");
}

#[tauri::command]
fn set_pet(app: tauri::AppHandle, visible: bool) {
    if let Some(w) = app.get_window("pet") {
        if visible {
            let _ = w.show();
        } else {
            let _ = w.hide();
        }
    }
}
