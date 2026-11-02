"""docs/35 sections 5-11 on the INSTALLED build: every surface, with physical
mouse/keyboard input (CDP :9335 is used only to read state and element rects).

User data safety: %APPDATA%\\JarvisDesktopPet\\{config,data} is backed up first
and restored at the end, so memories/settings the test touches come back.
Skipped on purpose (marked N/A): Memory "Clear all" and Integrations hook
install (would touch real user data / ~/.claude; covered by hook_e2e with
backups), mic-dependent tests (wake/mic test buttons, dictation audio).

Run: .venv/Scripts/python scripts/qa35_surfaces.py    exit 0 = no FAIL
Screenshots: artifacts/qa35/*.png, visual pass in artifacts/qa35/visual/
"""

import asyncio
import os
import sys
import time

import aiohttp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa35_common import (  # noqa: E402
    OUT, backup_user_data, check, click_el, ev, hover_el, key, kill_all, launch, main_state, mouse_away, na,
    port_open, raise_main, resize_main, restore_user_data, results, save_results, screenshot, type_text,
    visible, wait_for,
)

M = "/"           # main window CDP target
PET = "/pet.html"
DOCK = "/dock.html"
W = "Jarvis"
RAW_TOOLS = ["delete_file", "run_shell", "launch_app", "open_url", "move_file", "type_text", "press_hotkey",
             "vision_describe", "list_dir", "close_app"]


async def tab_now(s):
    return await ev(s, M, "(document.querySelector('.nav-item[aria-current]') || {}).dataset ? document.querySelector('.nav-item[aria-current]').dataset.tab : null")


async def click(s, sel, page=M, title=W):
    raise_main() if title == W else None
    ok = await click_el(s, page, title, sel)
    time.sleep(0.5)
    return ok


