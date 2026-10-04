//! jarvis-hook: named-pipe relay between terminal coding agents and Jarvis
//! (spec 29, sections 4 + 7.2).
//!
//! Contract: NEVER stall the terminal agent. Connect attempts are bounded by a
//! 300ms WaitNamedPipe timeout, every failure path exits 0, and the blocking
//! approval roundtrip carries a hard watchdog.

use serde_json::{json, Value};
use std::io::Read;
use std::process;

const PIPE: &str = r"\\.\pipe\jarvis-hook";
const WAIT_MS: u32 = 300;

#[link(name = "kernel32")]
extern "system" {
    fn WaitNamedPipeW(lp_named_pipe_name: *const u16, n_time_out: u32) -> i32;
    fn CreateFileW(
        lp_file_name: *const u32,
        dw_desired_access: u32,
        dw_share_mode: u32,
        lp_security_attributes: *const u8,
        dw_creation_disposition: u32,
        dw_flags_and_attributes: u32,
        h_template_file: *const u8,
    ) -> isize;
    fn WriteFile(
        h_file: isize,
        lp_buffer: *const u8,
        n_number_of_bytes_to_write: u32,
        lp_number_of_bytes_written: *mut u32,
        lp_overlapped: *const u8,
    ) -> i32;
    fn ReadFile(
        h_file: isize,
        lp_buffer: *mut u8,
        n_number_of_bytes_to_read: u32,
        lp_number_of_bytes_read: *mut u32,
        lp_overlapped: *const u8,
    ) -> i32;
    fn CloseHandle(h_object: isize) -> i32;
    #[link_name = "CreateToolhelp32Snapshot"]
    fn CreateToolhelp32_snapshot(dw_flags: u32, th32_process_id: u32) -> isize;
    fn Process32FirstW(h_snapshot: isize, lppe: *mut PROCESSENTRY32W) -> i32;
    fn Process32NextW(h_snapshot: isize, lppe: *mut PROCESSENTRY32W) -> i32;
}

#[repr(C)]
#[allow(non_snake_case)]
struct PROCESSENTRY32W {
    dwSize: u32,
    cntUsage: u32,
    th32ProcessID: u32,
    th32DefaultHeapID: usize,
    th32ModuleID: u32,
    cntThreads: u32,
    th32ParentProcessID: u32,
    pcPriClassBase: i32,
    dwFlags: u32,
    szExeFile: [u16; 260],
}

const GENERIC_RW: u32 = 0xC000_0000;
const OPEN_EXISTING: u32 = 3;
const INVALID_HANDLE: isize = -1;
const TH32CS_SNAPPROCESS: u32 = 0x2;

fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().collect()
}

/// 300ms-bounded connect (Coucou pattern): None means "Jarvis absent/slow ->
/// exit 0, the agent continues without us".
fn connect() -> Option<isize> {
    let mut name = wide(PIPE);
    name.push(0);
    unsafe {
        if WaitNamedPipeW(name.as_ptr(), WAIT_MS) == 0 {
            return None;
        }
        let h = CreateFileW(
            name.as_ptr() as *const u32,
            GENERIC_RW,
            0,
            std::ptr::null(),
            OPEN_EXISTING,
            0,
            std::ptr::null(),
        );
        if h == INVALID_HANDLE {
            None
        } else {
            Some(h)
        }
    }
}

/// Fire-and-forget send; with want_reply, blocks for the bridge answer.
fn send(msg: &str, want_reply: bool) -> Option<String> {
    let h = connect()?;
    unsafe {
        let bytes = msg.as_bytes();
        let mut written = 0u32;
        if WriteFile(h, bytes.as_ptr(), bytes.len() as u32, &mut written, std::ptr::null()) == 0 {
            CloseHandle(h);
            return None;
        }
        if !want_reply {
            CloseHandle(h);
            return None;
        }
        let mut buf = vec![0u8; 65536];
        let mut got = 0u32;
        let ok = ReadFile(h, buf.as_mut_ptr(), buf.len() as u32, &mut got, std::ptr::null());
        CloseHandle(h);
        if ok == 0 {
            return None;
        }
        Some(String::from_utf8_lossy(&buf[..got as usize]).into_owned())
    }
}

