# Visual inspection capture (doc 30, section 7).
# Captures REAL Tauri OS windows by exact title: "Jarvis Pet", "Jarvis Dynamic Island", "Jarvis".
# State -> window mapping:
#   pet_idle | pet_hover | pet_speech | pet_approval  -> Jarvis Pet
#   dock_collapsed | dock_expanded                    -> Jarvis Dynamic Island
#   main_app_expanded                                 -> Jarvis
# (main_app_collapsed is captured by scripts/inspect_states.py after a real
#  coordinate click on the toggle, then this script in collapsed state.)
#
# Usage: .\inspect_ui.ps1 -State pet_idle [-OutputDir <dir>]
param(
    [Parameter(Mandatory = $true)][string]$State,
    [string]$OutputDir = "$PSScriptRoot\..\artifacts\ui_inspection"
)

if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class InspectWin {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }

    public static IntPtr FindByTitle(string title, uint preferPid) {
        IntPtr found = IntPtr.Zero, alt = IntPtr.Zero;
        EnumWindows(delegate(IntPtr h, IntPtr l) {
            if (!IsWindowVisible(h)) return true;
            var sb = new StringBuilder(256);
            GetWindowText(h, sb, 256);
            if (string.Equals(sb.ToString(), title, StringComparison.Ordinal)) {
                uint pid; GetWindowThreadProcessId(h, out pid);
                if (preferPid != 0 && pid == preferPid) { found = h; return false; }
                if (alt == IntPtr.Zero) alt = h;
            }
            return true;
        }, IntPtr.Zero);
        return found != IntPtr.Zero ? found : alt;
    }
    public static RECT Rect(IntPtr h) { RECT r; GetWindowRect(h, out r); return r; }
}
"@

$StateMap = @{
    "pet_idle"         = @("Jarvis Pet", "pet_idle.png")
    "pet_hover"        = @("Jarvis Pet", "pet_hover.png")
    "pet_speech"       = @("Jarvis Pet", "pet_speech.png")
    "pet_approval"     = @("Jarvis Pet", "pet_approval.png")
    "dock_collapsed"   = @("Jarvis Dynamic Island", "dock_collapsed.png")
    "dock_expanded"    = @("Jarvis Dynamic Island", "dock_expanded.png")
    "main_app_expanded" = @("Jarvis", "main_app_expanded.png")
    "main_app_collapsed" = @("Jarvis", "main_app_collapsed.png")
}

if (-not $StateMap.ContainsKey($State)) {
    Write-Error "Unknown state '$State'. Valid: $($StateMap.Keys -join ', ')"
    exit 2
}

[void][InspectWin]::SetProcessDPIAware()
$jarvisPid = 0
$jp = Get-Process -Name "JarvisDesktopPet" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($jp) { $jarvisPid = [uint32]$jp.Id }

$titles = $StateMap[$State]
$hwnd = [InspectWin]::FindByTitle($titles[0], $jarvisPid)
if ($hwnd -eq [IntPtr]::Zero) {
    Write-Output "FAIL no window titled '$($titles[0])'"
    exit 1
}

[void][InspectWin]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 350

$r = [InspectWin]::Rect($hwnd)
$w = $r.Right - $r.Left
$h = $r.Bottom - $r.Top
if ($w -le 0 -or $h -le 0) {
    Write-Output "FAIL bad rect for '$($titles[0])' ($w x $h)"
    exit 1
}

$bmp = New-Object System.Drawing.Bitmap($w, $h)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$path = Join-Path $OutputDir $titles[1]
$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$gfx.Dispose()
$bmp.Dispose()

Write-Output "RESULT $path ($w x $h)"
exit 0
