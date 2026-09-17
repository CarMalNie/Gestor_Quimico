(function () {
  "use strict";

  function initCascade() {
    var industrySelect = document.querySelector('[name="tipo_industria"]');
    var appSelect = document.querySelector('[name="id_aplicacion"]');

    if (!industrySelect || !appSelect) {
      return;
    }

    var appToIndustry = null;
    var dataEl = document.getElementById("compuesto-cascade-data");
    if (dataEl) {
      try {
        var parsed = JSON.parse(dataEl.textContent);
        if (parsed && typeof parsed === "object" && Object.keys(parsed).length > 0) {
          appToIndustry = parsed;
        }
      } catch (e) {
        appToIndustry = null;
      }
    }

    function filterApplications() {
      // Fail-open: without a populated industry map we cannot filter safely,
      // so every option stays visible and the server-side clean() validation
      // remains the guard against cross-industry mismatches.
      if (!appToIndustry) {
        return;
      }

      var selectedIndustry = industrySelect.value;

      for (var i = 0; i < appSelect.options.length; i++) {
        var option = appSelect.options[i];
        if (!option.value) {
          continue; // empty placeholder stays visible
        }
        var industryId = String(appToIndustry[option.value] || "");
        var mismatch = selectedIndustry && industryId !== selectedIndustry;
        // Never hide the currently selected option so validation-error re-renders survive.
        option.hidden = mismatch && !option.selected;
      }
    }

    industrySelect.addEventListener("change", function () {
      appSelect.value = "";
      filterApplications();
    });

    filterApplications();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCascade);
  } else {
    initCascade();
  }
})();
