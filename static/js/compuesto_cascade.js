(function () {
  "use strict";

  function initCascade() {
    var industrySelect = document.querySelector('[name="tipo_industria"]');
    var appSelect = document.querySelector('[name="id_aplicacion"]');

    if (!industrySelect || !appSelect) {
      return;
    }

    var appToIndustry = {};
    var dataEl = document.getElementById("compuesto-cascade-data");
    if (dataEl) {
      try {
        appToIndustry = JSON.parse(dataEl.textContent);
      } catch (e) {
        appToIndustry = {};
      }
    }

    function filterApplications() {
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
