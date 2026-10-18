import re

CAREERTASKTYPES = { 
    "jobanalysis", 
    "careeradvice", 
    "resume", 
    "coverletter", 
    "applicationresponse", 
    "jobsummary", 
    "general", 
    }

PERSONALFACTFIELDS = { 
    "skills", 
    "qualifications", 
    "education", 
    "experience", 
    "achievements", 
    "certifications", 
    "employment_history", 
    }

JOBFIELDS = { 
    "id", 
    "title", 
    "company", 
    "location", 
    "industry", 
    "jobtype", 
    "description", 
    "requirements", 
    "salary", 
    "applicationurl", 
    "createdat", 
    }

def normalise(value):
    """Normalise text for deterministic comparisons.""" 
    
    if not isinstance(value, str): 
        return "" 
    
    return " ".join(value.casefold().split())

def valid_job(selected_job): 
    """Validate the structure of a selected database job record.""" 
    
    if not isinstance(selected_job, dict): 
        return False

    job_id = selected_job.get("id") 
    
    if not isinstance(jobid, int) or isinstance(jobid, bool): 
        return False

    if job_id <= 0: 
        return False

    if not isinstance(selected_job.get("title"), str): 
        return False

    if not selected_job["title"].strip(): 
        return False

    if not isinstance(selected_job.get("company"), str): 
        return False

    if not selected_job["company"].strip(): 
        return False

    for field in JOBFIELDS - {"id"}: 
        value = selected_job.get(field) 
    
    if value is not None and not isinstance(value, (str, int, float)): 
        return False
    
    return True

def validate_career_inputs(userrequest, selectedjob, careerdetails=None): 
    """Validate inputs shared by career planning, execution, and review.""" 
    
    if not isinstance(userrequest, str) or not userrequest.strip(): 
        raise ValueError("userrequest is required")

    if not validjob(selectedjob): 
        raise ValueError( "selected_job must contain a valid id, title, and company" )

    if careerdetails is None: 
        careerdetails = {}

    if not isinstance(careerdetails, dict): 
        raise ValueError("careerdetails must be a dictionary")

    return { "userrequest": userrequest.strip(), "selectedjob": selectedjob, "careerdetails": careerdetails, }

def detect_tasktype(userrequest): 
    """Classify common career tasks using conservative keyword matching.""" 
    
    text = normalise(userrequest)

    if any(word in text for word in ( 
        "cover letter", 
        "cover-letter", 
        "write a letter", 
        "application letter", )): 
        return "cover_letter"

    if any(word in text for word in ( "resume", "cv", )): 
        return "resume"

    if any(phrase in text for phrase in ( 
        "skills gap", 
        "skill gap", 
        "missing skills", 
        "skills match", 
        "match my skills",
        "compare my skills", 
        "qualification gap", )): 
        return "skills_gap"

    if any(phrase in text for phrase in ( 
        "application question", 
        "selection criteria", 
        "application response", 
        "answer the employer", 
        "respond to the employer", )): 
        return "application_response"

    if any(phrase in text for phrase in ( 
        "summarise this job", 
        "summarize this job", 
        "job summary", 
        "summarise the job", 
        "summarize the job", 
        "explain this job", 
        "job responsibilities", )): 
        return "job_summary"

    if any(phrase in text for phrase in ( 
        "analyse this job", 
        "analyze this job", 
        "job analysis", 
        "job requirements", 
        "what does this job require", 
        "am i qualified", 
        "am i a good fit", 
        "am i suitable", )): 
        return "job_analysis"

    if any(phrase in text for phrase in ( 
        "career advice", 
        "career path", 
        "career guidance", 
        "career recommendation", 
        "how can i improve", 
        "how do i prepare", 
        "how to prepare", )): 
        return "career_advice"

    return "general"

def job_evidence(selected_job): 
    """Return non-empty job fields that can be used as evidence.""" 
    
    if not isinstance(selected_job, dict): 
        raise ValueError("selectedjob must be a dictionary")

    return { field: selected_job[field] 
            for field in JOBFIELDS 
            if field in selected_job and selected_job[field] is not None and str(selected_job[field]).strip() 
            }

