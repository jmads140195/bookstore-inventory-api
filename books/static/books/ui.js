"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const SESSION_KEY = "estante.session.v1";
  const state = {token: null, user: null, expires: null, books: [], page: 1, query: "", category: "", stock: "all", total: 0,
    currency: document.body.dataset.currency, editing: null, listVersion: 0, generation: 0};
  let listController, searchTimer, toastTimer, expiryTimer;
  const editable = () => state.user?.role === "full";
  const count = (value) => new Intl.NumberFormat("es-ES").format(value);
  const date = (value) => value ? new Intl.DateTimeFormat("es", {dateStyle: "medium", timeStyle: "short"}).format(new Date(value)) : "Sin fecha de publicación";
  function money(value, currency = state.currency) {
    if (value === null || value === undefined) return "Sin calcular";
    // Preserve Decimal cents even for amounts beyond JavaScript's safe integer range.
    const [whole, cents = ""] = String(value).split(".");
    return `${new Intl.NumberFormat("es-ES").format(BigInt(whole))},${cents.padEnd(2, "0")} ${currency}`;
  }
  const rateText = (value) => String(value).replace(/(\.\d*?[1-9])0+$|\.0+$/, "$1").replace(".", ",");
  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function icon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS(svg.namespaceURI, "use");
    use.setAttribute("href", `#i-${name}`);
    svg.append(use);
    return svg;
  }
  function alertAt(id, message = "") { $(id).textContent = message; $(id).hidden = !message; }
  function toast(message) {
    clearTimeout(toastTimer); $("toast").textContent = message; $("toast").hidden = false;
    toastTimer = setTimeout(() => { $("toast").hidden = true; }, 5500);
  }
  function errorMessage(error) { return error.message || "No pudimos completar la operación. Inténtalo de nuevo."; }
  async function busy(button, label, operation) {
    const children = Array.from(button.childNodes).map((child) => child.cloneNode(true));
    button.disabled = true; button.textContent = label;
    try { return await operation(); }
    finally { button.replaceChildren(...children); button.disabled = false; }
  }
  function clearSession(message = "") {
    state.generation++; state.listVersion++; listController?.abort();
    clearTimeout(expiryTimer); clearTimeout(searchTimer); clearTimeout(toastTimer);
    state.token = null; state.user = null; state.books = []; state.editing = null; state.expires = null;
    try { sessionStorage.removeItem(SESSION_KEY); } catch (_) { /* Storage may be disabled. */ }
    document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
    $("app-screen").hidden = true; $("login-screen").hidden = false; $("toast").hidden = true;
    $("book-rows").replaceChildren(); $("book-form").reset(); $("price-breakdown").replaceChildren();
    $("password").value = ""; $("password").type = "password";
    $("toggle-password").setAttribute("aria-pressed", "false"); $("toggle-password").setAttribute("aria-label", "Mostrar contraseña");
    alertAt("login-error", message);
  }
  async function api(path, {method = "GET", body, signal} = {}) {
    const token = state.token;
    const headers = {Accept: "application/json"};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let response;
    try { response = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal, credentials: "omit", cache: "no-store"}); }
    catch (cause) {
      if (cause.name === "AbortError") throw cause;
      throw new Error("No pudimos conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.");
    }
    if (response.status === 204) return null;
    let data;
    try { data = await response.json(); } catch (_) { data = {}; }
    if (!response.ok) {
      const error = new Error(data.error?.message || `No pudimos procesar la petición (${response.status}).`);
      error.status = response.status; error.details = data.error?.details;
      if (response.status === 429) error.message = `Has alcanzado el límite de peticiones. Inténtalo de nuevo en ${response.headers.get("Retry-After") || "unos"} segundos.`;
      if (response.status === 401 && path !== "/auth/login" && token === state.token) clearSession("Tu sesión venció o fue revocada. Inicia sesión de nuevo.");
      throw error;
    }
    return data;
  }
  function rememberSession(token, expires) {
    state.token = token; state.expires = expires;
    try { sessionStorage.setItem(SESSION_KEY, JSON.stringify({token, expires})); } catch (_) { /* In-memory session remains usable. */ }
    clearTimeout(expiryTimer);
    expiryTimer = setTimeout(() => clearSession("Tu sesión ha vencido. Inicia sesión de nuevo."), Math.max(0, new Date(expires).getTime() - Date.now()));
  }
  function showWorkspace(user) {
    state.user = user; state.page = 1; state.query = ""; state.category = ""; state.stock = "all";
    $("login-screen").hidden = true; $("app-screen").hidden = false; $("password").value = "";
    $("user-name").textContent = user.first_name || user.username;
    $("user-role").textContent = editable() ? "Acceso completo" : "Solo consulta";
    $("user-avatar").textContent = (user.first_name || user.username).slice(0, 2).toUpperCase();
    $("greeting").textContent = `HOLA, ${user.first_name || user.username}`.toUpperCase();
    $("readonly-note").hidden = editable();
    document.querySelectorAll("[data-full]").forEach((element) => { element.hidden = !editable(); });
    $("book-search").value = ""; $("category-filter").value = ""; updateTabs();
    for (const id of ["stat-titles", "stat-units", "stat-low", "stat-unpriced", "sidebar-count"]) $(id).textContent = "—";
    $("rate-value").textContent = "Consultando la tasa de cambio…"; alertAt("app-error");
  }
  async function login(event) {
    event.preventDefault(); alertAt("login-error");
    await busy($("login-submit"), "Entrando…", async () => {
      try {
        const result = await api("/auth/login", {method: "POST", body: {username: $("username").value.trim(), password: $("password").value}});
        rememberSession(result.token, result.expires_at); showWorkspace(result.user); await reloadAll();
      } catch (error) { alertAt("login-error", error.status === 401 ? "El usuario o la contraseña no son correctos." : errorMessage(error)); }
    });
  }
  async function logout() {
    await busy($("logout-button"), "…", async () => {
      let message = "";
      try { await api("/auth/logout", {method: "POST"}); }
      catch (error) { if (error.status !== 401) message = "Cerramos la sesión en este navegador, pero no pudimos revocarla en el servidor. El token caducará a las 8 horas de su emisión."; }
      clearSession(message); $("username").focus();
    });
  }
  async function loadOverview() {
    const generation = state.generation;
    const summary = await api("/books/overview");
    if (!state.user || state.generation !== generation) return;
    state.currency = summary.currency; $("price-heading").textContent = `Venta · ${state.currency}`;
    for (const [id, field] of [["stat-titles", "total_titles"], ["stat-units", "total_units"], ["stat-low", "low_stock"], ["stat-unpriced", "unpriced"], ["sidebar-count", "total_titles"]]) $(id).textContent = count(summary[field]);
    const select = $("category-filter"); select.replaceChildren(new Option("Todas las categorías", ""));
    const categories = [...summary.categories];
    if (state.category && !categories.includes(state.category)) categories.push(state.category);
    for (const category of categories) select.add(new Option(category, category));
    select.value = state.category;
    $("category-suggestions").replaceChildren(...summary.categories.map((category) => { const option = document.createElement("option"); option.value = category; return option; }));
  }
  async function loadRate() {
    const generation = state.generation;
    try {
      const rate = await api("/rates/current");
      if (!state.user || generation !== state.generation) return;
      $("rate-value").textContent = `1 USD = ${rateText(rate.exchange_rate)} ${rate.currency} · Recargo del 40 %`;
      $("rate-date").textContent = rate.provider_updated_at ? `Cotización publicada el ${date(rate.provider_updated_at)}. Actualización programada: 08:00 y 15:00 de Caracas.` : "Tasa de respaldo inicial, sin cotización del proveedor disponible.";
      alertAt("rate-warning", rate.warning || "");
    } catch (error) {
      if (state.user && generation === state.generation) {
        $("rate-value").textContent = "Tasa no disponible"; $("rate-date").textContent = "Puedes seguir gestionando el inventario. El cálculo necesita una tasa utilizable.";
        alertAt("rate-warning", errorMessage(error));
      }
    }
  }
  async function reloadAll() {
    alertAt("app-error");
    const results = await Promise.allSettled([loadBooks(), loadOverview(), loadRate()]);
    for (const result of results) if (result.status === "rejected" && state.user && result.reason.name !== "AbortError") alertAt("app-error", errorMessage(result.reason));
  }
  function updateTabs() {
    document.querySelectorAll("[data-stock]").forEach((button) => {
      const selected = button.dataset.stock === state.stock;
      button.classList.toggle("selected", selected); button.setAttribute("aria-pressed", String(selected));
    });
  }
  async function loadBooks() {
    const version = ++state.listVersion;
    listController?.abort(); listController = new AbortController();
    $("list-status").textContent = "Buscando…"; $("book-rows").setAttribute("aria-busy", "true");
    $("previous-page").disabled = true; $("next-page").disabled = true;
    const query = new URLSearchParams({page: String(state.page), stock: state.stock});
    if (state.query) query.set("q", state.query);
    if (state.category) query.set("category", state.category);
    try {
      const result = await api(`/books?${query}`, {signal: listController.signal});
      if (!state.user || version !== state.listVersion) return;
      state.books = result.results; state.total = result.count;
      renderBooks(); $("catalog-count").textContent = count(result.count);
      $("previous-page").disabled = !result.previous; $("next-page").disabled = !result.next;
      const first = result.count ? (state.page - 1) * 20 + 1 : 0;
      $("pagination-info").textContent = `${first}–${first ? first + result.results.length - 1 : 0} de ${count(result.count)} libros`;
      $("page-number").textContent = `Página ${state.page}`;
      $("list-status").textContent = `${count(result.count)} resultados`;
    } catch (error) {
      if (error.name === "AbortError" || version !== state.listVersion || !state.user) return;
      if (error.status === 404 && state.page > 1) { state.page = 1; return loadBooks(); }
      $("list-status").textContent = "No se pudo cargar";
      alertAt("app-error", errorMessage(error));
    } finally { if (version === state.listVersion) $("book-rows").setAttribute("aria-busy", "false"); }
  }
  function actionButton(label, symbol, action) {
    const button = node("button", "icon-button"); button.type = "button"; button.title = label; button.setAttribute("aria-label", label);
    button.append(icon(symbol)); button.addEventListener("click", action); return button;
  }
  function renderBooks() {
    const fragment = document.createDocumentFragment();
    for (const book of state.books) {
      const row = node("tr"); row.dataset.bookId = book.id;
      const identity = node("td", "book-identity"), cell = node("div", "book-cell");
      const cover = node("span", `book-cover cover-${book.id % 4}`, book.title.slice(0, 1).toUpperCase()); cover.setAttribute("aria-hidden", "true");
      const text = node("div", "book-text");
      text.append(node("strong", "book-name", book.title), node("span", "book-author", book.author), node("span", "book-isbn", `ISBN ${book.isbn}`));
      cell.append(cover, text); identity.append(cell);
      const category = node("td", "book-category-cell"); category.append(node("span", "category-tag", book.category));
      const stockClass = book.stock_quantity === 0 ? "stock-out" : book.stock_quantity < 10 ? "stock-low" : "stock-ok";
      const stock = node("td", `book-stock-cell ${stockClass}`); stock.dataset.label = "Existencias";
      stock.append(node("span", "stock-number", `${count(book.stock_quantity)} ud.`), node("span", "stock-status", book.stock_quantity === 0 ? "Agotado" : book.stock_quantity < 10 ? "Stock bajo" : "Disponible"));
      const meter = node("div", "stock-meter"); meter.setAttribute("aria-hidden", "true"); meter.append(node("span")); stock.append(meter);
      const cost = node("td", "book-cost-cell"); cost.dataset.label = "Costo · USD"; cost.append(node("span", "money", money(book.cost_usd, "USD")));
      const sale = node("td", "book-sale-cell"); sale.dataset.label = `Venta · ${state.currency}`;
      sale.append(node("span", book.selling_price_local === null ? "no-price" : "money sale", money(book.selling_price_local)));
      const actionsCell = node("td", "book-actions-cell"), actions = node("div", "row-actions");
      if (editable()) actions.append(actionButton(`Calcular precio de ${book.title}`, "calc", () => calculatePrice(book)));
      actions.append(actionButton(`${editable() ? "Editar" : "Ver"} ${book.title}`, editable() ? "edit" : "eye", () => openBook(book)));
      actionsCell.append(actions); row.append(identity, category, stock, cost, sale, actionsCell); fragment.append(row);
    }
    $("book-rows").replaceChildren(fragment);
    const filtering = !!(state.query || state.category || state.stock !== "all");
    $("empty-state").hidden = state.books.length > 0;
    $("empty-title").textContent = filtering ? "No encontramos esos libros" : "Tu estante empieza aquí";
    $("empty-description").textContent = filtering ? "Prueba otra búsqueda o cambia los filtros del catálogo." : editable() ? "Añade tu primer libro para comenzar a organizar el inventario." : "Todavía no hay libros en el inventario. El administrador puede añadirlos.";
    $("empty-add").hidden = filtering || !editable(); $("clear-filters").hidden = !filtering;
  }
  function clearBookErrors() {
    alertAt("book-error");
    $("book-form").querySelectorAll(".field-error").forEach((element) => { element.textContent = ""; });
    $("book-form").querySelectorAll("[aria-invalid]").forEach((element) => element.removeAttribute("aria-invalid"));
  }
  function openBook(book = null) {
    if (!book && !editable()) return;
    state.editing = book; $("book-form").reset(); clearBookErrors();
    $("book-dialog-title").textContent = !editable() ? "Detalle del libro" : book ? "Editar libro" : "Añadir libro";
    $("book-dialog-intro").textContent = book ? `Libro #${book.id} · ${book.title}` : "Los pequeños detalles hacen un buen catálogo.";
    for (const name of ["title", "author", "isbn", "cost_usd", "stock_quantity", "category", "supplier_country"]) {
      const field = $("book-form").elements.namedItem(name); field.disabled = !editable();
      field.setAttribute("aria-describedby", name === "isbn" ? "isbn-help error-isbn" : `error-${name}`);
      field.value = book ? book[name] : name === "stock_quantity" ? 0 : "";
    }
    $("save-book").hidden = !editable(); $("delete-book").hidden = !editable() || !book;
    $("book-price-note").textContent = book ? `Precio de venta: ${money(book.selling_price_local)}. Al cambiar el costo tendrás que volver a calcular el precio.` : "El precio de venta se calcula después de guardar el libro, utilizando la tasa de cambio y el recargo del 40 %.";
    $("book-updated").textContent = book ? `Última modificación: ${date(book.updated_at)}` : "";
    $("book-dialog").showModal();
  }
  async function saveBook(event) {
    event.preventDefault(); if (!editable()) return; clearBookErrors();
    const editing = state.editing;
    const form = new FormData($("book-form"));
    const body = Object.fromEntries(["title", "author", "isbn", "category", "supplier_country"].map((name) => [name, String(form.get(name)).trim()]));
    body.cost_usd = String(form.get("cost_usd")).trim().replace(",", ".");
    body.stock_quantity = Number(form.get("stock_quantity"));
    $("book-dialog").dataset.busy = "true";
    await busy($("save-book"), "Guardando…", async () => {
      try {
        await api(editing ? `/books/${editing.id}` : "/books", {method: editing ? "PATCH" : "POST", body});
        $("book-dialog").close(); toast(editing ? "Cambios guardados." : "Libro añadido al inventario."); await reloadAll();
      } catch (error) {
        alertAt("book-error", errorMessage(error));
        if (error.details && typeof error.details === "object") {
          for (const [name, messages] of Object.entries(error.details)) {
            const display = $(`error-${name}`), field = $("book-form").elements.namedItem(name);
            if (display) display.textContent = Array.isArray(messages) ? messages.join(" ") : String(messages);
            if (field) field.setAttribute("aria-invalid", "true");
          }
          $("book-form").querySelector('[aria-invalid="true"]')?.focus();
        }
      }
    });
    $("book-dialog").dataset.busy = "false";
  }
  function askDelete() {
    if (!editable() || !state.editing) return;
    $("delete-book-name").textContent = state.editing.title; alertAt("delete-error"); $("delete-dialog").showModal();
  }
  async function deleteBook() {
    if (!editable() || !state.editing) return;
    const id = state.editing.id; $("delete-dialog").dataset.busy = "true";
    await busy($("confirm-delete"), "Eliminando…", async () => {
      try {
        await api(`/books/${id}`, {method: "DELETE"}); $("delete-dialog").close(); $("book-dialog").close();
        state.editing = null; state.page = 1; toast("Libro eliminado del inventario."); await reloadAll();
      } catch (error) { alertAt("delete-error", errorMessage(error)); }
    });
    $("delete-dialog").dataset.busy = "false";
  }
  async function calculatePrice(book) {
    if (!editable()) return;
    $("price-book-name").textContent = book.title; alertAt("price-error"); $("price-loading").hidden = false;
    $("price-result").hidden = true; $("price-dialog").showModal(); $("price-dialog").dataset.busy = "true";
    try {
      const result = await api(`/books/${book.id}/calculate-price`, {method: "POST"});
      if (!state.user) return;
      $("result-price").textContent = money(result.selling_price_local, result.currency);
      const rows = [["Costo original", money(result.cost_usd, "USD")], ["Tasa de cambio", `1 USD = ${rateText(result.exchange_rate)} ${result.currency}`],
        ["Costo convertido", money(result.cost_local, result.currency)], ["Recargo sobre el costo", `${result.margin_percentage} %`],
        ["Origen de la tasa", ({stored: "Cotización guardada", last_known: "Última cotización conocida", fallback: "Respaldo configurado"})[result.rate_source]],
        ["Publicación de la tasa", date(result.provider_updated_at)], ["Cálculo realizado", date(result.calculation_timestamp)]];
      $("price-breakdown").replaceChildren(...rows.map(([label, value]) => { const row = node("div"); row.append(node("dt", "", label), node("dd", "", value)); return row; }));
      alertAt("price-warning", result.warning || ""); $("price-result").hidden = false; await reloadAll();
    } catch (error) { alertAt("price-error", errorMessage(error)); }
    finally { $("price-loading").hidden = true; $("price-dialog").dataset.busy = "false"; }
  }
  $("login-form").addEventListener("submit", login);
  $("toggle-password").addEventListener("click", () => {
    const visible = $("password").type === "password"; $("password").type = visible ? "text" : "password";
    $("toggle-password").setAttribute("aria-pressed", String(visible)); $("toggle-password").setAttribute("aria-label", visible ? "Ocultar contraseña" : "Mostrar contraseña");
  });
  $("logout-button").addEventListener("click", logout);
  $("new-book").addEventListener("click", () => openBook()); $("empty-add").addEventListener("click", () => openBook());
  $("book-form").addEventListener("submit", saveBook); $("delete-book").addEventListener("click", askDelete); $("confirm-delete").addEventListener("click", deleteBook);
  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => { const dialog = $(button.dataset.close); if (dialog.dataset.busy !== "true") dialog.close(); }));
  document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("cancel", (event) => { if (dialog.dataset.busy === "true") event.preventDefault(); }));
  $("book-search").addEventListener("input", () => {
    clearTimeout(searchTimer); searchTimer = setTimeout(() => { state.query = $("book-search").value.trim(); state.page = 1; loadBooks(); }, 300);
  });
  $("category-filter").addEventListener("change", () => { state.category = $("category-filter").value; state.page = 1; loadBooks(); });
  document.querySelectorAll("[data-stock]").forEach((button) => button.addEventListener("click", () => { state.stock = button.dataset.stock; state.page = 1; updateTabs(); loadBooks(); }));
  $("clear-filters").addEventListener("click", () => { clearTimeout(searchTimer); state.query = ""; state.category = ""; state.stock = "all"; state.page = 1; $("book-search").value = ""; $("category-filter").value = ""; updateTabs(); loadBooks(); });
  $("previous-page").addEventListener("click", () => { state.page--; loadBooks(); });
  $("next-page").addEventListener("click", () => { state.page++; loadBooks(); });
  $("reload-button").addEventListener("click", () => busy($("reload-button"), "Actualizando…", reloadAll));
  $("refresh-rate").addEventListener("click", () => busy($("refresh-rate"), "Actualizando…", async () => {
    try {
      const result = await api("/rates/refresh", {method: "POST"}); await loadRate();
      toast(result.status === "updated" ? "Tasa de cambio actualizada." : "Hay otra actualización en curso. Vuelve a consultar en unos instantes.");
    } catch (error) { alertAt("rate-warning", errorMessage(error)); }
  }));
  (async () => {
    let saved;
    try { saved = JSON.parse(sessionStorage.getItem(SESSION_KEY)); } catch (_) { /* No stored session. */ }
    if (saved?.token && typeof saved.token === "string" && Number.isFinite(Date.parse(saved.expires)) && Date.parse(saved.expires) > Date.now()) {
      rememberSession(saved.token, saved.expires); $("login-submit").disabled = true;
      try { const user = await api("/auth/me"); showWorkspace(user); await reloadAll(); }
      catch (error) { clearSession(error.status === 401 ? "Tu sesión venció o fue revocada. Inicia sesión de nuevo." : errorMessage(error)); }
      finally { $("login-submit").disabled = false; }
    } else { clearSession(); }
  })();
})();