fn parent_pid() -> u32 {
    unsafe {
        let snap = CreateToolhelp32_snapshot(TH32CS_SNAPPROCESS, 0);
        if snap == INVALID_HANDLE {
            return 0;
        }
        let mut e: PROCESSENTRY32W = std::mem::zeroed();
        e.dwSize = std::mem::size_of::<PROCESSENTRY32W>() as u32;
        let mut ppid = 0u32;
        let mut ok = Process32FirstW(snap, &mut e);
        while ok != 0 {
            if e.th32ProcessID == process::id() {
                ppid = e.th32ParentProcessID;
                break;
            }
            ok = Process32NextW(snap, &mut e);
        }
        CloseHandle(snap);
        ppid
    }
}

fn basename(p: &str) -> String {
    p.rsplit(['/', '\\']).next().unwrap_or(p).to_string()
}

fn forward(topic: &str, payload: Value, cid: Option<&str>) {
    let mut msg = json!({"topic": topic, "payload": payload});
    if let Some(c) = cid {
        msg["correlation_id"] = json!(c);
    }
    let _ = send(&msg.to_string(), false);
}

fn session(agent: &str, project: &str, status: &str) {
    forward(
        "agent.hook.session",
        json!({"agent": agent, "pid": parent_pid(), "project": project, "status": status}),
        None,
    );
}

fn edit_event(file: &str, added: i64, removed: i64, patch: &str) {
    forward(
        "agent.hook.diff",
        json!({"file": file, "added": added, "removed": removed, "patch": patch}),
        None,
    );
}

/// Blocking approval roundtrip. Prints the Claude-Code PreToolUse decision
/// object; a watchdog guarantees we return even if the bridge dies.
fn approve_and_print(agent: &str, tool: &str, command: &str) {
    let pid = parent_pid();
    let watchdog_pid = pid;
    let _ = watchdog_pid;
    std::thread::spawn(|| {
        std::thread::sleep(std::time::Duration::from_secs(120));
        process::exit(0);
    });
    let msg = json!({
        "topic": "agent.hook.approval_request",
        "correlation_id": format!("hook-{}", pid),
        "payload": {"agent": agent, "tool": tool, "command": command, "pid": pid}
    });
    let resp = send(&msg.to_string(), true).unwrap_or_default();
    // parse properly: python json.dumps writes `"allow": true` (space after colon)
    let v: Value = serde_json::from_str(resp.trim()).unwrap_or(Value::Null);
    let allow = v.get("allow").and_then(|a| a.as_bool()).unwrap_or(false);
    let timed_out = v.get("timeout").and_then(|t| t.as_bool()).unwrap_or(false);
    let reason = if allow {
        "Jarvis approved this command"
    } else if timed_out {
        "Jarvis approval timed out - denied"
    } else {
        "Jarvis denied this command"
    };
    let out = json!({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": if allow { "allow" } else { "deny" },
            "permissionDecisionReason": reason
        }
    });
    println!("{}", out);
}

fn patch_from_response(v: &Value) -> (i64, i64, String) {
    if let Some(sp) = v.pointer("/structuredPatch").and_then(|p| p.as_array()) {
        let mut added = 0i64;
        let mut removed = 0i64;
        let mut lines: Vec<String> = Vec::new();
        for h in sp {
            for l in h.get("lines").and_then(|x| x.as_array()).map(|a| a.as_slice()).unwrap_or(&[]) {
                let s = l.as_str().unwrap_or("");
                if s.starts_with('+') && !s.starts_with("+++") {
                    added += 1;
                } else if s.starts_with('-') && !s.starts_with("---") {
                    removed += 1;
                }
                lines.push(s.to_string());
            }
        }
        let joined = lines.join("\n");
        let cap: String = joined.chars().take(4000).collect();
        return (added, removed, cap);
    }
    (0, 0, String::new())
}

