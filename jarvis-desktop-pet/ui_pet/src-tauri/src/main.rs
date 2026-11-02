#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{
    CustomMenuItem, Manager, PhysicalPosition, RunEvent, SystemTray, SystemTrayEvent,
    SystemTrayMenu, SystemTrayMenuItem, WindowEvent,
};

struct BackendChild(Mutex<Option<std::process::Child>>);

// What the titlebar close / Alt+F4 does (docs/35 L5): hide to the tray (the
// default) or quit everything. The main window sets it from Settings.
static CLOSE_TO_TRAY: AtomicBool = AtomicBool::new(true);
static TRAY_HINT_SHOWN: AtomicBool = AtomicBool::new(false);

// Single instance (docs/35 L3/L4): the first instance owns this loopback port.
// A second launch connects, asks it to show the main window, and exits before
// creating any window or spawning a second backend.
const INSTANCE_ADDR: &str = "127.0.0.1:47823";
const INSTANCE_HELLO: &[u8] = b"jarvis-show";

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

fn hidden_command(program: &str) -> std::process::Command {
    #[allow(unused_mut)]
    let mut cmd = std::process::Command::new(program);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    cmd
}

// The PyInstaller backend is a bootloader plus a child process, so killing the
// handle we hold would orphan the real backend: end the whole tree instead.
fn stop_backend(app: &tauri::AppHandle) {
    let child = app.state::<BackendChild>().0.lock().unwrap().take();
    if let Some(mut child) = child {
        let pid = child.id().to_string();
        let _ = hidden_command("taskkill").args(["/PID", &pid, "/T", "/F"]).status();
        let _ = child.kill();
        let _ = child.wait();
    }
}

fn quit_app(app: &tauri::AppHandle) {
    stop_backend(app);
    app.exit(0);
}

fn hide_main(app: &tauri::AppHandle) {
    if let Some(w) = app.get_window("main") {
        let _ = w.hide();
    }
    if !TRAY_HINT_SHOWN.swap(true, Ordering::SeqCst) {
        // say it where the user is looking: the companion's bubble or the
        // island headline. A Windows toast lands bottom-right on top of the pet.
        let hint = "Still here! Closed to the tray \u{2014} right-click the tray icon to Quit.";
        let pet = app.get_window("pet").filter(|w| w.is_visible().unwrap_or(false));
        let dock = app.get_window("dock").filter(|w| w.is_visible().unwrap_or(false));
        if let Some(w) = pet {
            let _ = w.eval(&format!("window.showBubble && window.showBubble({:?}, 6000)", hint));
        } else if let Some(w) = dock {
            let _ = w.eval(&format!("window.islandHint && window.islandHint({:?})", hint));
        } else {
            let _ = tauri::api::notification::Notification::new(&app.config().tauri.bundle.identifier)
                .title("Jarvis is still running")
                .body("It's in the tray. Right-click the tray icon and choose Quit to exit.")
                .show();
        }
    }
}

fn close_main(app: &tauri::AppHandle) {
    if CLOSE_TO_TRAY.load(Ordering::SeqCst) {
        hide_main(app);
    } else {
        quit_app(app);
    }
}

fn claim_single_instance() -> Option<TcpListener> {
    match TcpListener::bind(INSTANCE_ADDR) {
        Ok(listener) => Some(listener),
        Err(_) => {
            if let Ok(mut stream) = TcpStream::connect_timeout(
                &INSTANCE_ADDR.parse().unwrap(),
                Duration::from_millis(800),
            ) {
                let _ = stream.write_all(INSTANCE_HELLO);
            }
            None
        }
    }
}

fn serve_instance_requests(listener: TcpListener, app: tauri::AppHandle) {
    std::thread::spawn(move || {
        for stream in listener.incoming().flatten() {
            let mut stream = stream;
            let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
            let mut buf = [0u8; 32];
            let n = stream.read(&mut buf).unwrap_or(0);
            if &buf[..n] == INSTANCE_HELLO {
                let handle = app.clone();
                let _ = app.run_on_main_thread(move || open_main_tab(&handle, "chat"));
            }
        }
    });
}

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
        // Windows refuses a plain focus steal from a background process; a
        // brief always-on-top round trip brings the window to the front
        let _ = w.set_always_on_top(true);
        let _ = w.set_always_on_top(false);
        let _ = w.set_focus();
    }
}

fn open_main_tab(app: &tauri::AppHandle, tab: &str) {
    show_window(app, "main");
    if let Some(w) = app.get_window("main") {
        let _ = w.eval(&format!("window.showTab && window.showTab(\"{}\")", tab));
    }
}

// Tauri v1 hides windows without telling the page (document.hidden stays
// false), so the pet is told directly and pauses its renderer (spec 34 7.4)
fn pet_visibility(w: &tauri::Window, visible: bool) {
    let _ = w.eval(&format!(
        "window.setPetVisible && window.setPetVisible({})",
        visible
    ));
}

