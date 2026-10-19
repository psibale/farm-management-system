(function () {
  "use strict";
  const form = document.getElementById("geoPhotoForm");
  if (!form) return;
  const photoInput = document.getElementById("photo");
  const preview = document.getElementById("preview");
  const fieldSelect = document.getElementById("field");
  const otherWrap = document.getElementById("otherFieldWrap");
  const otherField = document.getElementById("otherField");
  const gpsStatus = document.getElementById("gpsStatus");
  const gpsButton = document.getElementById("gpsButton");
  const saveButton = document.getElementById("saveButton");
  const message = document.getElementById("saveMessage");
  let gps = null;
  let compressedPhoto = "";
  const now = new Date();
  const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  document.getElementById("photo_date").value = localDate;

  function showMessage(text, type) {
    message.textContent = text;
    message.className = "msg show " + type;
    message.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  function setField() {
    const custom = fieldSelect.value === "__other__";
    otherWrap.hidden = !custom;
    otherField.required = custom;
  }
  fieldSelect.addEventListener("change", setField);
  setField();

  function compress(file) {
    return new Promise((resolve, reject) => {
      if (!file || !file.type.startsWith("image/")) return reject(new Error("Choose an image file."));
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("The selected photo could not be read."));
      reader.onload = () => {
        const image = new Image();
        image.onerror = () => reject(new Error("This photo format is not supported by this browser. Choose a JPEG or PNG."));
        image.onload = () => {
          const scale = Math.min(1, 1280 / Math.max(image.width, image.height));
          const canvas = document.createElement("canvas");
          canvas.width = Math.max(1, Math.round(image.width * scale));
          canvas.height = Math.max(1, Math.round(image.height * scale));
          const context = canvas.getContext("2d");
          if (!context) return reject(new Error("Photo processing is unavailable on this device."));
          context.drawImage(image, 0, 0, canvas.width, canvas.height);
          let quality = 0.78;
          let data = canvas.toDataURL("image/jpeg", quality);
          while (data.length * 0.75 > 880000 && quality > 0.38) {
            quality -= 0.08;
            data = canvas.toDataURL("image/jpeg", quality);
          }
          if (data.length * 0.75 > 880000) return reject(new Error("Photo is still too large after resizing. Choose another photo."));
          resolve(data);
        };
        image.src = reader.result;
      };
      reader.readAsDataURL(file);
    });
  }

  photoInput.addEventListener("change", async () => {
    compressedPhoto = "";
    preview.hidden = true;
    if (!photoInput.files || !photoInput.files[0]) return;
    try {
      compressedPhoto = await compress(photoInput.files[0]);
      preview.src = compressedPhoto;
      preview.hidden = false;
    } catch (error) {
      photoInput.value = "";
      showMessage(error.message || "Could not prepare the photo.", "error");
    }
  });

  gpsButton.addEventListener("click", () => {
    if (!navigator.geolocation) {
      showMessage("GPS location is not available in this browser.", "error");
      return;
    }
    gpsButton.disabled = true;
    gpsStatus.textContent = "Getting GPS location… move to an open area and allow location access.";
    navigator.geolocation.getCurrentPosition(position => {
      gps = {
        latitude: Number(position.coords.latitude.toFixed(7)),
        longitude: Number(position.coords.longitude.toFixed(7)),
        accuracy: Number(position.coords.accuracy.toFixed(1))
      };
      gpsStatus.textContent = `Location captured: ${gps.latitude}, ${gps.longitude} (accuracy about ${gps.accuracy} m).`;
      gpsButton.disabled = false;
    }, error => {
      gps = null;
      const reason = error.code === 1 ? "Allow location access in your phone settings, then try again." : "Could not get a GPS fix. Move to an open area and try again.";
      gpsStatus.textContent = reason;
      showMessage(reason, "error");
      gpsButton.disabled = false;
    }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 });
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (!compressedPhoto) return showMessage("Select a photo and wait for its preview before saving.", "error");
    if (!gps) return showMessage("Capture GPS location before saving this geo-tagged photo.", "error");
    if (typeof saveSurveyOffline !== "function") return showMessage("Offline storage did not load. Keep this page open and try again.", "error");
    saveButton.disabled = true;
    saveButton.textContent = "Saving on this phone…";
    const option = fieldSelect.selectedOptions[0];
    const record = {
      record_type: "geo_photo",
      survey_id: generateSurveyID(),
      photo_date: document.getElementById("photo_date").value,
      field: fieldSelect.value === "__other__" ? otherField.value.trim() : fieldSelect.value.trim(),
      main_field: option && option.dataset ? option.dataset.main || "" : "",
      latitude: gps.latitude,
      longitude: gps.longitude,
      gps_accuracy: gps.accuracy,
      category: document.getElementById("category").value,
      notes: document.getElementById("notes").value.trim(),
      photo_data: compressedPhoto,
      season: form.elements.season.value
    };
    try {
      await saveSurveyOffline(record);
      showMessage("Photo and GPS location saved on this phone. It will sync when the DCGL server is reachable.", "success");
      form.reset();
      document.getElementById("photo_date").value = localDate;
      preview.src = "";
      preview.hidden = true;
      compressedPhoto = "";
      gps = null;
      gpsStatus.textContent = "GPS location has not been captured.";
      setField();
      if (navigator.onLine) window.dispatchEvent(new Event("dcglManualSync"));
    } catch (error) {
      showMessage("Could not save the photo on this phone: " + (error.message || "storage error"), "error");
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "Save photo";
    }
  });
})();
