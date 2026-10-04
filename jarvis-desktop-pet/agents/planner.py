import re

from agents.base import BaseAgent
from core.bus import Event, create_event

PATH_RE = re.compile(r"""(?P<q>["'][^"']+["'])|(?P<p>~?[\w.]:[\\/][\w\s.\\/-]+|\.{0,2}[\\/][\w\s.\\/-]+|\b[\w-]+\.[a-zA-Z]{1,5}\b)""")
URL_RE = re.compile(r"https?://\S+|\bwww\.\S+")
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")


def _clean_path(m: re.Match) -> str:
    if m.group("q"):
        return m.group("q")[1:-1]
    return m.group("p").strip().strip('",.')


class PlannerAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("planner", bus)

    async def start(self):
        await super().start()
        self.bus.subscribe("planner.request", self.handle)

    async def handle(self, ev: Event):
        if ev.type == "plan":
            q = str(ev.payload.get("query", ""))
            low = q.lower()
            steps = []

            screenish = re.search(r"\b(screen|desktop|screenshot)\b", low)
            screen_intent = re.search(
                r"summar\w*|\bdescribe\b|\bread\b|\bcapture\b|\bgrab\b|take a (screenshot|picture)|"
                r"\bscreenshot\b|what(?:'s| is| am i)\b|\bam i looking\b|\blook at\b|\bshow me\b",
                low,
            )
            screen_mutation = re.search(
                r"\b(open|close|delete|remove|move|create|list|run|search|find|google)\b", low
            )

            # file ingestion prompts (spec 29 section 5.2) - raised by the pet
            # drag-and-drop composer prefill: images go to the vision pipeline,
            # text/code/pdf documents get summarized.
            paths = [_clean_path(m) for m in PATH_RE.finditer(q)]
            img = next((p for p in paths if p.lower().rstrip('".').endswith(IMG_EXTS)), None)
            if img and re.search(
                r"\b(describe|analy[sz]e|inspect|look at|summar\w*|what(?:'s| is| am) in)\b", low
            ):
                steps.append({"action": "vision_file", "path": img, "query": q, "risk": 0})
            elif paths and re.search(r"\b(summar\w*|explain|describe|break down)\b", low) and (
                re.search(r"\b(this|the|a|that|dropped)?\s*(file|document|pdf|doc)\b", low)
                or re.search(r"\.\w{1,5}\b", q)
            ):
                steps.append({"action": "summarize_file", "path": paths[0], "query": q, "risk": 0})

            elif screenish and screen_intent and not screen_mutation:
                steps.append({"action": "vision_describe", "query": q, "risk": 0})

            elif re.search(r"\b(search|google|look up|web search)\b", low):
                m = re.search(r"(?:search(?: for| the web for| the web)?|google|look up)\s+(.+)", q, re.I)
                term = m.group(1).strip().rstrip("?.!") if m else q
                steps.append({"action": "web_search", "query": term, "risk": 0})

            elif re.search(r"\bclose\b", low):
                m = re.search(r"\bclose\s+(.+)", q, re.I)
                target = m.group(1).strip().rstrip(".") if m else ""
                steps.append({"action": "close_app", "target": target, "risk": 5})

            elif re.search(r"\b(open|launch|start)\b", low):
                m = re.search(r"\b(?:open|launch|start)\s+(.+)", q, re.I)
                target = m.group(1).strip().rstrip(".") if m else ""
                if target.endswith("?"):
                    steps.append({"action": "respond", "text": "What would you like me to open — an app or a URL?", "risk": 0})
                elif URL_RE.search(target) or "browser" in low or "website" in low:
                    url = URL_RE.search(target)
                    steps.append({"action": "open_url", "url": url.group(0) if url else target, "risk": 2})
                else:
                    steps.append({"action": "launch_app", "target": target, "risk": 2})

            elif re.search(r"\b(delete|remove)\b", low):
                paths = [_clean_path(m) for m in PATH_RE.finditer(q)]
                if paths:
                    for p in paths:
                        steps.append({"action": "delete_file", "target": p, "risk": 9})
                else:
                    steps.append({"action": "respond", "text": "Which file or folder should I delete? Give me the path.", "risk": 0})

            elif re.search(r"\bmove|mv\b", low):
                paths = [_clean_path(m) for m in PATH_RE.finditer(q)]
                if len(paths) >= 2:
                    steps.append({"action": "move_file", "src": paths[0], "dst": paths[1], "risk": 4})
                else:
                    steps.append({"action": "respond", "text": "What should I move, and where to?", "risk": 0})

            elif re.search(r"\bcreate|make (a )?file|new file\b", low):
                paths = [_clean_path(m) for m in PATH_RE.finditer(q)]
                if paths:
                    steps.append({"action": "create_file", "path": paths[0], "content": "", "risk": 4})
                else:
                    steps.append({"action": "respond", "text": "What file should I create, and where?", "risk": 0})

            elif re.search(r"\b(list|show) (files|directory|folder)\b", low):
                paths = [_clean_path(m) for m in PATH_RE.finditer(q)]
                steps.append({"action": "list_dir", "target": paths[0] if paths else ".", "risk": 0})

            elif re.search(r"\b(run|execute|shell|command|powershell)\b", low):
                m = re.search(r"\b(?:run|execute|shell command|command|powershell)\s*[:\s]\s*(.+)", q, re.I)
                cmd = m.group(1).strip().rstrip(".") if m else ""
                if cmd and len(cmd) < 160 and not cmd.endswith("?"):
                    steps.append({"action": "run_shell", "cmd": cmd, "risk": 8})
                else:
                    steps.append({"action": "respond", "text": f"Understood: {q}", "risk": 0})

            elif re.search(r"\b(type|write|input)\b", low):
                m2 = re.search(r"""['"](.+?)['"]""", q)
                text = m2.group(1) if m2 else re.sub(r"^\s*(type|write|input)\s*", "", q, flags=re.I)
                steps.append({"action": "type_text", "text": text, "risk": 6})

            else:
                # no action intent matched (e.g. the query merely mentioned a
                # screen) - hand back to recall so the user gets a real answer
                await self.bus.publish(
                    create_event(
                        "memory.request", "recall", {"query": q}, correlation_id=ev.correlation_id
                    )
                )
                return

            await self.bus.publish(
                create_event("planner.result", "plan", {"steps": steps, "query": q}, correlation_id=ev.correlation_id)
            )
