from fastapi import APIRouter, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
import os
from pathlib import Path


from ..core import * 


# --- Configuration ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "supersecret")

# --- Setup ---
router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# --- Helper Function to check cookie ---
def get_admin_user(request: Request):
    if request.cookies.get("admin_auth") != ADMIN_PASSWORD:
        raise HTTPException(status_code=307, detail="Not authenticated", headers={"Location": "/admin/login"})
    return True

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: Session = Depends(get_session), is_admin: bool = Depends(get_admin_user)):
    users = session.exec(select(User).order_by(User.score.desc())).all()
    tasks = session.exec(select(Task).order_by(Task.id)).all() 
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "users": users,
        "tasks": tasks  
    })

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def handle_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/dashboard", status_code=303)

        response.set_cookie(key="admin_auth", value=ADMIN_PASSWORD, httponly=True )
        return response
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Incorrect password"}, status_code=401)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: Session = Depends(get_session), is_admin: bool = Depends(get_admin_user)):
    users = session.exec(select(User).order_by(User.score.desc())).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "users": users})

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login")
    response.delete_cookie("admin_auth")
    return response


@router.post("/add_task" )
async def add_task(
    session: Session = Depends(get_session),
    is_admin: bool = Depends(get_admin_user),
    name: str = Form(...),
    description: str = Form(...),
    points: int = Form(...),
    link: str = Form(...),
    icon: str = Form(...)
):

    new_task = Task(
        name=name,
        description=description,
        points=points,
        link=link,
        icon=icon
    )
    

    session.add(new_task)
    session.commit()

    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.post("/edit_task/{task_id}")
async def edit_task(
    task_id: int,
    session: Session = Depends(get_session),
    is_admin: bool = Depends(get_admin_user),
    name: str = Form(...),
    description: str = Form(...),
    points: int = Form(...),
    link: str = Form(...),
    icon: str = Form(...)
):

    task_to_edit = session.get(Task, task_id)
    if not task_to_edit:
        raise HTTPException(status_code=404, detail="Task not found")

    task_to_edit.name = name
    task_to_edit.description = description
    task_to_edit.points = points
    task_to_edit.link = link
    task_to_edit.icon = icon
    
    session.add(task_to_edit)
    session.commit()
    
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.get("/delete_task/{task_id}")
async def delete_task(
    task_id: int,
    session: Session = Depends(get_session),
    is_admin: bool = Depends(get_admin_user)
):

    task_to_delete = session.get(Task, task_id)
    if not task_to_delete:
        raise HTTPException(status_code=404, detail="Task not found")

    
    session.delete(task_to_delete)
    session.commit()
    
    return RedirectResponse(url="/admin/dashboard", status_code=303)

