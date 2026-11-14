"""docs/38: the Mini World on the INSTALLED build, click by click.

Same rules as qa35_surfaces: real mouse/keyboard input (SendInput), CDP :9335
only to read state and element rects, %APPDATA%\\JarvisDesktopPet backed up
first and restored at the end. Needs LM Studio running for the model steps.

Run: .venv/Scripts/python scripts/qa38_world.py    exit 0 = no FAIL
Screenshots: artifacts/qa35/W*.png (same folder as the docs/35 run)
"""

import asyncio
import os
import sys
import time

import aiohttp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa35_common import (  # noqa: E402
    backup_user_data, check, click_el, ev, key, kill_all, launch, main_state, port_open, raise_main, resize_main,
    restore_user_data, results, save_results, screenshot, type_text, wait_for,
)

M = "/"
W = "Jarvis"


async def click(s, sel):
    raise_main()
    ok = await click_el(s, M, W, sel)
    time.sleep(0.6)
    return ok


async def js(s, expr):
    return await ev(s, M, expr)


async def until(s, expr, seconds, step=1.0):
    end = time.time() + seconds
    while time.time() < end:
        v = await js(s, expr)
        if v:
            return v
        time.sleep(step)
    return await js(s, expr)


async def type_into(s, sel, text):
    await click(s, sel)
    key("ctrl", "a") if False else None
    type_text(text)
    time.sleep(0.3)


AGENTS = "Object.values(window.__world.state().agents)"


