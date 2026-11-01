// Runs in <head> before the page paints: apply a theme the visitor picked earlier, if any.
// With nothing stored, data-style stays unset and the media queries in tokens.css decide.
// A plain script file, not inline, because the Content Security Policy blocks inline scripts.
(function () {
  try {
    var s = localStorage.getItem("scope-style");
    if (s === "scope" || s === "paper" || s === "hc") {
      document.documentElement.setAttribute("data-style", s);
    }
  } catch (e) {
    // Storage blocked (private window, strict settings): follow the browser instead.
  }
})();
