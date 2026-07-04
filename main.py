import os
import uuid
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Setup directories
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def view_upload_form(request: Request):
    # Render the upload landing page
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def handle_upload(files: list[UploadFile] = File(...)):
    for file in files:
        if file.filename:
            # Give files a unique name to prevent overwriting
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
                
    return RedirectResponse(url="/gallery", status_code=303)

@app.get("/gallery", response_class=HTMLResponse)
async def view_gallery(request: Request):
    # List all files in the upload directory, sorted by newest first
    photos = os.listdir(UPLOAD_DIR)
    # Filter to ensure only images are loaded if needed
    photos = [p for p in photos if p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    # Sort by creation time so newest uploads appear at the top
    photos.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)), reverse=True)
    
    return templates.TemplateResponse("gallery.html", {"request": request, "photos": photos})