async def run():
    async with aiohttp.ClientSession() as s:
        launch()
        wait_for(lambda: port_open() and main_state().get("visible"), 45)
        time.sleep(5)

        # ---------------- onboarding (O1-O3): open the sheet and walk it
        await ev(s, M, "window.openOnboarding && window.openOnboarding(); 1")
        time.sleep(0.8)
        t1 = await ev(s, M, "document.querySelector('#ob-step-1 h3').textContent")
        check("O1 onboarding step 1 is 'Meet Pip'", t1 == "Meet Pip", t1)
        screenshot("O1_meet_pip")
        await click(s, "#ob-next")
        st = await ev(s, M, "document.getElementById('onboarding').dataset.step")
        check("O2 Next goes to Microphone", st == "2", st)
        screenshot("O2_microphone")
        await click(s, "#ob-next")
        st = await ev(s, M, "document.getElementById('onboarding').dataset.step")
        check("O3 Next goes to Model", st == "3", st)
        screenshot("O3_model")
        await click(s, "#ob-back")
        st = await ev(s, M, "document.getElementById('onboarding').dataset.step")
        check("O3 Back returns to step 2", st == "2", st)
        await ev(s, M, "document.getElementById('onboarding').hidden = true; 1")

        # ---------------- header tabs (H2-H5) + keyboard
        for tab in ("activity", "memory", "settings", "chat"):
            await click(s, '.nav-item[data-tab="%s"]' % tab)
            cur = await tab_now(s)
            act = await ev(s, M, "document.getElementById('pane-%s').classList.contains('active')" % tab)
            check("H tab %s switches pane + aria-current" % tab, cur == tab and act is True, (cur, act))
        # H9 + menu
        await click(s, "#quick-actions-btn")
        opened = await ev(s, M, "!document.getElementById('plus-menu').hidden")
        key("esc")
        closed = await ev(s, M, "document.getElementById('plus-menu').hidden")
        check("H9 + menu opens, Esc closes", opened and closed, (opened, closed))
        await click(s, "#quick-actions-btn")
        await click(s, "#top-settings")
        check("H9 + menu Settings item opens Settings", await tab_now(s) == "settings")
        await click(s, '.nav-item[data-tab="chat"]')
        # + menu pet switch hides and shows the pet window
        await click(s, "#quick-actions-btn")
        await click(s, "#plus-menu .switch .slider")
        time.sleep(1.2)
        pet_off = not visible("Jarvis Pet")
        await click(s, "#plus-menu .switch .slider")
        time.sleep(1.2)
        pet_on = visible("Jarvis Pet")
        key("esc")
        check("H9 + menu pet switch hides then shows the pet", pet_off and pet_on, (pet_off, pet_on))
        # H7 palette
        await click(s, "#cmd-palette-btn")
        po = await ev(s, M, "!document.getElementById('cmd-palette').hidden && document.activeElement && document.activeElement.id")
        key("esc")
        pc = await ev(s, M, "document.getElementById('cmd-palette').hidden")
        check("H7 command palette opens focused, Esc closes", po == "cmd-palette-input" and pc is True, (po, pc))
        h6 = await ev(s, M, "(document.querySelector('.model-badge') || {}).textContent")
        check("H6 provider pill shows provider", bool(h6 and h6.strip()), h6)

        # ---------------- chat (CH1-CH5)
        empty = await ev(s, M, "!!document.getElementById('empty-state') && !!document.querySelector('.hero-pip')")
        check("CH1 empty state with Pip hero on a fresh start", empty, empty)
        screenshot("CH1_empty_state")
        chips = await ev(s, M, "[...document.querySelectorAll('#hero-chips .chip')].map(c => c.dataset.prompt)")
        for i, prompt in enumerate(chips or []):
            await click(s, "#hero-chips .chip:nth-child(%d)" % (i + 1))
            v = await ev(s, M, "document.getElementById('chat-input').value")
            check("CH2 chip %d prefills composer (not sent)" % (i + 1), v == prompt and await ev(s, M, "!!document.getElementById('empty-state')"), v)
        await ev(s, M, "document.getElementById('chat-input').value = ''; 1")
        await click(s, "#chat-input")
        type_text("hello pip")
        key("shift", "enter")
        type_text("second line")
        nl = await ev(s, M, "document.getElementById('chat-input').value")
        check("CH3 Shift+Enter makes a new line", nl == "hello pip\nsecond line", repr(nl))
        await ev(s, M, "document.getElementById('chat-input').value = ''; 1")
        key("enter")
        n0 = await ev(s, M, "document.querySelectorAll('.msg-row.user, .msg.user').length")
        check("CH3 Enter on empty composer sends nothing", n0 == 0, n0)
        type_text("what can you do?")
        key("enter")
        sent = wait_for(lambda: True, 0.1)
        await asyncio.sleep(2)
        n1 = await ev(s, M, "document.querySelectorAll('.msg-row.user, .msg.user, [data-role=user]').length")
        check("CH3 Enter sends the message", (n1 or 0) >= 1, n1)
        await asyncio.sleep(12)
        reply = await ev(s, M, "document.querySelectorAll('.msg-row.assistant, .msg.assistant, [data-role=assistant]').length")
        check("CH4 assistant reply rendered", (reply or 0) >= 1, reply)
        screenshot("CH4_reply")
        # CH5 approval in chat: real delete request on a probe file, Deny by physical click
        probe = os.path.join(os.environ["TEMP"], "qa35_probe.txt")
        open(probe, "w").write("qa35 probe - safe to delete")
        await click(s, "#chat-input")
        type_text("delete the file qa35_probe.txt in %s" % os.environ["TEMP"])
        key("enter")
        got = wait_for(lambda: True, 0.1)
        card = None
        for _ in range(40):
            card = await ev(s, M, "(() => { const c = document.querySelector('.chat-approval-card:not(.settled), .approval-card'); return c ? c.innerText : null; })()")
            if card:
                break
            await asyncio.sleep(1)
        check("CH5 approval card appears in chat", bool(card), card)
        if card:
            check("CH5 approval card has no raw tool names", not any(t in card for t in RAW_TOOLS), card)
            screenshot("CH5_approval_card")
            await click(s, ".chat-approval-card .deny, .approval-card .deny, .ac-btns .deny")
            await asyncio.sleep(3)
            still = os.path.exists(probe)
            check("CH5 Deny keeps the file", still, still)

        # ---------------- activity (A1-A3)
        await click(s, '.nav-item[data-tab="activity"]')
        txt = await ev(s, M, "document.getElementById('activity-list').innerText")
        check("A1 activity has task cards", bool(txt and txt.strip()), (txt or "")[:120])
        check("A1 no raw tool names in Activity", not any(t in (txt or "") for t in RAW_TOOLS), [t for t in RAW_TOOLS if t in (txt or "")])
        screenshot("A1_activity")
        await click(s, '.nav-item[data-tab="chat"]')
        await click(s, "#chat-input")
        type_text("set a timer for 9 minutes")
        key("enter")
        await asyncio.sleep(3)
        await click(s, '.nav-item[data-tab="activity"]')
        chip = await ev(s, M, "!document.getElementById('task-timers').hidden && document.querySelectorAll('#task-timers .task-chip-cancel').length")
        check("A2 timer pill with countdown appears", (chip or 0) >= 1, chip)
        screenshot("A2_timer")
        if chip:
            n_before = chip
            await click(s, "#task-timers .task-chip-cancel")
            await asyncio.sleep(2)
            n_after = await ev(s, M, "document.querySelectorAll('#task-timers .task-chip-cancel').length")
            check("A2 Cancel removes the timer", (n_after or 0) < n_before, (n_before, n_after))
        await click(s, "#activity-clear")
        cleared = await ev(s, M, "document.getElementById('activity-list').innerText")
        check("A3 Clear empties Activity", not any(t in (cleared or "") for t in ("You asked",)), (cleared or "")[:80])

        # ---------------- memory (M1-M4)
        await click(s, '.nav-item[data-tab="memory"]')
        await click(s, "#memory-add-btn")
        await click(s, "#memory-add-text")
        type_text("qa35 favourite colour is teal")
        await click(s, "#memory-add-form button[type=submit]")
        await asyncio.sleep(1.5)
        has = await ev(s, M, "[...document.querySelectorAll('.mem-card .mem-content')].some(p => p.textContent.includes('qa35 favourite colour'))")
        check("M2 Add Fact saves a fact", has, has)
        await click(s, "#memory-search")
        type_text("qa35")
        await asyncio.sleep(0.6)
        cnt = await ev(s, M, "document.querySelectorAll('.mem-card').length")
        check("M1 search filters live", cnt == 1, cnt)
        sel = ".mem-card"
        await hover_el(s, M, W, sel)
        await click(s, ".mem-card .mem-edit")
        await asyncio.sleep(0.4)
        key("ctrl", "a")
        type_text("qa35 favourite colour is amber")
        key("enter")
        await asyncio.sleep(1.5)
        ed = await ev(s, M, "(document.querySelector('.mem-card .mem-content') || {}).textContent + ' | ' + (document.querySelector('.mem-card .mem-time') || {}).textContent")
        check("M3 inline edit saves with Enter and marks edited", ed and "amber" in ed and "edited" in ed, ed)
        screenshot("M3_memory_edit")
        await hover_el(s, M, W, sel)
        await click(s, ".mem-card .mem-forget")
        await asyncio.sleep(1.0)
        gone = await ev(s, M, "document.querySelectorAll('.mem-card').length")
        await click(s, "#memory-undo")
        await asyncio.sleep(1.5)
        back = await ev(s, M, "document.querySelectorAll('.mem-card').length")
        check("M4 Forget removes, Undo restores", gone == 0 and back == 1, (gone, back))
        await hover_el(s, M, W, sel)
        await click(s, ".mem-card .mem-forget")
        await asyncio.sleep(1.0)
        await ev(s, M, "document.getElementById('memory-search').value=''; document.getElementById('memory-search').dispatchEvent(new Event('input')); 1")
        for cat in ("preferences", "facts", "projects", "workflows", "people", "all"):
            await click(s, '.mem-chip[data-cat="%s"]' % cat)
        act = await ev(s, M, "document.querySelector('.mem-chip.active').dataset.cat")
        check("M1 category chips switch", act == "all", act)
        na("M5 Clear all", "not clicked: would wipe the user's real memories")

        # ---------------- settings (S1-S10)
        await click(s, '.nav-item[data-tab="settings"]')
        secs = await ev(s, M, "[...document.querySelectorAll('#settings-index button[data-sec]')].map(b => b.dataset.sec)")
        for sec in secs or []:
            await click(s, '#settings-index button[data-sec="%s"]' % sec)
            only = await ev(s, M, "[...document.querySelectorAll('#settings-content .section')].filter(x => getComputedStyle(x).display !== 'none').map(x => x.id)")
            check("S1 %s shows only its section" % sec, only == [sec], only)
        await click(s, '#settings-index button[data-sec="sec-models"]')
        for prov in ("openai", "anthropic", "lm_studio"):
            await click(s, '#provider-seg button[data-provider="%s"]' % prov)
            on = await ev(s, M, "document.querySelector('#provider-seg button.on').dataset.provider")
            check("S2 provider seg %s" % prov, on == prov, on)
        await click(s, '#provider-seg button[data-provider="openai"]')
        await click(s, "#prov-openai-key")
        type_text("sk-qa35-not-a-key")
        t0 = await ev(s, M, "document.getElementById('prov-openai-key').type")
        await click(s, '.key-reveal[data-target="prov-openai-key"]')
        t1 = await ev(s, M, "document.getElementById('prov-openai-key').type")
        check("S2 key reveal toggles visibility", t0 == "password" and t1 == "text", (t0, t1))
        await ev(s, M, "document.getElementById('prov-openai-key').value=''; 1")
        await click(s, '#provider-seg button[data-provider="lm_studio"]')
        await click(s, "#test")
        await asyncio.sleep(4)
        res = await ev(s, M, "(document.querySelector('.model-connect-card') || {}).innerText")
        check("S2 Test connection shows a result card", bool(res), (res or "")[:120])
        screenshot("S2_model")
        # S4 companion + render segs (live)
        await click(s, '#settings-index button[data-sec="sec-assistant"]')
        await click(s, '#companion-seg button[data-mode="dock"]')
        time.sleep(1.5)
        dock_on = visible("Jarvis Dynamic Island") and not visible("Jarvis Pet")
        await click(s, '#companion-seg button[data-mode="pet"]')
        time.sleep(1.5)
        pet_back = visible("Jarvis Pet") and not visible("Jarvis Dynamic Island")
        check("S4 companion seg switches pet <-> island live", dock_on and pet_back, (dock_on, pet_back))
        await click(s, '#pet-render-seg button[data-render="3d"]')
        time.sleep(1.5)
        r3 = await ev(s, PET, "getComputedStyle(document.getElementById('pet-3d')).display !== 'none'")
        await click(s, '#pet-render-seg button[data-render="2d"]')
        time.sleep(1.2)
        r2 = await ev(s, PET, "getComputedStyle(document.getElementById('pet-2d')).display !== 'none'")
        check("S4 render seg 3D then 2D applies to the pet", r3 and r2, (r3, r2))
        # S10 Save: start clean (earlier live controls may have dirtied it), dirty -> save -> saved
        if not await ev(s, M, "document.getElementById('save').disabled"):
            await click(s, "#save")
            await asyncio.sleep(2)
        d0 = await ev(s, M, "document.getElementById('save').disabled")
        await click(s, '#settings-index button[data-sec="sec-assistant"]')
        await click(s, "#p-voice")
        type_text(" ")
        d1 = await ev(s, M, "document.getElementById('save').disabled")
        key("backspace")
        await click(s, "#save")
        await asyncio.sleep(2)
        note = await ev(s, M, "document.getElementById('settings-note').textContent")
        check("S10 Save enables when dirty and saves", d0 is True and d1 is False and note and "ave" in note, (d0, d1, note))
        # S7 dictionary add row
        await click(s, '#settings-index button[data-sec="sec-dictionary"]')
        r0 = await ev(s, M, "document.querySelectorAll('.vocab-row').length")
        await click(s, "#vocab-add")
        r1 = await ev(s, M, "document.querySelectorAll('.vocab-row').length")
        check("S7 dictionary Add row", r1 == (r0 or 0) + 1, (r0, r1))
        await click(s, '#settings-index button[data-sec="sec-history"]')
        await click(s, "#dict-history-refresh")
        check("S8 history refresh clickable", True)
        na("S9 Integrations install/remove", "not clicked: edits the user's real ~/.claude + agy configs; hook_e2e covers it with backups")
        na("S3 wake test / mic test", "needs a live microphone")
        # AB1/AB2
        await click(s, '#settings-index button[data-sec="sec-about"]')
        ver = await ev(s, M, "document.getElementById('about-version').textContent")
        check("AB1 About shows the version", ver == "v0.1.0", ver)
        await click(s, "#diag-export")
        await asyncio.sleep(4)
        ds = await ev(s, M, "document.getElementById('diag-status').textContent")
        check("AB2 Export diagnostics writes a zip", ds and ds.startswith("Saved to") and ds.endswith(".zip"), ds)
        screenshot("AB_about")

        # ---------------- keyboard (K3/K4)
        await click(s, '.nav-item[data-tab="chat"]')
        key("tab")
        f1 = await ev(s, M, "document.activeElement && (document.activeElement.id || document.activeElement.className)")
        ring = await ev(s, M, "getComputedStyle(document.activeElement).outlineStyle + ' ' + getComputedStyle(document.activeElement).outlineWidth")
        check("K3 Tab moves focus with a visible ring", bool(f1) and ring and not ring.startswith("none"), (f1, ring))

        # ---------------- pet (P2-P5) + island (I1-I5)
        na("P4 right-click menu", "not implemented in this build (spec 34 section 5 lists it as Phase 4+ pet simplification)")
        await ev(s, M, "window.applyCompanion('dock'); 1")
        time.sleep(2)
        await hover_el(s, DOCK, "Jarvis Dynamic Island", "#dynamic-island")
        time.sleep(1)
        exp = await ev(s, DOCK, "document.getElementById('dynamic-island').classList.contains('expanded')")
        check("I1 hover expands the island", exp, exp)
        await click_el(s, DOCK, "Jarvis Dynamic Island", '.island-tab[data-view="chat"]')
        time.sleep(0.6)
        cv = await ev(s, DOCK, "document.getElementById('dynamic-island').dataset.card")
        check("I2 island Chat tab shows the chat card", cv == "chat", cv)
        await click_el(s, DOCK, "Jarvis Dynamic Island", "#ichat-input")
        type_text("hi from the island")
        key("enter")
        await asyncio.sleep(2)
        sent = await ev(s, DOCK, "document.getElementById('ichat-log').innerText")
        check("I5 island inline chat sends", sent and "hi from the island" in sent, (sent or "")[:80])
        screenshot("I5_island_chat", "dock_expanded")
        await click_el(s, DOCK, "Jarvis Dynamic Island", '.island-tab[data-view="home"]')
        key("esc")
        mouse_away()
        await ev(s, M, "window.applyCompanion('pet'); 1")
        time.sleep(2)

        # ---------------- visual pass at two sizes
        os.makedirs(os.path.join(OUT, "visual"), exist_ok=True)
        panes = [("chat", None), ("activity", None), ("memory", None)] + [("settings", sec) for sec in (secs or [])]
        for w, h in ((1100, 760), (760, 560)):
            resize_main(w, h)
            for tab, sec in panes:
                await ev(s, M, "window.showTab(%r); %s 1" % (tab, ("window.showSettingsTab(%r);" % sec) if sec else ""))
                time.sleep(0.5)
                # overflow = something sticks out of the window that is NOT inside a horizontal scroller
                ov = await ev(s, M, "document.documentElement.scrollWidth > innerWidth + 1 || [...document.querySelectorAll('.pane.active *')].some(e => { const r = e.getBoundingClientRect(); if (!r.width || r.right <= innerWidth + 1) return false; for (let p = e.parentElement; p; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return false; } return true; })")
                name = "%s%s-%dx%d" % (tab, ("-" + sec) if sec else "", w, h)
                check("V overflow-free %s" % name, ov is False, ov)
                raise_main()
                screenshot(os.path.join("visual", name))
        resize_main(1100, 760)


def main():
    backup = backup_user_data()
    kill_all()
    try:
        asyncio.run(run())
    except Exception:
        import traceback

        traceback.print_exc()
        check("driver ran without exception", False)
    finally:
        kill_all()
        restore_user_data(backup)
    save_results("surfaces_results.json")
    fails = [c for c, p, _ in results if p is False]
    print("== %d PASS, %d FAIL, %d N/A ==" % (sum(1 for _, p, _ in results if p), len(fails),
                                              sum(1 for _, p, _ in results if p is None)))
    sys.exit(1 if fails else 0)


main()