fn relay(flavor: &str) {
    let mut input = String::new();
    let _ = std::io::stdin().read_to_string(&mut input);
    let v: Value = match serde_json::from_str(&input) {
        Ok(v) => v,
        Err(_) => return,
    };

    // coucou_agent generic payload: forward verbatim (spec 4.1)
    if let Some(topic) = v.get("topic").and_then(|t| t.as_str()) {
        let payload = v.get("payload").cloned().unwrap_or_else(|| json!({}));
        let cid = v.get("correlation_id").and_then(|c| c.as_str());
        forward(topic, payload, cid);
        return;
    }

    let agent = if flavor == "agy" || flavor == "antigravity" {
        "antigravity"
    } else {
        "claude-code"
    };
    let project = v
        .get("cwd")
        .and_then(|c| c.as_str())
        .map(basename)
        .unwrap_or_default();
    let event = v
        .get("hook_event_name")
        .and_then(|e| e.as_str())
        .unwrap_or("");

    match event {
        "SessionStart" => session(agent, &project, "running"),
        "Stop" | "SessionEnd" => session(agent, &project, "idle"),
        "Notification" => session(agent, &project, "waiting"),
        "PreToolUse" => {
            let tool = v.get("tool_name").and_then(|t| t.as_str()).unwrap_or("");
            if tool != "Bash" {
                return;
            }
            let command = v
                .pointer("/tool_input/command")
                .and_then(|c| c.as_str())
                .unwrap_or("");
            approve_and_print(agent, tool, command);
        }
        "PostToolUse" => {
            let tool = v.get("tool_name").and_then(|t| t.as_str()).unwrap_or("");
            if !matches!(tool, "Edit" | "Write" | "MultiEdit" | "NotebookEdit") {
                return;
            }
            let file = v
                .pointer("/tool_input/file_path")
                .and_then(|f| f.as_str())
                .unwrap_or("(unknown file)");
            let mut added = 0i64;
            let mut removed = 0i64;
            let mut patch = String::new();
            if let Some(resp) = v.get("tool_response") {
                let (a, r, p) = patch_from_response(resp);
                added = a;
                removed = r;
                patch = p;
            }
            if added == 0 && removed == 0 {
                let count = |key: &str| -> i64 {
                    v.pointer(&format!("/tool_input/{}", key))
                        .and_then(|s| s.as_str())
                        .map(|s| s.lines().count() as i64)
                        .unwrap_or(0)
                };
                added = count("new_string");
                removed = count("old_string");
                if patch.is_empty() {
                    patch = v
                        .pointer("/tool_input/new_string")
                        .and_then(|s| s.as_str())
                        .unwrap_or("")
                        .chars()
                        .take(4000)
                        .collect();
                }
            }
            edit_event(file, added, removed, &patch);
        }
        _ => {}
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let cmd = args.get(1).map(|s| s.as_str()).unwrap_or("help");
    match cmd {
        "relay" => relay(args.get(2).map(|s| s.as_str()).unwrap_or("generic")),
        "send" => {
            if let Some(raw) = args.get(2) {
                if let Ok(v) = serde_json::from_str::<Value>(raw) {
                    let topic = v
                        .get("topic")
                        .and_then(|t| t.as_str())
                        .unwrap_or("agent.hook.event")
                        .to_string();
                    let payload = v.get("payload").cloned().unwrap_or_else(|| json!({}));
                    let cid = v
                        .get("correlation_id")
                        .and_then(|c| c.as_str())
                        .map(|s| s.to_string());
                    forward(&topic, payload, cid.as_deref());
                }
            }
        }
        "session" => {
            let agent = args.get(2).map(|s| s.as_str()).unwrap_or("cli-agent");
            let project = args.get(3).map(|s| s.as_str()).unwrap_or("");
            let status = args.get(4).map(|s| s.as_str()).unwrap_or("running");
            session(agent, project, status);
        }
        "edit" => {
            let file = args.get(2).map(|s| s.as_str()).unwrap_or("(unknown file)");
            let added = args.get(3).and_then(|s| s.parse().ok()).unwrap_or(0);
            let removed = args.get(4).and_then(|s| s.parse().ok()).unwrap_or(0);
            let patch = args.get(5).map(|s| s.as_str()).unwrap_or("");
            edit_event(file, added, removed, patch);
        }
        "approve" => {
            let agent = args.get(2).map(|s| s.as_str()).unwrap_or("cli-agent");
            let tool = args.get(3).map(|s| s.as_str()).unwrap_or("Bash");
            let command = args.get(4).map(|s| s.as_str()).unwrap_or("");
            approve_and_print(agent, tool, command);
        }
        _ => {
            eprintln!("jarvis-hook: relay|send|session|edit|approve (always exits 0)");
        }
    }
    process::exit(0);
}