def career_evidence(career_details): 
    """Return supplied personal information without inventing details.""" 
    
    if not isinstance(career_details, dict): 
        raise ValueError("careerdetails must be a dictionary")

    return { key: value 
            for key, value in career_details.items() 
            if value is not None and value != "" and value != [] and value != {} 
            }

def requested_values(user_request, selected_job, career_details=None): 
    """Identify relevant supplied values for a career task.""" 
    inputs = validate_career_inputs( user_request, selected_job, career_details, )

    task_type = detect_tasktype(inputs["user_request"]) 
    
    job_values = job_evidence(inputs["selected_job"]) 
    
    personal_values = career_evidence(inputs["career_details"])

    values = { 
        "jobid": inputs["selectedjob"]["id"], 
        "jobtitle": inputs["selectedjob"]["title"], 
        "company": inputs["selected_job"]["company"], 
    }

    if tasktype in { 
        "jobanalysis", 
        "jobsummary", 
        "coverletter", 
        "resume", 
        "applicationresponse", 
        "careeradvice", 
        "general", }: 

        for field in ( 
            "location", 
            "industry", 
            "jobtype", 
            "description", 
            "requirements", 
            "salary",
            "applicationurl", ): 
            if field in job_values: values[field] = job_values[field]

    if tasktype in { 
        "resume", 
        "coverletter", 
        "applicationresponse", 
        "careeradvice", 
        "general", }: 
            
            values["careerdetails"] = personal_values

    return values

def missinginformation(user_request, selected_job, career_details=None): 
    """Report missing information relevant to common career tasks.""" 
    
    inputs = validate_career_inputs( user_request, selected_job, career_details, )

    tasktype = detect_tasktype(inputs["user_request"]) 
    job = inputs["selected_job"] 
    details = inputs["career_details"] 
    missing = []

    if not job.get("description") and not job.get("requirements"): 
        missing.append( "The selected job has no description or requirements to analyse." )

    if tasktype in { "resume", "coverletter", "applicationresponse", "skillsgap", }: 
        if not details: 
            missing.append( "Career details are unavailable, so personal qualifications " "and experience cannot be verified." )

    return list(dict.fromkeys(missing))

def evidenceidentifiers(selectedjob): 
    """Return stable identifiers actually supplied by the job record.""" 

    if not isinstance(selectedjob, dict): 
        raise ValueError("selectedjob must be a dictionary")

    jobid = selectedjob.get("id")

    if isinstance(jobid, int) and not isinstance(jobid, bool) and jobid > 0: return [f"jobid: {job_id}"]

    return []

def validateevidencereferences(references, selected_job): 
    """Validate references to the selected job without inventing identifiers.""" 
    
    if not isinstance(references, list): 
        return False

    allowed = set(evidenceidentifiers(selectedjob)) 
    allowed.add("selected_job")
    
    return all( isinstance(reference, str) and reference in allowed for reference in references )

def deterministiccompletion(user_request, selected_job, career_details=None, ): 
    """Provide deterministic output only for a simple job-summary request.""" 
    
    inputs = validate_career_inputs( user_request, selected_job, career_details, )

    if detect_tasktype(inputs["user_request"]) != "jobsummary": return None

    job = inputs["selected_job"]

    parts = [ f"Job title: {job['title']}", f"Company: {job['company']}", ]

    labels = { 
        "location": "Location", 
        "industry": "Industry", 
        "job_type": "Employment type", 
        "description": "Description", 
        "requirements": "Requirements", 
        "salary": "Salary", 
    }

    for field, label in labels.items(): 
        value = job.get(field) 
        if value is not None and str(value).strip(): 
            parts.append(f"{label}: {str(value).strip()}")

    return { 
        "result": "\n".join(parts), 
        "evidenceused": evidenceidentifiers(job), 
        "missinginformation": missinginformation( user_request, job, inputs["career_details"], ), 
        }