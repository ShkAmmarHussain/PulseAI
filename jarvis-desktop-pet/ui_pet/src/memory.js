// Memory Studio (spec 32, section 2.2): browse, search, add and forget the
// facts Jarvis keeps in data/memory.json. All mutations go over the WS and
// come back as full-state payloads, so the list always mirrors the store.
(function () {
  const list = document.getElementById("memory-list");
  if (!list) return;

  const search = document.getElementById("memory-search");
  const filters = document.getElementById("memory-filters");
  const addBtn = document.getElementById("memory-add-btn");
  const addForm = document.getElementById("memory-add-form");
  const addCat = document.getElementById("memory-add-cat");
  const addText = document.getElementById("memory-add-text");
  const addCancel = document.getElementById("memory-add-cancel");
  const clearBtn = document.getElementById("memory-clear");
  const exportBtn = document.getElementById("memory-export");
  const toast = document.getElementById("memory-toast");
  const toastText = document.getElementById("memory-toast-text");
  const undoBtn = document.getElementById("memory-undo");

  const LABELS = {
    preferences: "Preferences",
    facts: "Facts",
    projects: "Projects",
    workflows: "Workflows",
    people: "People",
  };

  let state = { profile: {}, facts: [] };
  let activeCat = "all";
  let query = "";
  let lastDeleted = null;
  let toastTimer = null;
  // inline edit (spec 34 section 4): survives re-renders from memory.updated
  let editing = null; // { id, draft }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function when(ts) {
    try {
      const d = new Date(ts);
      if (isNaN(d)) return "";
      const today = new Date();
      const same = d.toDateString() === today.toDateString();
      return same
        ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : d.toLocaleDateString([], { month: "short", day: "numeric" }) + " " +
          d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      return "";
    }
  }

  function visible() {
    const q = (query || "").trim().toLowerCase();
    return (state.facts || []).filter((f) => {
      if (activeCat !== "all" && (f.category || "facts") !== activeCat) return false;
      if (q && String(f.content || "").toLowerCase().indexOf(q) < 0 &&
          String(f.category || "").toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
  }

  function emptyNode() {
    const d = document.createElement("div");
    d.className = "mem-empty";
    d.id = "memory-empty";
    d.innerHTML =
      '<div class="mem-empty-orb orb" aria-hidden="true"><i class="core"></i></div>' +
      '<div class="mem-empty-title">Nothing remembered yet</div>' +
      '<p class="mem-empty-sub">Tell Jarvis &ldquo;remember that &hellip;&rdquo; and the fact will appear here &mdash; searchable, editable, and easy to forget.</p>';
    return d;
  }

  function render() {
    const facts = visible();
    list.innerHTML = "";
    if (!facts.length) {
      const e = emptyNode();
      if ((state.facts || []).length && (query || activeCat !== "all")) {
        e.querySelector(".mem-empty-title").textContent = "No matching memories";
        e.querySelector(".mem-empty-sub").textContent =
          "Nothing matches this filter yet. Try another category or clear the search.";
      }
      list.appendChild(e);
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "mem-cards";
    facts.forEach((f) => {
      const card = document.createElement("article");
      card.className = "mem-card";
      card.dataset.id = f.id || "";
      card.innerHTML =
        '<div class="mem-card-top">' +
        '<span class="mem-badge ' + escapeHtml(f.category || "facts") + '">' +
        escapeHtml(LABELS[f.category] || f.category || "Facts") + "</span>" +
        '<span class="mem-actions">' +
        '<button class="mem-edit" type="button" title="Edit this fact" aria-label="Edit this fact">' +
        '<svg class="ic"><use href="#i-edit"/></svg></button>' +
        '<button class="mem-forget" type="button" title="Forget this fact" aria-label="Forget this fact">' +
        '<svg class="ic"><use href="#i-trash"/></svg></button>' +
        "</span>" +
        "</div>" +
        '<p class="mem-content"></p>' +
        '<div class="mem-meta"><span class="mem-time"></span></div>';
      card.querySelector(".mem-content").textContent = f.content || "";
      card.querySelector(".mem-time").textContent =
        when(f.created_at) + (f.updated_at ? " · edited" : "");
      if (editing && editing.id === f.id) openEditor(card, editing.draft);
      wrap.appendChild(card);
    });
    list.appendChild(wrap);
  }

  function openEditor(card, draft) {
    const p = card.querySelector(".mem-content");
    if (!p || card.querySelector(".mem-editor")) return;
    card.classList.add("editing");
    const box = document.createElement("div");
    box.className = "mem-editor";
    const ta = document.createElement("textarea");
    ta.className = "mem-edit-text";
    ta.rows = 2;
    ta.value = draft;
    ta.setAttribute("aria-label", "Edit memory");
    const row = document.createElement("div");
    row.className = "mem-edit-actions";
    const save = document.createElement("button");
    save.type = "button";
    save.className = "mem-edit-save";
    save.textContent = "Save";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "mem-edit-cancel";
    cancel.textContent = "Cancel";
    const hint = document.createElement("span");
    hint.className = "mem-edit-hint";
    hint.innerHTML = "<kbd>Enter</kbd> save &middot; <kbd>Esc</kbd> cancel";
    row.appendChild(hint);
    row.appendChild(cancel);
    row.appendChild(save);
    box.appendChild(ta);
    box.appendChild(row);
    p.replaceWith(box);
    ta.addEventListener("input", () => { if (editing) editing.draft = ta.value; });
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); commitEdit(card.dataset.id, ta.value); }
      else if (e.key === "Escape") { e.preventDefault(); cancelEdit(); }
    });
    save.onclick = () => commitEdit(card.dataset.id, ta.value);
    cancel.onclick = cancelEdit;
    setTimeout(() => { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); }, 0);
  }

  function startEdit(id) {
    const fact = (state.facts || []).find((f) => f.id === id);
    if (!fact) return;
    editing = { id: id, draft: fact.content || "" };
    render();
  }
  function cancelEdit() {
    editing = null;
    render();
  }
  function commitEdit(id, text) {
    const content = String(text || "").trim();
    const fact = (state.facts || []).find((f) => f.id === id);
    editing = null;
    if (!fact || !content || content === fact.content) { render(); return; }
    fact.content = content; // optimistic; the full-state reply corrects it
    render();
    Jarvis.send({ type: "memory.update", payload: { id: id, content: content } });
  }

  function applyState(s) {
    if (!s) return;
    if (s.facts) state.facts = s.facts;
    if (s.profile) state.profile = s.profile;
    render();
  }

  function load() {
    Jarvis.send({ type: "memory.list" });
  }

  ["memory.list", "memory.add", "memory.update", "memory.delete", "memory.clear", "memory.updated"].forEach((t) => {
    Jarvis.on(t, (d) => applyState(d.payload));
  });

  document.addEventListener("jarvis:connected", load);
  load();

  // ---- filters + search ----
  if (filters) {
    filters.addEventListener("click", (e) => {
      const b = e.target.closest(".mem-chip");
      if (!b) return;
      activeCat = b.dataset.cat || "all";
      filters.querySelectorAll(".mem-chip").forEach((c) => c.classList.toggle("active", c === b));
      render();
    });
  }
  if (search) {
    search.addEventListener("input", () => {
      query = search.value || "";
      render();
    });
  }

  // ---- add fact ----
  function setAddOpen(open) {
    if (!addForm) return;
    addForm.hidden = !open;
    if (open && addText) {
      addText.focus();
    } else if (addText) {
      addText.value = "";
    }
  }
  if (addBtn) addBtn.onclick = () => setAddOpen(addForm.hidden);
  if (addCancel) addCancel.onclick = () => setAddOpen(false);
  if (addForm) {
    addForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const content = (addText.value || "").trim();
      if (!content) return;
      Jarvis.send({ type: "memory.add", payload: { content: content, category: addCat.value } });
      setAddOpen(false);
    });
  }

  // ---- forget + instant undo ----
  function showToast(text) {
    if (!toast) return;
    toastText.textContent = text;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.hidden = true;
      lastDeleted = null;
    }, 6000);
  }
  if (list) {
    list.addEventListener("click", (e) => {
      const ed = e.target.closest(".mem-edit");
      if (ed) {
        const c = ed.closest(".mem-card");
        if (c && c.dataset.id) startEdit(c.dataset.id);
        return;
      }
      const btn = e.target.closest(".mem-forget");
      if (!btn) return;
      const card = btn.closest(".mem-card");
      const id = card && card.dataset.id;
      const fact = (state.facts || []).find((f) => f.id === id);
      if (!fact) return;
      lastDeleted = { content: fact.content, category: fact.category };
      Jarvis.send({ type: "memory.delete", payload: { id: id } });
      showToast("Memory forgotten.");
    });
  }
  if (undoBtn) {
    undoBtn.onclick = () => {
      if (!lastDeleted) return;
      Jarvis.send({
        type: "memory.add",
        payload: { content: lastDeleted.content, category: lastDeleted.category },
      });
      lastDeleted = null;
      if (toast) toast.hidden = true;
      clearTimeout(toastTimer);
    };
  }

  // ---- clear all ----
  if (clearBtn) {
    clearBtn.onclick = () => {
      if (!(state.facts || []).length) return;
      if (!window.confirm("Forget everything Jarvis has remembered?")) return;
      lastDeleted = null;
      Jarvis.send({ type: "memory.clear", payload: {} });
    };
  }

  // ---- export ----
  if (exportBtn) {
    exportBtn.onclick = () => {
      try {
        const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "jarvis-memory.json";
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
          URL.revokeObjectURL(a.href);
          a.remove();
        }, 1000);
      } catch (e) {
        /* export is best-effort */
      }
    };
  }
})();