fn position_pet(tauri_app: &tauri::App) {
    if let Some(w) = tauri_app.get_window("pet") {
        if let Ok(Some(mon)) = w.primary_monitor() {
            let scale = mon.scale_factor();
            let size = mon.size();
            let pos = mon.position();
            let win_w = (360.0 * scale) as i32;
            let win_h = (360.0 * scale) as i32;
            let margin_x = (20.0 * scale) as i32;
            let margin_y = (44.0 * scale) as i32;
            let x = pos.x + (size.width as i32) - win_w - margin_x;
            let y = pos.y + (size.height as i32) - win_h - margin_y;
            let _ = w.set_position(PhysicalPosition::new(x, y));
        }
    }
}

fn position_dock(w: &tauri::Window) {
    if let Ok(Some(mon)) = w.primary_monitor() {
        let scale = mon.scale_factor();
        let size = mon.size();
        let pos = mon.position();
        let dock_w = (240.0 * scale) as i32;
        let x = pos.x + ((size.width as i32) - dock_w) / 2;
        let _ = w.set_position(PhysicalPosition::new(x, pos.y));
    }
}

fn main() {
    let instance = match claim_single_instance() {
        Some(listener) => listener,
        None => return, // another Jarvis is running and has been asked to show itself
    };
    let app = tauri::Builder::default()
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
                "quit" => quit_app(app),
                _ => {}
            },
            SystemTrayEvent::LeftClick { .. } => open_main_tab(app, "chat"),
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![
            open_chat,
            open_settings,
            open_tab,
            set_pet,
            set_companion,
            close_main_window,
            set_close_to_tray,
            quit
        ])
        .setup(move |app| {
            serve_instance_requests(instance, app.handle());
            if let Ok(exe) = std::env::current_exe() {
                if let Some(dir) = exe.parent() {
                    let backend = dir.join("jarvis-backend.exe");
                    if backend.exists() {
                        // the backend watches this pid and exits with us, even on a crash
                        let mut cmd = hidden_command(&backend.to_string_lossy());
                        cmd.current_dir(dir)
                            .env("JARVIS_PARENT_PID", std::process::id().to_string());
                        match cmd.spawn() {
                            Ok(child) => {
                                *app.state::<BackendChild>().0.lock().unwrap() = Some(child);
                            }
                            Err(e) => eprintln!("backend spawn failed: {}", e),
                        }
                    }
                }
            }
            position_pet(app);
            if let Some(w) = app.get_window("dock") {
                position_dock(&w);
            }
            if std::env::args().any(|a| a == "--hidden") {
                if let Some(w) = app.get_window("main") {
                    let _ = w.hide();
                }
            }
            Ok(())
        })
        .on_window_event(|event| {
            if let WindowEvent::CloseRequested { api, .. } = event.event() {
                let label = event.window().label();
                if label == "main" {
                    api.prevent_close();
                    close_main(&event.window().app_handle());
                } else if label == "pet" {
                    api.prevent_close();
                    let _ = event.window().hide();
                    pet_visibility(event.window(), false);
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("error building tauri app");
    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            stop_backend(handle);
        }
    });
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
        pet_visibility(&w, visible);
    }
}

#[tauri::command]
fn set_companion(app: tauri::AppHandle, mode: String) {
    let mode = if mode == "dock" { "dock" } else { "pet" };
    if mode == "dock" {
        if let Some(w) = app.get_window("pet") {
            let _ = w.hide();
            pet_visibility(&w, false);
        }
        match app.get_window("dock") {
            Some(dock) => {
                position_dock(&dock);
                let _ = dock.show();
            }
            None => eprintln!("dock window missing from tauri.conf"),
        }
    } else {
        if let Some(dock) = app.get_window("dock") {
            let _ = dock.hide();
        }
        if let Some(pet) = app.get_window("pet") {
            let _ = pet.show();
            pet_visibility(&pet, true);
        }
    }
    // keep every window's companion state in sync: the main window's settings
    // seg and pet toggle, the pet, which hands approvals to the island, and the
    // island, which wakes from its strip when shown
    for label in ["main", "pet", "dock"] {
        if let Some(w) = app.get_window(label) {
            let _ = w.eval(&format!(
                "window.onCompanionChanged && window.onCompanionChanged(\"{}\")",
                mode
            ));
        }
    }
}

#[tauri::command]
fn open_tab(app: tauri::AppHandle, tab: String) {
    let tab = match tab.as_str() {
        "activity" | "memory" | "settings" => tab,
        _ => "chat".to_string(),
    };
    open_main_tab(&app, &tab);
}

// The titlebar close button: never destroy the main window (a destroyed
// window is why "open chat" stopped working, docs/35 B2); hide or quit.
#[tauri::command]
fn close_main_window(app: tauri::AppHandle) {
    close_main(&app);
}

#[tauri::command]
fn set_close_to_tray(enabled: bool) {
    CLOSE_TO_TRAY.store(enabled, Ordering::SeqCst);
}

#[tauri::command]
fn quit(app: tauri::AppHandle) {
    quit_app(&app);
}
