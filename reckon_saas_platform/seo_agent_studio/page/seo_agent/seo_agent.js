// SEO Agent: one text box, plain replies, and cards you approve in the thread.
frappe.pages["seo-agent"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("SEO Agent"), single_column: true });
	const METHOD = "reckon_saas_platform.seo_agent_chat.";
	const esc = (value) => frappe.utils.escape_html(value == null ? "" : String(value));
	const rich = (text) =>
		esc(text)
			.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
			.replace(/\n/g, "<br>");
	const call = (method, args) => frappe.call({ method: METHOD + method, args: args || {}, freeze: false }).then((r) => r.message);

	if (!document.getElementById("sa-style")) {
		const style = document.createElement("style");
		style.id = "sa-style";
		style.textContent = `
		.sa-wrap{max-width:820px;margin:0 auto;display:flex;flex-direction:column;min-height:calc(100vh - 190px)}
		.sa-status{display:flex;flex-wrap:wrap;gap:8px 18px;justify-content:space-between;color:var(--text-muted);font-size:12px;padding:4px 2px 12px}
		.sa-banner{background:var(--bg-orange,#fff4e0);color:var(--text-color);border-radius:12px;padding:10px 14px;margin-bottom:12px;font-size:13px}
		.sa-banner a{font-weight:600}
		.sa-thread{flex:1;display:flex;flex-direction:column;gap:18px;padding-bottom:12px}
		.sa-msg{display:flex;gap:10px;max-width:100%}
		.sa-msg.user{justify-content:flex-end}
		.sa-avatar{width:30px;height:30px;border-radius:50%;flex:none;background:linear-gradient(135deg,#139bd9,#7c5cf0);color:#fff;display:grid;place-items:center;font-weight:700;font-size:13px}
		.sa-bubble{line-height:1.6;font-size:14px;max-width:calc(100% - 44px);overflow-wrap:anywhere}
		.sa-msg.user .sa-bubble{background:var(--control-bg,#f3f4f6);border-radius:18px;padding:9px 15px;max-width:80%}
		.sa-cards{display:grid;gap:10px;margin-top:10px}
		.sa-card{border:1px solid var(--border-color,#e5e7eb);border-radius:14px;padding:12px 14px;background:var(--card-bg,#fff)}
		.sa-card .sa-top{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin-bottom:6px;font-size:12px;color:var(--text-muted)}
		.sa-pill{background:var(--control-bg,#eef2ff);border-radius:999px;padding:1px 9px;font-weight:600;color:var(--text-color)}
		.sa-card h5{margin:0 0 4px;font-size:14px;line-height:1.4}
		.sa-label{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted);margin-top:8px}
		.sa-text{white-space:pre-wrap;font-size:13px;line-height:1.5}
		.sa-now{color:var(--text-muted);text-decoration:line-through;text-decoration-color:var(--border-color)}
		.sa-cover{width:100%;height:auto;border-radius:10px;margin-bottom:8px;display:block}
		.sa-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;align-items:center}
		.sa-done{font-size:13px;font-weight:600}
		.sa-chips{display:flex;flex-wrap:wrap;gap:8px;padding:4px 0 10px}
		.sa-chip{border:1px solid var(--border-color,#d1d5db);background:var(--card-bg,#fff);border-radius:999px;padding:6px 13px;font-size:13px;cursor:pointer}
		.sa-chip:hover{background:var(--control-bg,#f3f4f6)}
		.sa-form{position:sticky;bottom:0;background:var(--bg-color,#fff);padding:6px 0 4px;display:flex;gap:8px;align-items:flex-end}
		.sa-form textarea{flex:1;resize:none;border:1px solid var(--border-color,#d1d5db);border-radius:18px;padding:11px 16px;font-size:14px;line-height:1.4;max-height:160px;background:var(--control-bg,#fff)}
		.sa-send{width:42px;height:42px;border-radius:50%;border:0;background:#139bd9;color:#fff;font-size:18px;cursor:pointer;flex:none}
		.sa-send[disabled]{opacity:.5;cursor:default}
		.sa-note{text-align:center;color:var(--text-muted);font-size:11px;margin:6px 0 0}
		.sa-dots span{display:inline-block;width:6px;height:6px;margin-right:3px;border-radius:50%;background:var(--text-muted);animation:sa-b 1s infinite}
		.sa-dots span:nth-child(2){animation-delay:.15s}.sa-dots span:nth-child(3){animation-delay:.3s}
		@keyframes sa-b{0%,80%,100%{opacity:.3}40%{opacity:1}}
		@media (prefers-reduced-motion:reduce){.sa-dots span{animation:none}}`;
		document.head.appendChild(style);
	}

	const $body = $(page.body).addClass("sa-root");
	$body.html(`
		<div class="sa-wrap">
			<div class="sa-status"></div>
			<div class="sa-banner" hidden></div>
			<div class="sa-thread" aria-live="polite"></div>
			<div class="sa-chips"></div>
			<form class="sa-form">
				<textarea rows="1" maxlength="600" aria-label="${esc(__("Message the SEO agent"))}" placeholder="${esc(__("Ask the SEO agent anything, e.g. write a blog article about route planning"))}"></textarea>
				<button type="submit" class="sa-send" aria-label="${esc(__("Send"))}">&#8593;</button>
			</form>
			<p class="sa-note">${esc(__("Nothing goes live until you approve or publish it."))}</p>
		</div>`);
	const $thread = $body.find(".sa-thread");
	const $chips = $body.find(".sa-chips");
	const $input = $body.find("textarea");
	const $send = $body.find(".sa-send");
	let busy = false;

	const scroll = () => $thread.children().last()[0]?.scrollIntoView({ block: "end", behavior: "smooth" });

	function addUser(text) {
		$thread.append(`<div class="sa-msg user"><div class="sa-bubble">${esc(text)}</div></div>`);
		scroll();
	}
	function addAgent(html) {
		const $m = $(`<div class="sa-msg"><div class="sa-avatar" aria-hidden="true">R</div><div class="sa-bubble">${html}</div></div>`);
		$thread.append($m);
		scroll();
		return $m;
	}

	function cardHtml(card) {
		if (card.type === "article") {
			return `<div class="sa-card" data-doctype="${esc(card.doctype)}" data-name="${esc(card.name)}">
				${card.cover ? `<img class="sa-cover" src="${esc(card.cover)}" alt="" loading="lazy">` : ""}
				<div class="sa-top"><span class="sa-pill">${esc(card.category)}</span><span>${esc(__("Draft"))}</span></div>
				<h5>${esc(card.title)}</h5><div class="sa-text">${esc(card.summary)}</div>
				<div class="sa-actions">
					<button class="btn btn-primary btn-sm" data-act="publish">${esc(__("Publish"))}</button>
					<button class="btn btn-default btn-sm" data-act="open">${esc(__("Read and edit"))}</button>
					<button class="btn btn-default btn-sm" data-act="reject">${esc(__("Reject"))}</button>
				</div></div>`;
		}
		const idea = card.kind === "Content Idea";
		return `<div class="sa-card" data-doctype="${esc(card.doctype)}" data-name="${esc(card.name)}">
			<div class="sa-top"><span class="sa-pill">${esc(card.kind)}</span><span>${esc(card.page)}</span></div>
			${card.current ? `<div class="sa-label">${esc(__("Now"))}</div><div class="sa-text sa-now">${esc(card.current)}</div>` : ""}
			<div class="sa-label">${esc(idea ? __("Topic with no page yet") : __("Proposed"))}</div><div class="sa-text">${esc(card.proposed)}</div>
			${card.reason ? `<div class="sa-label">${esc(__("Why"))}</div><div class="sa-text">${esc(card.reason)}</div>` : ""}
			<div class="sa-actions">
				<button class="btn btn-primary btn-sm" data-act="approve">${esc(idea ? __("Save idea") : __("Approve"))}</button>
				<button class="btn btn-default btn-sm" data-act="open">${esc(__("Edit"))}</button>
				<button class="btn btn-default btn-sm" data-act="reject">${esc(__("Reject"))}</button>
			</div></div>`;
	}

	function showChips(chips) {
		$chips.empty();
		(chips || []).forEach((text) => {
			$(`<button type="button" class="sa-chip"></button>`).text(text).appendTo($chips);
		});
	}

	function render(res) {
		const cards = (res.cards || []).map(cardHtml).join("");
		addAgent(`${rich(res.reply)}${cards ? `<div class="sa-cards">${cards}</div>` : ""}`);
		showChips(res.chips);
	}

	async function send(text) {
		text = (text || "").trim();
		if (!text || busy) return;
		busy = true;
		$send.prop("disabled", true);
		addUser(text);
		$input.val("").css("height", "auto");
		showChips([]);
		const $wait = addAgent(`<span class="sa-dots" aria-label="${esc(__("Working"))}"><span></span><span></span><span></span></span>`);
		try {
			render(await call("ask", { message: text }));
			loadStatus();
		} catch (e) {
			addAgent(esc(__("I could not reach the server. Please try again.")));
		} finally {
			$wait.remove();
			busy = false;
			$send.prop("disabled", false);
			$input.focus();
		}
	}

	async function loadStatus(greet) {
		try {
			const s = await call("status");
			$body.find(".sa-status").html(
				`<span>${esc(__("{0} suggestion(s) and {1} draft(s) waiting", [s.suggestions, s.drafts]))}</span>
				 <span>${esc(__("AI calls this month: {0} of {1}", [s.calls_used, s.calls_cap]))}</span>`
			);
			const $b = $body.find(".sa-banner");
			if (s.setup) $b.html(`${rich(s.setup)} <a href="#" data-settings>${esc(__("Open settings"))}</a>`).prop("hidden", false);
			else $b.prop("hidden", true);
			if (greet) {
				addAgent(
					rich(
						s.suggestions || s.drafts
							? __("Hi! You have {0} suggestion(s) and {1} blog draft(s) waiting. What would you like to do?", [s.suggestions, s.drafts])
							: __("Hi! I am your SEO agent. What would you like to do?")
					)
				);
				const res = await call("ask", { message: "help" });
				showChips(res.chips);
			}
		} catch (e) {
			addAgent(esc(__("I could not load the status. Please refresh the page.")));
		}
	}

	async function act($card, act) {
		const doctype = $card.data("doctype");
		const name = $card.data("name");
		if (act === "open") return frappe.set_route("Form", doctype, name);
		$card.find("button").prop("disabled", true);
		const r = await call("decide", { doctype, name, action: act });
		$card.find(".sa-actions").html(
			`<span class="sa-done" style="color:${r.ok ? "var(--green-600,#16a34a)" : "var(--red-600,#dc2626)"}">${esc(r.message)}</span>`
		);
		if (!r.ok) {
			$card.find(".sa-actions").append(`<button class="btn btn-default btn-sm" data-act="open">${esc(__("Open to fix"))}</button>`);
		}
		loadStatus();
	}

	$body.on("click", ".sa-chip", function () {
		const text = $(this).text();
		if (text.endsWith(" ")) {
			$input.val(text).focus();
		} else {
			send(text);
		}
	});
	$body.on("click", "[data-act]", function () {
		act($(this).closest(".sa-card"), $(this).data("act"));
	});
	$body.on("click", "[data-settings]", (e) => {
		e.preventDefault();
		frappe.set_route("Form", "SaaS Platform Settings");
	});
	$body.find(".sa-form").on("submit", (e) => {
		e.preventDefault();
		send($input.val());
	});
	$input.on("keydown", (e) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			send($input.val());
		}
	});
	$input.on("input", function () {
		this.style.height = "auto";
		this.style.height = Math.min(this.scrollHeight, 160) + "px";
	});

	page.set_secondary_action(__("New chat"), () => {
		$thread.empty();
		showChips([]);
		loadStatus(true);
	});
	page.add_inner_button(__("Settings"), () => frappe.set_route("Form", "SaaS Platform Settings"));
	page.add_inner_button(__("All suggestions"), () => frappe.set_route("List", "SEO Suggestion"));
	page.add_inner_button(__("All articles"), () => frappe.set_route("List", "SEO Article"));
	loadStatus(true);
};
