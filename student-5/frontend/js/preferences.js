const form = document.getElementById("preferences-form");

async function loadPreferences() {
  try {
    const data = await getPreferences();

    if (!data || !data.id) {
      return;
    }

    document.getElementById("locations").value = data.locations || "";

    document.getElementById("industries").value = data.industries || "";

    document.getElementById("job-types").value = data.job_types || "";

    document.getElementById("skills").value = data.skills || "";

    document.getElementById("career-goals").value = data.career_goals || "";
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function showMessage(text, type = "success") {
  const message = document.getElementById("preferences-message");

  message.className = `message ${type}`;

  message.textContent = text;
}

form.addEventListener("submit", async function (event) {
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

    showMessage("Preferences saved successfully.", "success");

    loadRecommendations();
  } catch (error) {
    showMessage(error.message, "error");
  }
});

async function clearPreferences() {
  try {
    await deletePreferencesAPI();

    form.reset();

    showMessage("Preferences cleared.", "success");

    document.getElementById("recommendations").innerHTML = "";
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadRecommendations() {
  const container = document.getElementById("recommendations");

  try {
    const jobs = await getRecommendations();

    container.innerHTML = "";

    if (jobs.length === 0) {
      container.innerHTML = `<div class="empty-state">
                    No matching opportunities yet.
                </div>`;

      return;
    }

    jobs.forEach((job) => {
      container.innerHTML += `

                <article class="job-card">

                    <span class="tag">
                        ${job.match_score}
                        point match
                    </span>

                    <h3>
                        ${job.title}
                    </h3>

                    <p class="company">
                        ${job.company}
                    </p>

                    <p>
                        📍 ${job.location}
                    </p>

                    <p>
                        ${job.industry}
                    </p>

                    <a href="/job.html?id=${job.id}">
                        View Opportunity →
                    </a>

                </article>
            `;
    });
  } catch (error) {
    container.innerHTML = `
            <div class="message error">
                ${error.message}
            </div>
        `;
  }
}

loadPreferences();
loadRecommendations();
