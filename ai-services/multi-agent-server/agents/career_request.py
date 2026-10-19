JOB_FIELDS = {
    "id",
    "title",
    "company",
    "location",
    "industry",
    "job_type",
    "description",
    "requirements",
    "salary",
    "application_url",
    "created_at",
}


def job_evidence(selected_job):
    """Return available fields from the selected job record."""

    if not isinstance(selected_job, dict):
        raise ValueError("selected_job must be a dictionary")

    return {
        field: selected_job[field]
        for field in JOB_FIELDS
        if field in selected_job
        and selected_job[field] is not None
        and str(selected_job[field]).strip()
    }
