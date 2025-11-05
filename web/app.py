"""
Web Application for Data Engineering Study Management

FastAPI application providing a web interface for managing projects,
certifications, progress, tests, and benchmarks.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel

# Add parent directory to path to import CLI modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.utils import (
    load_progress, save_progress, load_config,
    get_project_path, get_cert_path, BASE_DIR
)
from cli.projects import PROJECTS
from cli.certifications import CERTIFICATIONS

app = FastAPI(
    title="Data Engineering Study Manager",
    description="Web interface for managing data engineering studies",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Templates
templates = Jinja2Templates(directory="web/templates")


# Pydantic models
class ProjectUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class CertUpdate(BaseModel):
    topic: Optional[str] = None
    status: Optional[str] = None
    score: Optional[int] = None


# Routes

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    progress = load_progress()

    # Calculate stats
    projects_data = progress.get('projects', {})
    certs_data = progress.get('certifications', {})

    stats = {
        'total_projects': len(PROJECTS),
        'completed_projects': sum(1 for p in projects_data.values() if p.get('status') == 'completed'),
        'total_certs': len(CERTIFICATIONS),
        'certified': sum(1 for c in certs_data.values() if c.get('status') == 'certified'),
        'study_sessions': sum(len(p.get('sessions', [])) for p in projects_data.values()) +
                          sum(len(c.get('study_sessions', [])) for c in certs_data.values())
    }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats
    })


@app.get("/api/projects")
async def get_projects(type: Optional[str] = None, difficulty: Optional[int] = None):
    """Get all projects with optional filters"""
    filtered_projects = PROJECTS.copy()

    if type and type != 'all':
        filtered_projects = {k: v for k, v in filtered_projects.items() if v['type'] == type}

    if difficulty:
        filtered_projects = {k: v for k, v in filtered_projects.items() if v['difficulty'] == difficulty}

    # Add progress information
    progress = load_progress()
    for project_id, project in filtered_projects.items():
        project_progress = progress.get('projects', {}).get(project_id, {})
        project['status'] = project_progress.get('status', 'not_started')
        project['sessions'] = len(project_progress.get('sessions', []))

    return filtered_projects


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get specific project details"""
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")

    project = PROJECTS[project_id].copy()
    progress = load_progress()
    project_progress = progress.get('projects', {}).get(project_id, {})

    project['status'] = project_progress.get('status', 'not_started')
    project['started_at'] = project_progress.get('started_at')
    project['completed_at'] = project_progress.get('completed_at')
    project['sessions'] = project_progress.get('sessions', [])
    project['notes'] = project_progress.get('notes')

    return project


@app.post("/api/projects/{project_id}/start")
async def start_project(project_id: str):
    """Start a project"""
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")

    progress = load_progress()
    if 'projects' not in progress:
        progress['projects'] = {}

    if project_id not in progress['projects']:
        progress['projects'][project_id] = {
            'status': 'in_progress',
            'started_at': datetime.now().isoformat(),
            'sessions': []
        }
    else:
        progress['projects'][project_id]['status'] = 'in_progress'

    progress['projects'][project_id]['sessions'].append({
        'started_at': datetime.now().isoformat()
    })

    save_progress(progress)

    return {"status": "success", "message": "Project started"}


@app.post("/api/projects/{project_id}/complete")
async def complete_project(project_id: str, update: ProjectUpdate):
    """Complete a project"""
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")

    progress = load_progress()
    if 'projects' not in progress:
        progress['projects'] = {}

    if project_id not in progress['projects']:
        progress['projects'][project_id] = {}

    progress['projects'][project_id]['status'] = 'completed'
    progress['projects'][project_id]['completed_at'] = datetime.now().isoformat()

    if update.notes:
        progress['projects'][project_id]['notes'] = update.notes

    save_progress(progress)

    return {"status": "success", "message": "Project completed"}


@app.get("/api/certifications")
async def get_certifications(provider: Optional[str] = None, difficulty: Optional[int] = None):
    """Get all certifications with optional filters"""
    filtered_certs = CERTIFICATIONS.copy()

    if provider and provider != 'all':
        filtered_certs = {k: v for k, v in filtered_certs.items() if v['provider'] == provider}

    if difficulty:
        filtered_certs = {k: v for k, v in filtered_certs.items() if v['difficulty'] == difficulty}

    # Add progress information
    progress = load_progress()
    for cert_id, cert in filtered_certs.items():
        cert_progress = progress.get('certifications', {}).get(cert_id, {})
        cert['status'] = cert_progress.get('status', 'not_started')
        cert['completed_topics'] = cert_progress.get('completed_topics', [])
        cert['progress'] = len(cert_progress.get('completed_topics', [])) / len(cert['topics']) * 100 if cert['topics'] else 0

    return filtered_certs


