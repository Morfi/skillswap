// SkillSwap — одностраничный клиент без сборки. Общается с API через /api (проксирует nginx).

const state = { token: localStorage.getItem("token"), user: null, categories: [], view: "catalog" };

const LABELS = {
  kind: { offer: "Научу", want: "Хочу научиться" },
  level: { beginner: "Начальный", intermediate: "Средний", expert: "Эксперт" },
  format: { online: "Онлайн", offline: "Офлайн", both: "Онлайн и офлайн" },
  status: { pending: "Ожидает", accepted: "Принята", declined: "Отклонена", completed: "Завершена", cancelled: "Отменена" },
  category: {
    languages: "Языки", music: "Музыка", it: "IT", sport: "Спорт", art: "Искусство", cooking: "Кулинария",
    science: "Наука", crafts: "Рукоделие", business: "Бизнес", other: "Другое",
  },
};

const $ = (sel) => document.querySelector(sel);
const app = $("#app");

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function toast(msg, error = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (error ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), 2800);
}

async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(`/api${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401 && state.token) {
    logout();
    throw new Error("Сессия истекла, войдите снова");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join("; ") : data.detail;
    throw new Error(detail || `Ошибка ${res.status}`);
  }
  return data;
}

async function safe(fn) {
  try {
    await fn();
  } catch (e) {
    toast(e.message, true);
  }
}

function options(map, selected, withEmpty) {
  const empty = withEmpty ? `<option value="">${withEmpty}</option>` : "";
  const entries = Array.isArray(map) ? map : Object.entries(map);
  return empty + entries.map(([v, l]) => `<option value="${v}" ${v === selected ? "selected" : ""}>${l}</option>`).join("");
}

// ---------------- modal ----------------
function openModal(html, onSubmit) {
  const dlg = $("#modal");
  const form = $("#modal-form");
  form.innerHTML = html + `<div class="modal-actions"><button type="button" class="ghost" id="m-cancel">Отмена</button><button type="submit">Сохранить</button></div>`;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    try {
      await onSubmit(data);
      dlg.close();
    } catch (err) {
      toast(err.message, true);
    }
  };
  $("#m-cancel").onclick = () => dlg.close();
  dlg.showModal();
}

// ---------------- auth ----------------
function renderAuth(mode = "login") {
  $("#nav").classList.add("hidden");
  $("#userbox").classList.add("hidden");
  app.innerHTML = `
    <div class="auth">
      <div class="hero"><h1>🔁 SkillSwap</h1><p>Научу тому, что умею, — научусь тому, что хочу. Без денег, только обмен знаниями.</p></div>
      <div class="card">
        <div class="tabs">
          <button class="${mode === "login" ? "" : "ghost"}" id="tab-login">Вход</button>
          <button class="${mode === "register" ? "" : "ghost"}" id="tab-register">Регистрация</button>
        </div>
        <form id="auth-form">
          ${mode === "register" ? `<label>Имя</label><input name="username" required minlength="2"><label>Город</label><input name="city">` : ""}
          <label>Email</label><input name="email" type="email" required>
          <label>Пароль</label><input name="password" type="password" required minlength="6">
          <div class="modal-actions"><button type="submit">${mode === "login" ? "Войти" : "Создать аккаунт"}</button></div>
        </form>
        <p class="meta">Демо: anna@skillswap.dev / demo123 · Админ: admin@skillswap.dev / admin123</p>
      </div>
    </div>`;
  $("#tab-login").onclick = () => renderAuth("login");
  $("#tab-register").onclick = () => renderAuth("register");
  $("#auth-form").onsubmit = (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    safe(async () => {
      const res = await api(`/auth/${mode}`, { method: "POST", body: data });
      state.token = res.access_token;
      localStorage.setItem("token", state.token);
      await boot();
    });
  };
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("token");
  renderAuth();
}

// ---------------- skill card ----------------
function skillCard(s, { own = false, canRequest = false } = {}) {
  const isAdmin = state.user.role === "admin";
  return `
    <div class="card skill ${s.kind}">
      <div class="tags">
        <span class="tag ${s.kind}">${LABELS.kind[s.kind]}</span>
        <span class="tag">${LABELS.category[s.category] || s.category}</span>
        <span class="tag">${LABELS.level[s.level]}</span>
        <span class="tag">${LABELS.format[s.format]}</span>
        ${s.is_active ? "" : `<span class="tag">скрыто</span>`}
      </div>
      <h3>${esc(s.title)}</h3>
      ${s.description ? `<div>${esc(s.description)}</div>` : ""}
      ${own ? "" : `<div class="meta">👤 <a href="#" data-profile="${s.owner_id}">${esc(s.owner_name)}</a>${s.owner_city ? " · " + esc(s.owner_city) : ""}</div>`}
      <div class="actions">
        ${canRequest && s.kind === "offer" && s.owner_id !== state.user.id ? `<button class="small" data-request="${s.id}">Предложить обмен</button>` : ""}
        ${own ? `<button class="small ghost" data-edit-skill="${s.id}">Изменить</button>` : ""}
        ${own || (isAdmin && s.owner_id !== state.user.id) ? `<button class="small danger" data-del-skill="${s.id}">Удалить</button>` : ""}
      </div>
    </div>`;
}

function bindSkillActions(container, skills, reload) {
  container.querySelectorAll("[data-request]").forEach((b) => (b.onclick = () => requestExchange(+b.dataset.request)));
  container.querySelectorAll("[data-edit-skill]").forEach((b) => (b.onclick = () => skillForm(skills.find((s) => s.id === +b.dataset.editSkill), reload)));
  container.querySelectorAll("[data-del-skill]").forEach(
    (b) =>
      (b.onclick = () =>
        confirm("Удалить навык?") &&
        safe(async () => {
          await api(`/skills/${b.dataset.delSkill}`, { method: "DELETE" });
          toast("Навык удалён");
          reload();
        })),
  );
  container.querySelectorAll("[data-profile]").forEach((a) => (a.onclick = (e) => (e.preventDefault(), showProfile(+a.dataset.profile))));
}

function skillForm(skill, reload) {
  const s = skill || { kind: "offer", category: "other", level: "beginner", format: "online", is_active: true };
  const cats = Object.fromEntries(state.categories.map((c) => [c, LABELS.category[c] || c]));
  openModal(
    `<h2>${skill ? "Редактировать навык" : "Новый навык"}</h2>
     <label>Тип</label><select name="kind">${options(LABELS.kind, s.kind)}</select>
     <label>Название</label><input name="title" required minlength="2" value="${esc(s.title)}">
     <label>Категория</label><select name="category">${options(cats, s.category)}</select>
     <label>Уровень</label><select name="level">${options(LABELS.level, s.level)}</select>
     <label>Формат</label><select name="format">${options(LABELS.format, s.format)}</select>
     <label>Описание</label><textarea name="description" rows="3">${esc(s.description)}</textarea>
     <label><input type="checkbox" name="is_active" style="width:auto" ${s.is_active ? "checked" : ""}> Показывать в каталоге</label>`,
    async (data) => {
      const body = { ...data, is_active: data.is_active === "on" };
      await api(skill ? `/skills/${skill.id}` : "/skills", { method: skill ? "PUT" : "POST", body });
      toast(skill ? "Навык обновлён" : "Навык добавлен");
      reload();
    },
  );
}

async function requestExchange(requestedId, exchange) {
  const mine = await api("/skills?mine=true&kind=offer");
  const opts = [["", "— ничего конкретного —"], ...mine.map((s) => [String(s.id), s.title])];
  openModal(
    `<h2>${exchange ? "Изменить заявку" : "Предложить обмен"}</h2>
     <label>Что вы предложите взамен</label><select name="offered_skill_id">${options(opts, String(exchange?.offered_skill_id ?? ""))}</select>
     <label>Сообщение</label><textarea name="message" rows="4" placeholder="Расскажите о себе и удобном времени">${esc(exchange?.message)}</textarea>`,
    async (data) => {
      const body = { offered_skill_id: data.offered_skill_id ? +data.offered_skill_id : null, message: data.message };
      if (exchange) await api(`/exchanges/${exchange.id}`, { method: "PUT", body });
      else await api("/exchanges", { method: "POST", body: { ...body, requested_skill_id: requestedId } });
      toast(exchange ? "Заявка обновлена" : "Заявка отправлена");
      if (exchange) views.exchanges();
    },
  );
}

async function showProfile(id) {
  safe(async () => {
    const [u, skills] = await Promise.all([api(`/users/${id}`), api(`/users/${id}/skills`)]);
    app.innerHTML = `
      <button class="ghost" id="back">← Назад</button>
      <div class="card" style="margin-top:12px">
        <h1>${esc(u.username)}</h1>
        <div class="meta">${esc(u.city)} · Рейтинг: ${u.rating ? "⭐ " + u.rating + ` (${u.reviews})` : "пока нет оценок"}</div>
        <p>${esc(u.bio)}</p>
      </div>
      <h2>Навыки</h2><div class="grid" id="list">${skills.map((s) => skillCard(s, { canRequest: true })).join("") || '<div class="empty">Нет навыков</div>'}</div>`;
    $("#back").onclick = () => go(state.view);
    bindSkillActions(app, skills, () => showProfile(id));
  });
}

// ---------------- views ----------------
const views = {
  async catalog() {
    const cats = Object.fromEntries(state.categories.map((c) => [c, LABELS.category[c] || c]));
    app.innerHTML = `
      <h1>Каталог навыков</h1>
      <div class="toolbar">
        <input id="f-search" placeholder="Поиск…">
        <select id="f-kind">${options(LABELS.kind, "offer", "Все")}</select>
        <select id="f-category">${options(cats, "", "Все категории")}</select>
        <select id="f-level">${options(LABELS.level, "", "Любой уровень")}</select>
        <select id="f-format">${options(LABELS.format, "", "Любой формат")}</select>
        <input id="f-city" placeholder="Город">
      </div>
      <div class="grid" id="list"></div>`;
    const load = () =>
      safe(async () => {
        const params = new URLSearchParams();
        for (const k of ["search", "kind", "category", "level", "format", "city"]) {
          const v = $(`#f-${k}`).value.trim();
          if (v) params.set(k, v);
        }
        const skills = await api(`/skills?${params}`);
        const list = $("#list");
        list.innerHTML = skills.map((s) => skillCard(s, { canRequest: true })).join("") || '<div class="empty">Ничего не найдено</div>';
        bindSkillActions(list, skills, load);
      });
    app.querySelectorAll(".toolbar input, .toolbar select").forEach((el) => (el.oninput = load));
    load();
  },

  async matches() {
    const matches = await api("/skills/matches");
    app.innerHTML = `
      <h1>Подбор партнёров</h1>
      <p class="meta">Люди, которые умеют то, чему вы хотите научиться, и/или хотят научиться тому, что умеете вы. Взаимные совпадения — сверху.</p>
      <div id="list"></div>`;
    const list = $("#list");
    if (!matches.length) {
      list.innerHTML = `<div class="empty card">Совпадений пока нет. Добавьте навыки «Научу» и «Хочу научиться» в разделе «Мои навыки».</div>`;
      return;
    }
    list.innerHTML = matches
      .map(
        (m) => `
      <div class="card match" style="margin-bottom:14px">
        <div class="head">
          <div><b><a href="#" data-profile="${m.user.id}">${esc(m.user.username)}</a></b> <span class="meta">${esc(m.user.city)} ${m.user.rating ? "· ⭐ " + m.user.rating : ""}</span></div>
          <span class="badge">${m.mutual ? "🤝 Взаимный обмен" : "Частичное совпадение"} · ${m.score}</span>
        </div>
        <div><div class="meta">Может научить вас</div>${m.they_offer.map((s) => skillCard(s, { canRequest: true })).join("") || '<div class="meta">—</div>'}</div>
        <div><div class="meta">Хочет научиться у вас</div>${m.they_want.map((s) => skillCard(s)).join("") || '<div class="meta">—</div>'}</div>
      </div>`,
      )
      .join("");
    bindSkillActions(list, matches.flatMap((m) => m.they_offer), views.matches);
  },

  async skills() {
    const skills = await api("/skills?mine=true");
    app.innerHTML = `
      <h1>Мои навыки</h1>
      <div class="toolbar"><button id="add">+ Добавить навык</button></div>
      <h2>Научу</h2><div class="grid" id="offers"></div>
      <h2>Хочу научиться</h2><div class="grid" id="wants"></div>`;
    const reload = () => views.skills();
    for (const [id, kind] of [["offers", "offer"], ["wants", "want"]]) {
      const part = skills.filter((s) => s.kind === kind);
      $(`#${id}`).innerHTML = part.map((s) => skillCard(s, { own: true })).join("") || '<div class="empty">Пока пусто</div>';
    }
    bindSkillActions(app, skills, reload);
    $("#add").onclick = () => skillForm(null, reload);
  },

  async exchanges() {
    const dir = views.exchanges.dir || "all";
    const list = await api(`/exchanges?direction=${dir}`);
    app.innerHTML = `
      <h1>Обмены</h1>
      <div class="toolbar">
        <select id="dir">${options({ all: "Все", incoming: "Входящие", outgoing: "Исходящие" }, dir)}</select>
      </div>
      <div id="list"></div>`;
    $("#dir").onchange = (e) => ((views.exchanges.dir = e.target.value), views.exchanges());
    $("#list").innerHTML = list.length ? exchangeTable(list) : '<div class="empty card">Заявок пока нет. Найдите партнёра в каталоге или подборе.</div>';
    bindExchangeActions(list);
  },

  async profile() {
    const u = state.user;
    app.innerHTML = `
      <h1>Профиль</h1>
      <div class="card">
        <div class="meta">${esc(u.email)} · роль: ${u.role}</div>
        <form id="profile-form">
          <label>Имя</label><input name="username" value="${esc(u.username)}" required minlength="2">
          <label>Город</label><input name="city" value="${esc(u.city)}">
          <label>О себе</label><textarea name="bio" rows="4">${esc(u.bio)}</textarea>
          <div class="modal-actions"><button type="submit">Сохранить</button></div>
        </form>
      </div>`;
    $("#profile-form").onsubmit = (e) => {
      e.preventDefault();
      safe(async () => {
        state.user = await api("/auth/me", { method: "PUT", body: Object.fromEntries(new FormData(e.target).entries()) });
        $("#username").textContent = state.user.username;
        toast("Профиль сохранён");
      });
    };
  },

  async admin() {
    const [stats, users, exchanges] = await Promise.all([api("/admin/stats"), api("/admin/users"), api("/exchanges?all_users=true")]);
    app.innerHTML = `
      <h1>Администрирование</h1>
      <div class="stats">
        <div class="card stat"><b>${stats.users}</b>пользователей</div>
        <div class="card stat"><b>${stats.skills}</b>навыков</div>
        <div class="card stat"><b>${stats.exchanges}</b>обменов</div>
        <div class="card stat"><b>${stats.exchanges_by_status.completed || 0}</b>завершено</div>
      </div>
      <h2>Пользователи</h2>
      <div style="overflow-x:auto"><table>
        <tr><th>ID</th><th>Имя</th><th>Email</th><th>Город</th><th>Роль</th><th>Статус</th><th></th></tr>
        ${users
          .map(
            (u) => `<tr>
          <td>${u.id}</td><td><a href="#" data-profile="${u.id}">${esc(u.username)}</a></td><td>${esc(u.email)}</td><td>${esc(u.city)}</td>
          <td>${u.id === state.user.id ? u.role : `<select data-role="${u.id}">${options({ user: "user", admin: "admin" }, u.role)}</select>`}</td>
          <td>${u.is_blocked ? '<span class="badge status-declined">заблокирован</span>' : '<span class="badge status-completed">активен</span>'}</td>
          <td>${u.id === state.user.id ? "" : `<button class="small ghost" data-block="${u.id}" data-val="${!u.is_blocked}">${u.is_blocked ? "Разблокировать" : "Заблокировать"}</button>
              <button class="small danger" data-del-user="${u.id}">Удалить</button>`}</td></tr>`,
          )
          .join("")}
      </table></div>
      <h2>Все обмены</h2>
      <div id="list">${exchanges.length ? exchangeTable(exchanges, true) : '<div class="empty card">Нет обменов</div>'}</div>`;
    app.querySelectorAll("[data-role]").forEach(
      (s) => (s.onchange = () => safe(async () => (await api(`/admin/users/${s.dataset.role}/role`, { method: "PATCH", body: { role: s.value } }), toast("Роль изменена")))),
    );
    app.querySelectorAll("[data-block]").forEach(
      (b) =>
        (b.onclick = () =>
          safe(async () => {
            await api(`/admin/users/${b.dataset.block}/block`, { method: "PATCH", body: { is_blocked: b.dataset.val === "true" } });
            views.admin();
          })),
    );
    app.querySelectorAll("[data-del-user]").forEach(
      (b) =>
        (b.onclick = () =>
          confirm("Удалить пользователя со всеми его навыками и обменами?") &&
          safe(async () => {
            await api(`/admin/users/${b.dataset.delUser}`, { method: "DELETE" });
            toast("Пользователь удалён");
            views.admin();
          })),
    );
    app.querySelectorAll("[data-profile]").forEach((a) => (a.onclick = (e) => (e.preventDefault(), showProfile(+a.dataset.profile))));
    bindExchangeActions(exchanges, views.admin);
  },
};

