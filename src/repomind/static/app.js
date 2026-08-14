// Progressive enhancement only: the copy buttons ship hidden so a browser without
// JavaScript never shows a control that cannot work. Everything the console proves
// -- the answer, the path:line evidence, the request id -- is already in the HTML.
(function () {
  "use strict";

  var RESET_DELAY_MS = 1400;

  function copyWithSelection(text) {
    var carrier = document.createElement("textarea");
    carrier.value = text;
    carrier.setAttribute("readonly", "");
    carrier.style.position = "fixed";
    carrier.style.opacity = "0";
    document.body.appendChild(carrier);
    carrier.select();
    try {
      return document.execCommand("copy");
    } catch (error) {
      return false;
    } finally {
      document.body.removeChild(carrier);
    }
  }

  function copy(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(
        function () {
          return true;
        },
        function () {
          return copyWithSelection(text);
        }
      );
    }
    return Promise.resolve(copyWithSelection(text));
  }

  function enhance(button) {
    var idle = button.textContent;
    var timer = null;

    button.hidden = false;
    button.addEventListener("click", function () {
      copy(button.dataset.copy).then(function (ok) {
        button.textContent = ok ? "copied" : "copy failed";
        button.classList.toggle("copied", ok);
        window.clearTimeout(timer);
        timer = window.setTimeout(function () {
          button.textContent = idle;
          button.classList.remove("copied");
        }, RESET_DELAY_MS);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var buttons = document.querySelectorAll(".copy-location");
    for (var index = 0; index < buttons.length; index += 1) {
      enhance(buttons[index]);
    }
  });
})();