@app.get("/api/certifications/{cert_id}")
async def get_certification(cert_id: str):
    """Get specific certification details"""
    if cert_id not in CERTIFICATIONS:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert = CERTIFICATIONS[cert_id].copy()
    progress = load_progress()
    cert_progress = progress.get('certifications', {}).get(cert_id, {})

    cert['status'] = cert_progress.get('status', 'not_started')
    cert['started_at'] = cert_progress.get('started_at')
    cert['completed_topics'] = cert_progress.get('completed_topics', [])
    cert['study_sessions'] = cert_progress.get('study_sessions', [])
    cert['progress'] = len(cert_progress.get('completed_topics', [])) / len(cert['topics']) * 100 if cert['topics'] else 0

    if cert['status'] == 'certified':
        cert['certified_at'] = cert_progress.get('certified_at')
        cert['score'] = cert_progress.get('score')

    return cert


@app.post("/api/certifications/{cert_id}/start")
async def start_certification(cert_id: str, update: CertUpdate):
    """Start studying a certification"""
    if cert_id not in CERTIFICATIONS:
        raise HTTPException(status_code=404, detail="Certification not found")

    progress = load_progress()
    if 'certifications' not in progress:
        progress['certifications'] = {}

    if cert_id not in progress['certifications']:
        progress['certifications'][cert_id] = {
            'status': 'in_progress',
            'started_at': datetime.now().isoformat(),
            'completed_topics': [],
            'study_sessions': []
        }

    progress['certifications'][cert_id]['study_sessions'].append({
        'started_at': datetime.now().isoformat(),
        'topic': update.topic
    })

    save_progress(progress)

    return {"status": "success", "message": "Certification study started"}


@app.post("/api/certifications/{cert_id}/topic/{topic}")
async def complete_topic(cert_id: str, topic: str):
    """Mark a certification topic as complete"""
    if cert_id not in CERTIFICATIONS:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert = CERTIFICATIONS[cert_id]
    if topic not in cert['topics']:
        raise HTTPException(status_code=404, detail="Topic not found")

    progress = load_progress()
    if 'certifications' not in progress:
        progress['certifications'] = {}

    if cert_id not in progress['certifications']:
        progress['certifications'][cert_id] = {
            'completed_topics': [],
            'status': 'in_progress'
        }

    if 'completed_topics' not in progress['certifications'][cert_id]:
        progress['certifications'][cert_id]['completed_topics'] = []

    if topic not in progress['certifications'][cert_id]['completed_topics']:
        progress['certifications'][cert_id]['completed_topics'].append(topic)

    # Check if all topics completed
    if len(progress['certifications'][cert_id]['completed_topics']) == len(cert['topics']):
        progress['certifications'][cert_id]['status'] = 'ready_for_exam'

    save_progress(progress)

    return {"status": "success", "message": f"Topic '{topic}' completed"}


@app.post("/api/certifications/{cert_id}/certified")
async def mark_certified(cert_id: str, update: CertUpdate):
    """Mark certification as obtained"""
    if cert_id not in CERTIFICATIONS:
        raise HTTPException(status_code=404, detail="Certification not found")

    progress = load_progress()
    if 'certifications' not in progress:
        progress['certifications'] = {}

    if cert_id not in progress['certifications']:
        progress['certifications'][cert_id] = {}

    progress['certifications'][cert_id]['status'] = 'certified'
    progress['certifications'][cert_id]['certified_at'] = datetime.now().isoformat()

    if update.score:
        progress['certifications'][cert_id]['score'] = update.score

    save_progress(progress)

    return {"status": "success", "message": "Certification marked as obtained"}


@app.get("/api/progress")
async def get_progress():
    """Get full progress data"""
    progress = load_progress()

    # Calculate statistics
    projects_data = progress.get('projects', {})
    certs_data = progress.get('certifications', {})

    stats = {
        'projects': {
            'total': len(PROJECTS),
            'completed': sum(1 for p in projects_data.values() if p.get('status') == 'completed'),
            'in_progress': sum(1 for p in projects_data.values() if p.get('status') == 'in_progress'),
            'not_started': len(PROJECTS) - len(projects_data)
        },
        'certifications': {
            'total': len(CERTIFICATIONS),
            'certified': sum(1 for c in certs_data.values() if c.get('status') == 'certified'),
            'ready_for_exam': sum(1 for c in certs_data.values() if c.get('status') == 'ready_for_exam'),
            'in_progress': sum(1 for c in certs_data.values() if c.get('status') == 'in_progress'),
            'not_started': len(CERTIFICATIONS) - len(certs_data)
        },
        'study_sessions': {
            'total': sum(len(p.get('sessions', [])) for p in projects_data.values()) +
                     sum(len(c.get('study_sessions', [])) for c in certs_data.values())
        },
        'last_updated': progress.get('last_updated')
    }

    return {
        "progress": progress,
        "stats": stats
    }


@app.delete("/api/progress/reset")
async def reset_progress():
    """Reset all progress"""
    # Create backup
    progress = load_progress()
    backup_file = Path('.data') / f'progress_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    with open(backup_file, 'w') as f:
        json.dump(progress, f, indent=2)

    # Reset
    new_progress = {
        'projects': {},
        'certifications': {},
        'last_updated': datetime.now().isoformat()
    }

    save_progress(new_progress)

    return {
        "status": "success",
        "message": "Progress reset successfully",
        "backup": str(backup_file)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