// ---------------- exchanges ----------------
function exchangeTable(list, adminView = false) {
  return `<div style="overflow-x:auto"><table>
    <tr><th>#</th><th>От кого</th><th>Кому</th><th>Хочет научиться</th><th>Предлагает</th><th>Сообщение</th><th>Статус</th><th>Оценки</th><th></th></tr>
    ${list.map((e) => `<tr>
      <td>${e.id}</td><td>${esc(e.requester_name)}</td><td>${esc(e.receiver_name)}</td>
      <td>${esc(e.requested_skill_title) || "—"}</td><td>${esc(e.offered_skill_title) || "—"}</td>
      <td>${esc(e.message)}</td>
      <td><span class="badge status-${e.status}">${LABELS.status[e.status]}</span></td>
      <td>${e.requester_rating ? "⭐" + e.requester_rating : "—"} / ${e.receiver_rating ? "⭐" + e.receiver_rating : "—"}</td>
      <td><div class="actions">${exchangeButtons(e, adminView)}</div></td></tr>`).join("")}
  </table></div>`;
}

function exchangeButtons(e, adminView) {
  const me = state.user.id;
  const isReq = e.requester_id === me;
  const isRec = e.receiver_id === me;
  const b = [];
  const btn = (label, action, cls = "") => b.push(`<button class="small ${cls}" data-ex="${e.id}" data-action="${action}">${label}</button>`);
  if (e.status === "pending" && isRec) btn("Принять", "accepted", "ok"), btn("Отклонить", "declined", "danger");
  if (e.status === "pending" && isReq) btn("Изменить", "edit", "ghost"), btn("Отменить", "cancelled", "ghost");
  if (e.status === "accepted" && (isReq || isRec)) btn("Завершить", "completed", "ok"), btn("Отменить", "cancelled", "ghost");
  if (e.status === "completed" && ((isReq && !e.requester_rating) || (isRec && !e.receiver_rating))) btn("Оценить", "rate");
  if ((isReq && ["pending", "declined", "cancelled"].includes(e.status)) || (adminView && state.user.role === "admin")) btn("Удалить", "delete", "danger");
  return b.join("");
}

