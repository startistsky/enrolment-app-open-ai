const jobForm = document.getElementById("job-form");

async function addJob(event) {
  event.preventDefault();

  const data = {
    title: document.getElementById("title").value,

    company: document.getElementById("company").value,

    location: document.getElementById("location").value,

    industry: document.getElementById("industry").value,

    job_type: document.getElementById("job-type").value,

    description: document.getElementById("description").value,

    requirements: document.getElementById("requirements").value,

    salary: document.getElementById("salary").value,

    application_url: document.getElementById("application-url").value,
  };

  try {
    const result = await createJob(data);

    alert(`Job created! ID: ${result.job_id}`);

    jobForm.reset();
  } catch (error) {
    alert(error.message);
  }
}

jobForm.addEventListener("submit", addJob);
