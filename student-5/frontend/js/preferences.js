const form = document.getElementById("preferences-form");

async function loadPreferences() {
  try {
    const data = await getPreferences();

    if (!data) return;

    document.getElementById("locations").value = data.locations || "";

    document.getElementById("industries").value = data.industries || "";

    document.getElementById("job-types").value = data.job_types || "";

    document.getElementById("skills").value = data.skills || "";

    document.getElementById("career-goals").value = data.career_goals || "";
  } catch (error) {
    console.error(error);
  }
}

form.addEventListener("submit", async function (event) {
  event.preventDefault();

  const data = {
    locations: document.getElementById("locations").value,

    industries: document.getElementById("industries").value,

    job_types: document.getElementById("job-types").value,

    skills: document.getElementById("skills").value,

    career_goals: document.getElementById("career-goals").value,
  };

  try {
    await savePreferences(data);

    alert("Career preferences saved!");
  } catch (error) {
    alert(error.message);
  }
});

async function deleteAllPreferences() {
  if (!confirm("Delete your preferences?")) {
    return;
  }

  try {
    await deletePreferences();

    form.reset();

    alert("Preferences deleted.");
  } catch (error) {
    alert(error.message);
  }
}

document.addEventListener("DOMContentLoaded", loadPreferences);