function bindExchangeActions(list, reload = views.exchanges) {
  app.querySelectorAll("[data-ex]").forEach((btn) => {
    btn.onclick = () => {
      const id = +btn.dataset.ex;
      const action = btn.dataset.action;
      if (action === "edit") return requestExchange(null, list.find((e) => e.id === id));
      if (action === "rate") {
        return openModal(
          `<h2>Оцените партнёра</h2><label>Оценка</label><select name="rating">${options({ 5: "⭐⭐⭐⭐⭐", 4: "⭐⭐⭐⭐", 3: "⭐⭐⭐", 2: "⭐⭐", 1: "⭐" }, "5")}</select>`,
          async (d) => (await api(`/exchanges/${id}/rate`, { method: "POST", body: { rating: +d.rating } }), toast("Спасибо за оценку!"), reload()),
        );
      }
      if (action === "delete") {
        if (!confirm("Удалить заявку?")) return;
        return safe(async () => (await api(`/exchanges/${id}`, { method: "DELETE" }), toast("Заявка удалена"), reload()));
      }
      safe(async () => (await api(`/exchanges/${id}/status`, { method: "PATCH", body: { status: action } }), toast("Статус обновлён"), reload()));
    };
  });
}

// ---------------- routing ----------------
function go(view) {
  state.view = view;
  document.querySelectorAll("#nav button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  safe(() => views[view]());
}

async function boot() {
  if (!state.token) return renderAuth();
  try {
    [state.user, state.categories] = await Promise.all([api("/auth/me"), api("/skills/categories")]);
  } catch (e) {
    return logout();
  }
  $("#nav").classList.remove("hidden");
  $("#userbox").classList.remove("hidden");
  $("#username").textContent = state.user.username;
  $("#rolebadge").textContent = state.user.role;
  document.querySelectorAll(".admin-only").forEach((el) => el.classList.toggle("hidden", state.user.role !== "admin"));
  go("catalog");
}

document.querySelectorAll("#nav button").forEach((b) => (b.onclick = () => go(b.dataset.view)));
$("#logout").onclick = logout;
boot();
