/* /login: same name, logo and "powered by" line as the landing page. */
(function () {
  var BRAND = "ReckonERP";
  var LOGO = "/assets/reckon_saas_platform/images/reckonerp-logo.webp";
  var POWERED = "Powered by ReckonERP";
  var OWNER = "Reckon Technologies Ltd.";

  function isLogin() {
    var body = document.body;
    return !!body && (body.getAttribute("data-path") === "login" || location.pathname.replace(/\/+$/, "") === "/login");
  }

  function apply() {
    if (!isLogin()) return;
    document.querySelectorAll(".page-card-head img, img.app-logo, .login-content img.app-logo").forEach(function (img) {
      img.src = LOGO;
      img.alt = BRAND;
    });
    document.querySelectorAll(".page-card-head h4, .page-card-head h1, .login-content h4").forEach(function (el) {
      el.textContent = el.textContent.replace(/^(.*?\s)(?:to|\u09a4\u09c7)\s+.+$/i, "$1to " + BRAND);
    });
    if (document.title) document.title = document.title.replace(/\s*[|\u2013-]\s*(Frappe|ERPNext)[^|]*$/i, "");
    document.querySelectorAll("[class*=powered], .web-footer, footer").forEach(function (el) {
      if (/frappe|erpnext/i.test(el.textContent || "")) el.textContent = POWERED;
    });
    if (!document.querySelector(".reckon-powered")) {
      var line = document.createElement("p");
      line.className = "reckon-powered";
      line.innerHTML = "&copy; " + new Date().getFullYear() + " " + OWNER + " &middot; <strong></strong>";
      line.querySelector("strong").textContent = POWERED;
      document.body.appendChild(line);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply);
  else apply();
  // The login card can render after load (hash changes between login, signup and forgot password).
  window.addEventListener("hashchange", apply);
  window.addEventListener("load", apply);
})();
