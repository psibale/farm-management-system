(function () {
  "use strict";
  const form = document.getElementById("irrigationInspectionForm");
  if (!form) return;
  const fieldSelect = document.getElementById("field");
  const otherWrap = document.getElementById("otherFieldWrap");
  const otherField = document.getElementById("otherField");
  const cropInput = document.getElementById("crop_variety");
  const message = document.getElementById("saveMessage");
  const saveButton = document.getElementById("saveButton");
  const today = new Date();
  const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  document.getElementById("inspection_date").value = localDate;

  function selectedField() {
    return fieldSelect.value === "__other__" ? otherField.value.trim() : fieldSelect.value.trim();
  }
  function updateFieldMetadata() {
    const option = fieldSelect.selectedOptions[0];
    const custom = fieldSelect.value === "__other__";
    otherWrap.hidden = !custom;
    otherField.required = custom;
    cropInput.value = custom || !option ? "" : (option.dataset.crop || "");
  }
  fieldSelect.addEventListener("change", updateFieldMetadata);
  updateFieldMetadata();

  function showMessage(text, kind) {
    message.textContent = text;
    message.className = "msg show " + kind;
    message.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (typeof saveSurveyOffline !== "function") {
      showMessage("Offline storage did not load. Keep this page open and try again.", "error");
      return;
    }
    saveButton.disabled = true;
    saveButton.textContent = "Saving on this phone…";
    const option = fieldSelect.selectedOptions[0];
    const record = {
      record_type: "irrigation_inspection",
      survey_id: generateSurveyID(),
      inspection_date: document.getElementById("inspection_date").value,
      field: selectedField(),
      main_field: option && option.dataset ? option.dataset.main || "" : "",
      area_ha: option && option.dataset ? option.dataset.area || "" : "",
      crop_variety: cropInput.value.trim(),
      irrigation_method: document.getElementById("irrigation_method").value,
      water_source: document.getElementById("water_source").value,
      soil_moisture: document.getElementById("soil_moisture").value,
      system_condition: document.getElementById("system_condition").value,
      water_distribution: document.getElementById("water_distribution").value,
      observed_issues: document.getElementById("observed_issues").value.trim(),
      observations: document.getElementById("observations").value.trim(),
      recommended_action: document.getElementById("recommended_action").value.trim(),
      priority: document.getElementById("priority").value,
      season: form.elements.season.value,
      surveyor: ""
    };
    try {
      await saveSurveyOffline(record);
      showMessage("Inspection saved on this phone. It will upload when the DCGL server is reachable.", "success");
      form.reset();
      document.getElementById("inspection_date").value = localDate;
      updateFieldMetadata();
      if (navigator.onLine) window.dispatchEvent(new Event("dcglManualSync"));
    } catch (error) {
      showMessage("Could not save this inspection on the phone: " + (error.message || "storage error"), "error");
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "Save inspection";
    }
  });
})();
