const form =
    document.getElementById("preferences-form");


form.addEventListener("submit", async function(event) {

    event.preventDefault();


    const data = {

        locations:
            document.getElementById("locations").value,

        industries:
            document.getElementById("industries").value,

        job_types:
            document.getElementById("job-types").value,

        skills:
            document.getElementById("skills").value,

        career_goals:
            document.getElementById("career-goals").value

    };


    await fetch(
        "http://localhost:5000/preferences",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(data)
        }
    );


    alert("Career preferences saved!");
});