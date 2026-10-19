(function () {
  "use strict";
  const form = document.getElementById("pestDiseaseForm");
  if (!form) return;
  const kind = document.getElementById("inspection_type");
  const disease = document.getElementById("diseaseFields");
  const pests = document.getElementById("pestFields");
  const treatment = document.getElementById("treatmentFields");
  const pesticide = document.getElementById("pesticide_used");
  const hectares = document.getElementById("hectares");
  const fieldSelect = document.getElementById("field");
  const otherWrap = document.getElementById("otherFieldWrap");
  const otherField = document.getElementById("otherField");
  const cropInput = document.getElementById("crop_variety");
  const message = document.getElementById("saveMessage");
  const saveButton = document.getElementById("saveButton");
  const today = new Date();
  const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  document.getElementById("inspection_date").value = localDate;

  function setMode() {
    const isTreatment = kind.value === "Pest Control";
    const isDisease = kind.value === "Disease Inspection";
    treatment.hidden = !isTreatment;
    disease.hidden = !isDisease;
    pests.hidden = isDisease || isTreatment;
    pesticide.required = isTreatment;
    hectares.required = isTreatment;
    const findingType = document.getElementById("pest_disease_type");
    if (kind.value === "Disease Inspection" && !findingType.value) findingType.value = "Disease";
    if ((kind.value === "Pest Inspection" || isTreatment) && !findingType.value) findingType.value = "Pest";
  }
  function setField() {
    const option = fieldSelect.selectedOptions[0];
    const custom = fieldSelect.value === "__other__";
    otherWrap.hidden = !custom;
    otherField.required = custom;
    cropInput.value = custom || !option ? "" : (option.dataset.crop || "");
  }
  kind.addEventListener("change", setMode);
  fieldSelect.addEventListener("change", setField);
  setMode(); setField();

  function showMessage(text, type) {
    message.textContent = text;
    message.className = "msg show " + type;
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
      record_type: "pest_disease_inspection",
      survey_id: generateSurveyID(),
      inspection_date: document.getElementById("inspection_date").value,
      field: fieldSelect.value === "__other__" ? otherField.value.trim() : fieldSelect.value.trim(),
      main_field: option && option.dataset ? option.dataset.main || "" : "",
      area_ha: option && option.dataset ? option.dataset.area || "" : "",
      crop_variety: cropInput.value.trim(),
      inspection_type: kind.value,
      pest_disease_type: document.getElementById("pest_disease_type").value,
      issue_name: document.getElementById("issue_name").value.trim(),
      smut_percent: document.getElementById("smut_percent").value,
      ysa_percent: document.getElementById("ysa_percent").value,
      black_beetles_per_ha: document.getElementById("black_beetles_per_ha").value,
      lady_beetle_count: document.getElementById("lady_beetle_count").value,
      hectares: document.getElementById("hectares").value,
      pesticide_used: document.getElementById("pesticide_used").value.trim(),
      liters: document.getElementById("liters").value,
      mandays: document.getElementById("mandays").value,
      observations: document.getElementById("observations").value.trim(),
      recommended_action: document.getElementById("recommended_action").value.trim(),
      priority: document.getElementById("priority").value,
      season: form.elements.season.value,
      surveyor: ""
    };
    try {
      await saveSurveyOffline(record);
      showMessage("Record saved on this phone. It will upload when the DCGL server is reachable.", "success");
      form.reset();
      document.getElementById("inspection_date").value = localDate;
      setMode(); setField();
      if (navigator.onLine) window.dispatchEvent(new Event("dcglManualSync"));
    } catch (error) {
      showMessage("Could not save this record on the phone: " + (error.message || "storage error"), "error");
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "Save record";
    }
  });
})();
