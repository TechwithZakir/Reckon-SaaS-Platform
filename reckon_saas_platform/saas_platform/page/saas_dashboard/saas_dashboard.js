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
  const moduleCell = (row) =>
    row.saas_module ? link("SaaS Module", row.saas_module, row.module_name || row.saas_module) : "";

  function billing(b) {
    if (!b) return "";
    if (b.state === "trial") return esc(__("Trial until {0}", [b.trial_end_date]));
    if (b.state === "active") return b.paid_until ? esc(__("Paid until {0}", [b.paid_until])) : esc(__("Active"));
    if (b.state === "grace") return `${pill(__("Dues"))} ${esc(__("grace until {0}", [b.grace_end]))}`;
    return b.dues ? `${pill(__("Dues"))} ${esc(__("locked"))}` : esc(__("Locked"));
  }

  function card(label, value, doctype, filters) {
    const href = doctype ? `${route(doctype)}${filters ? "?" + filters : ""}` : "#";
    return `<a class="rs-card" href="${href}"><div class="rs-card-label">${esc(label)}</div>
      <div class="rs-card-value">${esc(value || 0)}</div></a>`;
  }

  function table(title, headers, rows, empty) {
    const head = headers.map((h) => `<th>${esc(h)}</th>`).join("");
    const body = rows.length
      ? rows.join("")
      : `<tr><td colspan="${headers.length}" class="text-muted">${esc(empty)}</td></tr>`;
    return `<section class="rs-panel"><h4>${esc(title)}</h4>
      <div class="rs-table-wrap"><table class="table table-bordered"><thead><tr>${head}</tr></thead>
      <tbody>${body}</tbody></table></div></section>`;
  }

  function render(data) {
    const s = data.summary || {};
    const failed = (data.registrations || []).filter((r) => r.status === "Failed");
    $body.html(`
      <div class="rs-cards">
        ${card(__("Modules for sale"), s.modules, "SaaS Module", "enabled=1")}
        ${card(__("Plans"), s.plans, "SaaS Plan")}
        ${card(__("Registrations"), s.registrations, "SaaS Registration")}
        ${card(__("Failed registrations"), s.registrations_failed, "SaaS Registration", "status=Failed")}
        ${card(__("Active subscriptions"), s.subscriptions_active, "SaaS Subscription")}
        ${card(__("Payments to verify"), s.payments_pending, "SaaS Payment", "status=Pending%20Verification")}
        ${card(__("Seed jobs open"), s.seed_jobs_pending, "Tenant Provisioning Job")}
      </div>
      ${table(
        __("Modules"),
        [__("Module"), __("Plans"), __("Registrations"), __("Active subscriptions")],
        (data.module_stats || []).map(
          (m) => `<tr><td>${link("SaaS Module", m.module, m.module_name)}</td>
            <td><a href="${route("SaaS Plan")}?saas_module=${encodeURIComponent(m.module)}">${esc(m.plans)}</a></td>
            <td><a href="${route("SaaS Registration")}?saas_module=${encodeURIComponent(m.module)}">${esc(m.registrations)}</a></td>
            <td><a href="${route("SaaS Subscription")}?saas_module=${encodeURIComponent(m.module)}">${esc(m.active_subscriptions)}</a></td></tr>`
        ),
        __("No modules registered yet. Run bench migrate after installing a product app.")
      )}
      ${table(
        __("Plans"),
        [__("Plan"), __("Module"), __("Price"), __("Trial days"), __("Grace days"), __("Enabled")],
        (data.plans || []).map(
          (p) => `<tr><td>${link("SaaS Plan", p.name, p.plan_name)}</td><td>${moduleCell(p)}</td>
            <td>${esc(p.currency)} ${esc(p.price)} / ${esc(__(p.billing_cycle || "Monthly"))}</td>
            <td>${esc(p.trial_days || 0)}</td><td>${esc(p.grace_days || 0)}</td>
            <td>${p.enabled ? esc(__("Yes")) : esc(__("No"))}</td></tr>`
        ),
        __("No plans yet.")
      )}
      ${table(
        __("Payments to verify"),
        [__("Payment"), __("Company"), __("Module"), __("Amount"), __("Reference"), __("Action")],
        (data.pending_payments || []).map(
          (p) => `<tr><td>${link("SaaS Payment", p.name)}</td><td>${esc(p.company)}</td>
            <td>${moduleCell(p)}</td><td>${esc(p.currency)} ${esc(p.amount)}</td>
            <td><input class="form-control input-xs" data-reference="${esc(p.name)}" value="${esc(p.gateway_reference)}" placeholder="${esc(__("Reference"))}"></td>
            <td><button class="btn btn-xs btn-primary" data-verify="${esc(p.name)}">${esc(__("Verify"))}</button></td></tr>`
        ),
        __("No payments waiting.")
      )}
      ${table(
        __("Failed registrations"),
        [__("Registration"), __("Business"), __("Module"), __("Error"), __("Action")],
        failed.map(
          (r) => `<tr><td>${link("SaaS Registration", r.name)}</td><td>${esc(r.business_name)}</td>
            <td>${moduleCell(r)}</td><td class="rs-error" title="${esc(r.error)}">${esc(r.error)}</td>
            <td><button class="btn btn-xs btn-default" data-retry-registration="${esc(r.name)}">${esc(__("Retry Provisioning"))}</button></td></tr>`
        ),
        __("No failed registrations.")
      )}
      ${table(
        __("Recent registrations"),
        [__("Registration"), __("Business"), __("Owner"), __("Module"), __("Plan"), __("Status")],
        (data.registrations || []).map(
          (r) => `<tr><td>${link("SaaS Registration", r.name)}</td><td>${esc(r.business_name)}</td>
            <td>${esc(r.owner_email)}${r.email_verified ? " ✓" : ""}${r.owner_phone ? `<br><small class="text-muted">${esc(r.owner_phone)}${r.phone_verified ? " ✓" : ""}</small>` : ""}</td>
            <td>${moduleCell(r)}</td><td>${link("SaaS Plan", r.plan)}</td><td>${pill(r.status)}</td></tr>`
        ),
        __("No registrations yet.")
      )}
      ${table(
        __("Provisioning jobs"),
        [__("Job"), __("Company"), __("Status"), __("Step / Error"), __("Action")],
        (data.seed_jobs || []).map(
          (j) => `<tr><td>${link("Tenant Provisioning Job", j.name)}</td><td>${esc(j.company)}</td>
            <td>${pill(j.status)}</td><td class="rs-error">${esc(j.error || j.current_step)}</td>
            <td>${j.status !== "Complete" ? `<button class="btn btn-xs btn-default" data-retry-seed="${esc(j.company)}">${esc(__("Run / Retry"))}</button>` : ""}</td></tr>`
        ),
        __("No provisioning jobs yet.")
      )}
      ${table(
        __("Subscriptions"),
        [__("Subscription"), __("Company"), __("Module"), __("Plan"), __("Status"), __("Billing")],
        (data.subscriptions || []).map(
          (s) => `<tr><td>${link("SaaS Subscription", s.name)}</td><td>${esc(s.company)}</td>
            <td>${moduleCell(s)}</td><td>${link("SaaS Plan", s.plan)}</td><td>${pill(s.status)}</td>
            <td>${billing(s.billing)}</td></tr>`
        ),
        __("No subscriptions yet.")
      )}
    `);
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
      .rs-saas-dashboard .rs-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; margin: 8px 0 20px; }
      .rs-saas-dashboard .rs-card { display: block; padding: 14px 16px; border: 1px solid var(--border-color); border-radius: var(--border-radius-lg); background: var(--card-bg); color: var(--text-color); text-decoration: none; }
      .rs-saas-dashboard .rs-card:hover { border-color: var(--primary); }
      .rs-saas-dashboard .rs-card-label { font-size: var(--text-sm); color: var(--text-muted); }
      .rs-saas-dashboard .rs-card-value { font-size: 26px; font-weight: 700; margin-top: 4px; }
      .rs-saas-dashboard .rs-panel { margin-bottom: 22px; }
      .rs-saas-dashboard .rs-table-wrap { overflow-x: auto; }
      .rs-saas-dashboard .rs-error { max-width: 360px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    `)
    .appendTo($body.parent());

  load();
};
