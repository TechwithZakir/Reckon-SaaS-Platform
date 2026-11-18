frappe.pages["saas-dashboard"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("SaaS Dashboard"),
    single_column: true,
  });
  page.set_primary_action(__("Refresh"), () => load(), "refresh");
  page.add_inner_button(__("Classic Dashboard"), () => window.open("/reckon-saas-admin", "_blank"));
  page.add_inner_button(__("Public Signup"), () => window.open("/reckonerp-signup", "_blank"));

  const $body = $(page.body).addClass("rs-saas-dashboard");
  const esc = (value) => frappe.utils.escape_html(value == null ? "" : String(value));
  const route = (doctype, name) =>
    `/app/${frappe.router.slug(doctype)}${name ? "/" + encodeURIComponent(name) : ""}`;
  const link = (doctype, name, label) =>
    name ? `<a href="${route(doctype, name)}">${esc(label || name)}</a>` : "";
  const pill = (status) => `<span class="indicator-pill ${statusColor(status)}">${esc(status)}</span>`;

  function statusColor(status) {
    if (["Active", "Complete", "Verified", "Trial"].includes(status)) return "green";
    if (["Failed", "Expired", "Suspended", "Cancelled", "Rejected"].includes(status)) return "red";
    if (["Grace", "Due", "Dues", "Pending Payment", "Pending Verification", "Provisioning", "Running"].includes(status))
      return "orange";
    return "gray";
  }

  // Module label for a row; falls back to the key for rows of a removed module.
  const moduleName = (row) => (row.saas_module ? row.module_name || row.saas_module : "");
  const moduleCell = (row) => (row.saas_module ? link("SaaS Module", row.saas_module, moduleName(row)) : "");

  function billingText(b) {
    if (!b) return "";
    if (b.state === "trial") return __("Trial until {0}", [b.trial_end_date]);
    if (b.state === "active") return b.paid_until ? __("Paid until {0}", [b.paid_until]) : __("Active");
    if (b.state === "grace") return `${__("Dues")} ${__("grace until {0}", [b.grace_end])}`;
    return b.dues ? `${__("Dues")} ${__("locked")}` : __("Locked");
  }
  function billing(b) {
    if (!b) return "";
    if (b.state === "grace") return `${pill(__("Dues"))} ${esc(__("grace until {0}", [b.grace_end]))}`;
    if (b.state !== "trial" && b.state !== "active") return b.dues ? `${pill(__("Dues"))} ${esc(__("locked"))}` : esc(__("Locked"));
    return esc(billingText(b));
  }

  function card(label, value, doctype, filters) {
    const href = doctype ? `${route(doctype)}${filters ? "?" + filters : ""}` : "#";
    return `<a class="rs-card" href="${href}"><div class="rs-card-label">${esc(label)}</div>
      <div class="rs-card-value">${esc(value || 0)}</div></a>`;
  }

  /* ---------------------------------------------------------------- tables
     Every table has a search box, sortable headings (click again to reverse) and pages. The rows are kept as data,
     so searching, sorting and paging never rebuild the page and never lose what was typed. */

  const SIZES = [10, 25, 50, 100];
  const tables = {};
  const view = {}; // per table: { q, col, dir, page, size } survives a Refresh

  const num = (v) => (Number.isFinite(Number(v)) ? Number(v) : 0);
  const text = (v) => String(v == null ? "" : v).toLowerCase();

  function defineTable(id, title, cols, rows, empty) {
    tables[id] = { title, cols, rows, empty };
    view[id] = view[id] || { q: "", col: -1, dir: 1, page: 1, size: 10 };
    return `<section class="rs-panel" data-table="${id}">
      <header class="rs-panel-head">
        <h4>${esc(title)} <span class="rs-count" data-count></span></h4>
        <div class="rs-tools">
          <input type="search" class="form-control input-sm rs-search" data-q placeholder="${esc(__("Search"))}"
            aria-label="${esc(__("Search {0}", [title]))}" value="${esc(view[id].q)}">
          <select class="form-control input-sm rs-size" data-size aria-label="${esc(__("Rows per page"))}">
            ${SIZES.map((n) => `<option value="${n}"${n === view[id].size ? " selected" : ""}>${esc(__("{0} per page", [n]))}</option>`).join("")}
          </select>
        </div>
      </header>
      <div class="rs-table-wrap"><table class="table rs-table">
        <thead><tr>${cols
          .map((c, i) =>
            c.nosort
              ? `<th scope="col">${esc(c.label)}</th>`
              : `<th scope="col" aria-sort="none"><button type="button" class="rs-sort" data-col="${i}">${esc(c.label)}<span class="rs-arrow" aria-hidden="true"></span></button></th>`
          )
          .join("")}</tr></thead>
        <tbody data-body></tbody>
      </table></div>
      <footer class="rs-pager"><span class="rs-info" data-info></span><span class="rs-pages" data-pages></span></footer>
    </section>`;
  }

  function paint(id) {
    const $panel = $body.find(`[data-table="${id}"]`);
    const t = tables[id];
    if (!$panel.length || !t) return;
    const v = view[id];
    const q = v.q.trim().toLowerCase();
    let rows = t.rows;
    if (q) rows = rows.filter((r) => t.cols.some((c) => text(c.text ? c.text(r) : c.html(r)).includes(q)));
    if (v.col >= 0 && t.cols[v.col] && t.cols[v.col].sort) {
      const get = t.cols[v.col].sort;
      rows = rows.slice().sort((a, b) => {
        const x = get(a);
        const y = get(b);
        const r = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true, sensitivity: "base" });
        return r * v.dir;
      });
    }
    const pages = Math.max(1, Math.ceil(rows.length / v.size));
    v.page = Math.min(Math.max(1, v.page), pages);
    const from = (v.page - 1) * v.size;
    const slice = rows.slice(from, from + v.size);

    $panel.find("[data-body]").html(
      slice.length
        ? slice.map((r) => `<tr>${t.cols.map((c) => `<td>${c.html(r)}</td>`).join("")}</tr>`).join("")
        : `<tr><td colspan="${t.cols.length}" class="text-muted">${esc(q ? __("Nothing matches your search.") : t.empty)}</td></tr>`
    );
    $panel.find("[data-count]").text(q && rows.length !== t.rows.length ? `${rows.length} / ${t.rows.length}` : `${t.rows.length}`);
    $panel.find("th[aria-sort]").each(function () {
      const col = Number($(this).find("[data-col]").attr("data-col"));
      const active = col === v.col;
      $(this).attr("aria-sort", active ? (v.dir === 1 ? "ascending" : "descending") : "none");
      $(this).find(".rs-arrow").text(active ? (v.dir === 1 ? "▲" : "▼") : "");
    });
    $panel.find("[data-info]").text(
      rows.length ? __("{0}–{1} of {2}", [from + 1, from + slice.length, rows.length]) : __("0 rows")
    );
    $panel.find("[data-pages]").html(pager(v.page, pages));
    $panel.find(".rs-pager").toggleClass("is-single", pages <= 1);
  }

  function pager(current, pages) {
    if (pages <= 1) return "";
    const items = [];
    const add = (label, page, extra = "") =>
      items.push(`<button type="button" class="btn btn-xs btn-default rs-page ${extra}" data-page="${page}"${extra.includes("is-current") ? ' aria-current="page"' : ""}${extra.includes("is-off") ? " disabled" : ""}>${label}</button>`);
    add("‹", current - 1, current === 1 ? "is-off" : "");
    const near = new Set([1, pages, current - 1, current, current + 1]);
    let last = 0;
    [...near].filter((p) => p >= 1 && p <= pages).sort((a, b) => a - b).forEach((p) => {
      if (p - last > 1) items.push(`<span class="rs-gap">…</span>`);
      add(p, p, p === current ? "is-current btn-primary" : "");
      last = p;
    });
    add("›", current + 1, current === pages ? "is-off" : "");
    return items.join("");
  }

  $body.on("input", "[data-q]", function () {
    const id = $(this).closest("[data-table]").attr("data-table");
    view[id].q = this.value;
    view[id].page = 1;
    paint(id);
  });
  $body.on("change", "[data-size]", function () {
    const id = $(this).closest("[data-table]").attr("data-table");
    view[id].size = Number(this.value) || 10;
    view[id].page = 1;
    paint(id);
  });
  $body.on("click", ".rs-sort", function () {
    const id = $(this).closest("[data-table]").attr("data-table");
    const col = Number($(this).attr("data-col"));
    const v = view[id];
    v.dir = v.col === col ? -v.dir : 1;
    v.col = col;
    v.page = 1;
    paint(id);
  });
  $body.on("click", ".rs-page:not([disabled])", function () {
    const id = $(this).closest("[data-table]").attr("data-table");
    view[id].page = Number($(this).attr("data-page"));
    paint(id);
  });

  /* ---------------------------------------------------------------- page */

  function render(data) {
    const s = data.summary || {};
    const failed = (data.registrations || []).filter((r) => r.status === "Failed");
    const priceOf = (p) => `${p.currency || ""} ${p.price == null ? "" : p.price} / ${__(p.billing_cycle || "Monthly")}`.trim();
    $body.html(`
      <div class="rs-container">
      <div class="rs-cards">
        ${card(__("Modules for sale"), s.modules, "SaaS Module", "enabled=1")}
        ${card(__("Plans"), s.plans, "SaaS Plan")}
        ${card(__("Registrations"), s.registrations, "SaaS Registration")}
        ${card(__("Failed registrations"), s.registrations_failed, "SaaS Registration", "status=Failed")}
        ${card(__("Active subscriptions"), s.subscriptions_active, "SaaS Subscription")}
        ${card(__("Payments to verify"), s.payments_pending, "SaaS Payment", "status=Pending%20Verification")}
        ${card(__("Seed jobs open"), s.seed_jobs_pending, "Tenant Provisioning Job")}
      </div>
      ${defineTable(
        "modules",
        __("Modules"),
        [
          { label: __("Module"), sort: (m) => m.module_name || "", text: (m) => m.module_name, html: (m) => link("SaaS Module", m.module, m.module_name) },
          { label: __("Plans"), sort: (m) => num(m.plans), text: (m) => m.plans, html: (m) => `<a href="${route("SaaS Plan")}?saas_module=${encodeURIComponent(m.module)}">${esc(m.plans)}</a>` },
          { label: __("Registrations"), sort: (m) => num(m.registrations), text: (m) => m.registrations, html: (m) => `<a href="${route("SaaS Registration")}?saas_module=${encodeURIComponent(m.module)}">${esc(m.registrations)}</a>` },
          { label: __("Active subscriptions"), sort: (m) => num(m.active_subscriptions), text: (m) => m.active_subscriptions, html: (m) => `<a href="${route("SaaS Subscription")}?saas_module=${encodeURIComponent(m.module)}">${esc(m.active_subscriptions)}</a>` },
        ],
        data.module_stats || [],
        __("No modules registered yet. Run bench migrate after installing a product app.")
      )}
      ${defineTable(
        "plans",
        __("Plans"),
        [
          { label: __("Plan"), sort: (p) => p.plan_name || p.name || "", text: (p) => `${p.plan_name} ${p.name}`, html: (p) => link("SaaS Plan", p.name, p.plan_name) },
          { label: __("Module"), sort: (p) => moduleName(p), text: moduleName, html: (row) => moduleCell(row) },
          { label: __("Price"), sort: (p) => num(p.price), text: priceOf, html: (p) => esc(priceOf(p)) },
          { label: __("Trial days"), sort: (p) => num(p.trial_days), text: (p) => p.trial_days || 0, html: (p) => esc(p.trial_days || 0) },
          { label: __("Grace days"), sort: (p) => num(p.grace_days), text: (p) => p.grace_days || 0, html: (p) => esc(p.grace_days || 0) },
          { label: __("Enabled"), sort: (p) => (p.enabled ? 1 : 0), text: (p) => (p.enabled ? __("Yes") : __("No")), html: (p) => (p.enabled ? esc(__("Yes")) : esc(__("No"))) },
        ],
        data.plans || [],
        __("No plans yet.")
      )}
      ${defineTable(
        "payments",
        __("Payments to verify"),
        [
          { label: __("Payment"), sort: (p) => p.name, text: (p) => p.name, html: (p) => link("SaaS Payment", p.name) },
          { label: __("Company"), sort: (p) => p.company || "", text: (p) => p.company, html: (p) => esc(p.company) },
          { label: __("Module"), sort: (p) => moduleName(p), text: moduleName, html: (row) => moduleCell(row) },
          { label: __("Amount"), sort: (p) => num(p.amount), text: (p) => `${p.currency || ""} ${p.amount}`, html: (p) => `${esc(p.currency)} ${esc(p.amount)}` },
          {
            label: __("Reference"), sort: (p) => p.gateway_reference || "", text: (p) => p.gateway_reference,
            html: (p) => `<input class="form-control input-xs" data-reference="${esc(p.name)}" value="${esc(p.gateway_reference)}" placeholder="${esc(__("Reference"))}">`,
          },
          { label: __("Action"), nosort: true, html: (p) => `<button class="btn btn-xs btn-primary" data-verify="${esc(p.name)}">${esc(__("Verify"))}</button>` },
        ],
        data.pending_payments || [],
        __("No payments waiting.")
      )}
      ${defineTable(
        "failed",
        __("Failed registrations"),
        [
          { label: __("Registration"), sort: (r) => r.name, text: (r) => r.name, html: (r) => link("SaaS Registration", r.name) },
          { label: __("Business"), sort: (r) => r.business_name || "", text: (r) => r.business_name, html: (r) => esc(r.business_name) },
          { label: __("Module"), sort: (r) => moduleName(r), text: moduleName, html: (row) => moduleCell(row) },
          { label: __("Error"), sort: (r) => r.error || "", text: (r) => r.error, html: (r) => `<span class="rs-error" title="${esc(r.error)}">${esc(r.error)}</span>` },
          { label: __("Action"), nosort: true, html: (r) => `<button class="btn btn-xs btn-default" data-retry-registration="${esc(r.name)}">${esc(__("Retry Provisioning"))}</button>` },
        ],
        failed,
        __("No failed registrations.")
      )}
      ${defineTable(
        "registrations",
        __("Recent registrations"),
        [
          { label: __("Registration"), sort: (r) => r.name, text: (r) => r.name, html: (r) => link("SaaS Registration", r.name) },
          { label: __("Business"), sort: (r) => r.business_name || "", text: (r) => r.business_name, html: (r) => esc(r.business_name) },
          {
            label: __("Owner"), sort: (r) => r.owner_email || "", text: (r) => `${r.owner_email} ${r.owner_phone}`,
            html: (r) => `${esc(r.owner_email)}${r.email_verified ? " ✓" : ""}${r.owner_phone ? `<br><small class="text-muted">${esc(r.owner_phone)}${r.phone_verified ? " ✓" : ""}</small>` : ""}`,
          },
          { label: __("Module"), sort: (r) => moduleName(r), text: moduleName, html: (row) => moduleCell(row) },
          { label: __("Plan"), sort: (r) => r.plan || "", text: (r) => r.plan, html: (r) => link("SaaS Plan", r.plan) },
          { label: __("Status"), sort: (r) => r.status || "", text: (r) => r.status, html: (r) => pill(r.status) },
        ],
        data.registrations || [],
        __("No registrations yet.")
      )}
      ${defineTable(
        "jobs",
        __("Provisioning jobs"),
        [
          { label: __("Job"), sort: (j) => j.name, text: (j) => j.name, html: (j) => link("Tenant Provisioning Job", j.name) },
          { label: __("Company"), sort: (j) => j.company || "", text: (j) => j.company, html: (j) => esc(j.company) },
          { label: __("Status"), sort: (j) => j.status || "", text: (j) => j.status, html: (j) => pill(j.status) },
          { label: __("Step / Error"), sort: (j) => j.error || j.current_step || "", text: (j) => j.error || j.current_step, html: (j) => `<span class="rs-error">${esc(j.error || j.current_step)}</span>` },
          {
            label: __("Action"), nosort: true,
            html: (j) => (j.status !== "Complete" ? `<button class="btn btn-xs btn-default" data-retry-seed="${esc(j.company)}">${esc(__("Run / Retry"))}</button>` : ""),
          },
        ],
        data.seed_jobs || [],
        __("No provisioning jobs yet.")
      )}
      ${defineTable(
        "subscriptions",
        __("Subscriptions"),
        [
          { label: __("Subscription"), sort: (s2) => s2.name, text: (s2) => s2.name, html: (s2) => link("SaaS Subscription", s2.name) },
          { label: __("Company"), sort: (s2) => s2.company || "", text: (s2) => s2.company, html: (s2) => esc(s2.company) },
          { label: __("Module"), sort: (s2) => moduleName(s2), text: moduleName, html: (row) => moduleCell(row) },
          { label: __("Plan"), sort: (s2) => s2.plan || "", text: (s2) => s2.plan, html: (s2) => link("SaaS Plan", s2.plan) },
          { label: __("Status"), sort: (s2) => s2.status || "", text: (s2) => s2.status, html: (s2) => pill(s2.status) },
          { label: __("Billing"), sort: (s2) => billingText(s2.billing), text: (s2) => billingText(s2.billing), html: (s2) => billing(s2.billing) },
        ],
        data.subscriptions || [],
        __("No subscriptions yet.")
      )}
      </div>
    `);
    Object.keys(tables).forEach(paint);
  }

  function act(method, args, done) {
    frappe.call({ method, args, freeze: true }).then(() => {
      frappe.show_alert({ message: done, indicator: "green" });
      load();
    });
  }

  $body.on("click", "[data-verify]", function () {
    const payment = $(this).attr("data-verify");
    const reference = $body.find(`[data-reference="${CSS.escape(payment)}"]`).val();
    act("reckon_saas_platform.saas.verify_payment_manual", { payment, reference }, __("Payment verified"));
  });
  $body.on("click", "[data-retry-registration]", function () {
    act(
      "reckon_saas_platform.saas.retry_registration_provisioning",
      { registration: $(this).attr("data-retry-registration") },
      __("Provisioning queued")
    );
  });
  $body.on("click", "[data-retry-seed]", function () {
    act(
      "reckon_saas_platform.saas.retry_tenant_seed_job",
      { company: $(this).attr("data-retry-seed") },
      __("Seed job run finished")
    );
  });

  function load() {
    frappe.call("reckon_saas_platform.saas.get_vendor_dashboard").then((r) => render(r.message || {}));
  }

  $("<style>")
    .text(`
      .rs-saas-dashboard .rs-container { max-width: 1280px; margin: 0 auto; padding: 8px 16px 40px; }
      .rs-saas-dashboard .rs-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; margin: 4px 0 22px; }
      .rs-saas-dashboard .rs-card { display: block; padding: 14px 16px; border: 1px solid var(--border-color); border-radius: var(--border-radius-lg); background: var(--card-bg); color: var(--text-color); text-decoration: none; }
      .rs-saas-dashboard .rs-card:hover { border-color: var(--primary); }
      .rs-saas-dashboard .rs-card-label { font-size: var(--text-sm); color: var(--text-muted); }
      .rs-saas-dashboard .rs-card-value { font-size: 26px; font-weight: 700; margin-top: 4px; }
      .rs-saas-dashboard .rs-panel { margin-bottom: 22px; border: 1px solid var(--border-color); border-radius: var(--border-radius-lg); background: var(--card-bg); overflow: hidden; }
      .rs-saas-dashboard .rs-panel-head { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--border-color); }
      .rs-saas-dashboard .rs-panel-head h4 { margin: 0; font-size: 15px; font-weight: 600; }
      .rs-saas-dashboard .rs-count { margin-left: 6px; padding: 1px 8px; border-radius: 999px; background: var(--control-bg, var(--bg-color)); color: var(--text-muted); font-size: 12px; font-weight: 500; }
      .rs-saas-dashboard .rs-tools { display: flex; gap: 8px; }
      .rs-saas-dashboard .rs-search { width: 220px; }
      .rs-saas-dashboard .rs-size { width: auto; }
      .rs-saas-dashboard .rs-table-wrap { overflow-x: auto; }
      .rs-saas-dashboard .rs-table { margin: 0; width: 100%; }
      .rs-saas-dashboard .rs-table th, .rs-saas-dashboard .rs-table td { padding: 9px 16px; vertical-align: middle; border-left: 0; border-right: 0; }
      .rs-saas-dashboard .rs-table th { background: var(--control-bg, var(--bg-color)); font-weight: 600; white-space: nowrap; }
      .rs-saas-dashboard .rs-sort { background: none; border: 0; padding: 0; font: inherit; color: inherit; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
      .rs-saas-dashboard .rs-sort:hover { color: var(--primary); }
      .rs-saas-dashboard .rs-sort:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
      .rs-saas-dashboard .rs-arrow { font-size: 10px; min-width: 10px; color: var(--primary); }
      .rs-saas-dashboard .rs-pager { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; padding: 10px 16px; border-top: 1px solid var(--border-color); font-size: var(--text-sm); color: var(--text-muted); }
      .rs-saas-dashboard .rs-pages { display: inline-flex; gap: 4px; align-items: center; }
      .rs-saas-dashboard .rs-page { min-width: 28px; }
      .rs-saas-dashboard .rs-gap { padding: 0 2px; }
      .rs-saas-dashboard .rs-error { display: inline-block; max-width: 360px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; }
      @media (max-width: 640px) { .rs-saas-dashboard .rs-search { width: 100%; } .rs-saas-dashboard .rs-tools { width: 100%; } }
    `)
    .appendTo($body.parent());

  load();
};
