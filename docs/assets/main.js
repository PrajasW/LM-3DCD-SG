/* Small helpers for the LM-3DCD-SG project page: theme toggle, nav scroll-spy, copy-to-clipboard. */
(function () {
  "use strict";

  /* ---------- theme toggle (light / dark / follow the OS) ---------- */
  var root = document.documentElement;
  var STORAGE_KEY = "lm3dcdsg-theme";

  function applyTheme(theme) {
    if (theme === "light" || theme === "dark") {
      root.setAttribute("data-theme", theme);
    } else {
      root.removeAttribute("data-theme");
    }
    var btn = document.querySelector("[data-theme-toggle]");
    if (btn) {
      var dark = theme === "dark" ||
        (theme !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
      btn.textContent = dark ? "Light" : "Dark";
      btn.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
    }
  }

  try {
    applyTheme(localStorage.getItem(STORAGE_KEY) || "auto");
  } catch (e) {
    applyTheme("auto");
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-theme-toggle]");
    if (!btn) return;
    // Resolve "auto" to the theme the OS is currently showing, so the button label
    // always names the theme the next click will switch to.
    var current = root.getAttribute("data-theme");
    var effective;
    if (current === "light" || current === "dark") {
      effective = current;
    } else {
      effective = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    var next = effective === "dark" ? "light" : "dark";
    try { localStorage.setItem(STORAGE_KEY, next); } catch (e) { /* private mode */ }
    applyTheme(next);
  });

  /* Keep the button label in sync when the OS theme changes and the page is on "auto". */
  if (window.matchMedia) {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    var onChange = function () {
      var current = root.getAttribute("data-theme");
      if (!current) applyTheme("auto");
    };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }

  /* ---------- nav scroll-spy ---------- */
  var links = Array.prototype.slice.call(document.querySelectorAll(".topbar nav a[href^='#']"));
  var targets = links
    .map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); })
    .filter(Boolean);

  function spy() {
    var best = null, bestTop = -Infinity;
    var probe = window.scrollY + 140;
    targets.forEach(function (el) {
      var top = el.getBoundingClientRect().top + window.scrollY;
      if (top <= probe && top > bestTop) { bestTop = top; best = el; }
    });
    links.forEach(function (a) {
      a.classList.toggle("active", best !== null && a.getAttribute("href") === "#" + best.id);
    });
  }

  var ticking = false;
  window.addEventListener("scroll", function () {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () { spy(); ticking = false; });
  }, { passive: true });
  window.addEventListener("resize", spy);
  spy();

  /* ---------- copy to clipboard ---------- */
  var toast = document.createElement("div");
  toast.className = "toast";
  document.body.appendChild(toast);
  var toastTimer = null;

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove("show"); }, 1800);
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-copy]");
    if (!btn) return;
    var src = document.getElementById(btn.getAttribute("data-copy"));
    if (!src) return;
    var text = (src.innerText || src.textContent || "").trim();
    var done = function () { showToast("Copied to clipboard"); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
    } else {
      fallback(text, done);
    }
  });

  function fallback(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); done(); } catch (e) { showToast("Copy failed"); }
    document.body.removeChild(ta);
  }
})();