async def run():
    async with aiohttp.ClientSession() as s:
        launch()
        wait_for(lambda: port_open() and main_state().get("visible"), 60)
        time.sleep(6)
        raise_main()
        resize_main(1440, 900)
        time.sleep(1.5)

        # W1 home + team
        tab = await until(s, "(document.querySelector('.nav-item[aria-current]') || {dataset: {}}).dataset.tab === 'world' && 'world'", 15)
        check("W1 app opens on the World tab", tab == "world", tab)
        n = await until(s, "window.__world && %s.length >= 8 && %s.length" % (AGENTS, AGENTS), 20)
        check("W1 eight regulars in the building", n and n >= 8, n)
        canvas = await js(s, "!!document.querySelector('#wt-stage canvas')")
        check("W1 3D view is drawn", canvas is True, canvas)
        screenshot("W1_world_home")

        # W2 roster -> inspector
        for aid, name in (("rhea", "Rhea"), ("otto", "Otto"), ("pip", "Pip")):
            await click(s, '.wt-row[data-id="%s"]' % aid)
            h = await js(s, "(document.querySelector('#wt-insp h2') || {}).textContent")
            cur = await js(s, "document.querySelector('.wt-row[data-id=\"%s\"]').getAttribute('aria-current')" % aid)
            check("W2 roster click selects %s" % name, h == name and cur == "true", (h, cur))
        await click(s, "#wt-find")
        check("W2 Find in building works", True)

        # W3 floors
        for f in ("1", "2", "3", "0"):
            await click(s, '#wt-floors button[data-floor="%s"]' % f)
            time.sleep(0.8)
            d = await js(s, "window.__world.scene()")
            want = 3 if f == "0" else int(f)
            check("W3 floor button %s" % ("All" if f == "0" else f), d and d["shownFloors"] == want, d)
        screenshot("W3_floors_all")

        # W4 theme + home
        await click(s, "#wt-theme")
        th = await js(s, "window.__world.theme()")
        bg = await js(s, "window.__world.scene().background")
        check("W4 day theme", th == "day" and bg == "#a9c3dc", (th, bg))
        screenshot("W4_day")
        await click(s, "#wt-theme")
        check("W4 back to night", await js(s, "window.__world.theme()") == "night")
        await click(s, "#wt-home")
        check("W4 home view button", True)

        # W5 new agent
        before = await js(s, "%s.length" % AGENTS)
        await click(s, "#wt-add")
        check("W5 new agent form opens", await js(s, "!document.getElementById('wt-new-form').hidden"))
        await click(s, ".wt-preset[data-text^='Translate']")
        await click(s, "#wt-new-name")
        type_text("Paloma")
        await click(s, "#wt-new-form button[type=submit]")
        got = await until(s, "%s.find(a => a.name === 'Paloma')" % AGENTS, 15)
        check("W5 agent created with name + room", got and got["kind"] == "custom" and got["room"], got and (got["kind"], got["room"]))
        check("W5 roster grew by one", await js(s, "%s.length" % AGENTS) == before + 1)
        pid = got["id"] if got else None
        screenshot("W5_new_agent")

        if pid:
            await click(s, '.wt-row[data-id="%s"]' % pid)
            seed0 = await js(s, "window.__world.state().agents['%s'].look_seed" % pid)
            await click(s, "#wt-reroll")
            seed1 = await until(s, "window.__world.state().agents['%s'].look_seed !== %s && window.__world.state().agents['%s'].look_seed" % (pid, repr(seed0).replace("'", '"'), pid), 8)
            check("W6 reroll changes the look", seed1 and seed1 != seed0, (seed0, seed1))
            await click(s, "#wt-edit")
            await click(s, "#wt-edit-name")
            key("ctrl", "a")
            type_text("Paloma Two")
            await click(s, "#wt-edit-form button[type=submit]")
            nm = await until(s, "window.__world.state().agents['%s'].name === 'Paloma Two' && 'ok'" % pid, 8)
            check("W6 edit renames", nm == "ok", nm)
            await click(s, "#wt-del")
            check("W7 delete asks first", await js(s, "!document.getElementById('wt-confirm').hidden"))
            await click(s, "#wt-del-yes")
            gone = await until(s, "!window.__world.state().agents['%s'] && 'gone'" % pid, 10)
            check("W7 delete removes", gone == "gone", gone)
            back_btn = await until(s, "!!document.querySelector('#wt-archived button[data-id=\"%s\"]')" % pid, 10)
            check("W7 shows in Recently deleted", back_btn is True)
            await click(s, '#wt-archived button[data-id="%s"]' % pid)
            again = await until(s, "!!window.__world.state().agents['%s'] && 'back'" % pid, 10)
            check("W7 Bring back restores", again == "back", again)
            await click(s, '.wt-row[data-id="%s"]' % pid)
            await click(s, "#wt-del")
            await click(s, "#wt-del-yes")

        # W8 approval through the World tab (deny)
        await click(s, "#wt-input")
        type_text("run: dir")
        key("enter")
        card = await until(s, "!document.getElementById('wt-approval').hidden && document.getElementById('wt-ap-title').textContent", 40)
        check("W8 approval card in the World tab", bool(card), card)
        screenshot("W8_approval")
        await click(s, "#wt-deny")
        hidden = await until(s, "document.getElementById('wt-approval').hidden && 'hidden'", 10)
        check("W8 Deny closes the card", hidden == "hidden", hidden)
        st = await until(s, "(() => { const j = Object.values(window.__world.state().jobs).find(j => j.text === 'run: dir'); return j && j.status !== 'open' && j.status; })()", 30)
        check("W8 denied job closes without running", st in ("partial", "failed"), st)

        # W9 a real job end to end (model + rules)
        await click(s, "#wt-input")
        type_text("list files in .")
        key("enter")
        st = await until(s, "(() => { const j = Object.values(window.__world.state().jobs).find(j => j.text === 'list files in .'); return j && j.status !== 'open' && j.status; })()", 60)
        check("W9 rule job finishes", st == "done", st)
        strip = await js(s, "!document.getElementById('wt-job').hidden && document.getElementById('wt-job-meta').textContent")
        check("W9 job strip shows the result", bool(strip), strip)

        # W10 Stop all on a running model job
        await click(s, "#wt-input")
        type_text("Search the web for the best budget mechanical keyboards this year and then write me a short comparison of three of them")
        key("enter")
        await until(s, "Object.values(window.__world.state().jobs).some(j => j.status === 'open')", 20)
        time.sleep(2)
        await click(s, "#wt-stop")
        st = await until(s, "(() => { const j = Object.values(window.__world.state().jobs).find(j => j.text.startsWith('Search the web for the best budget')); return j && j.status !== 'open' && j.status; })()", 30)
        check("W10 Stop all stops the running job", st == "stopped", st)
        temps = await js(s, "%s.filter(a => a.kind === 'temp').length" % AGENTS)
        check("W10 no temporary agents left", temps == 0, temps)

        # W11 skills: draft with the real model, turn on, run in the packaged sandbox
        await click(s, "#wt-skills-btn")
        check("W11 Skills drawer opens", await js(s, "!document.getElementById('wt-skillpanel').hidden"))
        await click(s, "#wt-sk-desc")
        type_text("Convert a temperature between Celsius and Fahrenheit")
        await click(s, "#wt-sk-draft")
        card = await until(s, "document.querySelector('.wt-skill-card') && document.querySelector('.wt-skill-card').dataset.name", 180, 2)
        check("W11 Bodie drafts a skill", bool(card), card)
        screenshot("W11_skill_draft")
        if card:
            await click(s, '.wt-skill-card[data-name="%s"] .wt-sk-top' % card)
            ok = await js(s, "!!document.querySelector('.wt-skill-card.open [data-op=enable]')")
            problems = await js(s, "(document.querySelector('.wt-sk-problems') || {}).textContent || ''")
            check("W11 draft passed the safety check and its sandbox test (packaged exe)", ok is True, problems[:200])
            if ok:
                await click(s, ".wt-skill-card.open [data-op=enable]")
                on = await until(s, "document.querySelector('.wt-skill-card[data-name=\"%s\"] .wt-badge.on') && 'on'" % card, 10)
                check("W11 Turn on", on == "on", on)
                if not await js(s, "!!document.querySelector('.wt-skill-card.open')"):
                    await click(s, '.wt-skill-card[data-name="%s"] .wt-sk-top' % card)
                await click(s, ".wt-skill-card.open [data-op=test]")
                time.sleep(4)
                out = await js(s, "(() => { const r = [...document.querySelectorAll('.wt-skill-card.open .wt-kv')].find(k => k.querySelector('span').textContent === 'Example result'); return r ? r.querySelector('b').textContent : null; })()")
                check("W11 Run example in the sandbox", bool(out), out)
                await click(s, ".wt-skill-card.open [data-op=disable]")
            if not await js(s, "!!document.querySelector('.wt-skill-card.open')"):
                await click(s, '.wt-skill-card[data-name="%s"] .wt-sk-top' % card)
            await click(s, ".wt-skill-card.open [data-op=delete]")
            gone = await until(s, "!document.querySelector('.wt-skill-card[data-name=\"%s\"]') && 'gone'" % card, 10)
            check("W11 Delete skill", gone == "gone", gone)
        await click(s, "#wt-sp-close")

        # W12 power off / on
        await click(s, "#wt-power")
        off = await until(s, "!document.getElementById('wt-off').hidden && 'off'", 10)
        check("W12 turn off shows the off card", off == "off", off)
        screenshot("W12_off")
        await click(s, "#wt-enable")
        on = await until(s, "document.getElementById('wt-off').hidden && 'on'", 10)
        check("W12 Turn on Mini World without a restart", on == "on", on)

        # W13 narrow window
        resize_main(880, 900)
        time.sleep(1.5)
        order = await js(s, "(() => { const c = document.querySelector('.wt-center').getBoundingClientRect(); const r = document.querySelector('.wt-roster').getBoundingClientRect(); return c.top < r.top; })()")
        check("W13 at 880px the building comes first", order is True, order)
        screenshot("W13_narrow")
        resize_main(1440, 900)

        # W14 the other tabs still work
        for tab in ("chat", "activity", "memory", "settings", "world"):
            await click(s, '.nav-item[data-tab="%s"]' % tab)
            act = await js(s, "document.getElementById('pane-%s').classList.contains('active')" % tab)
            check("W14 %s tab still opens" % tab, act is True, act)


def main():
    backup = backup_user_data("qa38")
    try:
        asyncio.run(run())
    finally:
        kill_all()
        restore_user_data(backup)
        save_results("qa38_world_results.json")
    fails = [r for r in results if r[1] is False]
    print("\n%d checks, %d FAIL" % (len(results), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
