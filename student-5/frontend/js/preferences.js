// ============================================================
// Career Profile
// ============================================================

const preferencesForm = document.getElementById("preferences-form");

// ============================================================
// Load preferences
// ============================================================

async function loadPreferences() {
  try {
    const data = await getPreferences();

    if (!data) {
      return;
    }

    document.getElementById("locations").value = data.locations || "";

    document.getElementById("industries").value = data.industries || "";

    document.getElementById("job-types").value = data.job_types || "";

    document.getElementById("skills").value = data.skills || "";

    document.getElementById("career-goals").value = data.career_goals || "";
  } catch (error) {
    showPreferenceMessage("Could not load career profile.", true);
  }
}

// ============================================================
// Save
// ============================================================

async function savePreferences(event) {
  event.preventDefault();

  const data = {
    locations: document.getElementById("locations").value.trim(),

    industries: document.getElementById("industries").value.trim(),

    job_types: document.getElementById("job-types").value.trim(),

    skills: document.getElementById("skills").value.trim(),

    career_goals: document.getElementById("career-goals").value.trim(),
  };

  try {
    await savePreferencesAPI(data);

    showPreferenceMessage("Career profile saved successfully.", false);
  } catch (error) {
    showPreferenceMessage("Could not save profile: " + error.message, true);
  }
}

// ============================================================
// Message
// ============================================================

function showPreferenceMessage(text, error) {
  const element = document.getElementById("preferences-message");

  element.className = error ? "message error" : "message success";

  element.textContent = text;
}

// ============================================================
// Events
// ============================================================

if (preferencesForm) {
  preferencesForm.addEventListener("submit", savePreferences);

  loadPreferences();
}
