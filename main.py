import os
import uuid
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageOps
import io

app = FastAPI()

# Setup structured directories
BASE_UPLOAD_DIR = "static/uploads"
ORIGINALS_DIR = os.path.join(BASE_UPLOAD_DIR, "originals")
WEB_DIR = os.path.join(BASE_UPLOAD_DIR, "web")
THUMBS_DIR = os.path.join(BASE_UPLOAD_DIR, "thumbs")

for folder in [ORIGINALS_DIR, WEB_DIR, THUMBS_DIR]:
    os.makedirs(folder, exist_ok=True)

# ... your existing setup code ...
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- VERSION FIX OVERRIDE ---
_original_template_response = templates.TemplateResponse
def universal_template_response(*args, **kwargs):
    # If the first argument is a Request object, but we are on an older Starlette version, swap them
    if args and not isinstance(args[0], str):
        # Older Starlette: TemplateResponse(name, context)
        # Newer Starlette: TemplateResponse(request, name, context)
        try:
            return _original_template_response(*args, **kwargs)
        except (TypeError, ValueError):
            # Fallback for your local machine: extract variables and re-align positionally
            request_obj = args[0]
            template_name = args[1]
            context_dict = args[2] if len(args) > 2 else {}
            context_dict["request"] = request_obj
            return _original_template_response(template_name, context_dict)
    return _original_template_response(*args, **kwargs)

templates.TemplateResponse = universal_template_response
# -----------------------------


@app.post("/upload")
async def handle_upload(files: list[UploadFile] = File(...)):
    for file in files:
        if not file.filename:
            continue
            
        # 1. Generate a unique filename and read bytes
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.webp']:
            continue # Skip non-image files
            
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_bytes = await file.read()
        
        # 2. Save the Original untouched file
        original_path = os.path.join(ORIGINALS_DIR, unique_filename)
        with open(original_path, "wb") as buffer:
            buffer.write(file_bytes)
            
        # 3. Process Web & Thumbnails using Pillow
        try:
            # Open image in memory and auto-rotate based on mobile EXIF data
            img = Image.open(io.BytesIO(file_bytes))
            img = ImageOps.exif_transpose(img) 
            
            # Create & Save Web-Optimized Version (Max 1600px width/height maintaining aspect ratio)
            web_img = img.copy()
            web_img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            web_img.save(os.path.join(WEB_DIR, unique_filename), quality=85)
            
            # Create & Save Thumbnail (300x300 hard cropped square for perfect grid alignment)
            thumb_img = ImageOps.fit(img, (300, 300), Image.Resampling.LANCZOS)
            thumb_img.save(os.path.join(THUMBS_DIR, unique_filename), quality=80)
            
        except Exception as e:
            print(f"Error processing image {file.filename}: {e}")
                
    return RedirectResponse(url="/gallery", status_code=303)
    

@app.get("/", response_class=HTMLResponse)
async def view_upload_form(request: Request):
    # Pass request as the FIRST positional argument, 
    # AND include it explicitly in the context dictionary for backwards compatibility
    return templates.TemplateResponse(request, "upload.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def view_gallery(request: Request):
    photos = os.listdir(THUMBS_DIR)
    photos = [p for p in photos if p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    photos.sort(key=lambda x: os.path.getmtime(os.path.join(THUMBS_DIR, x)), reverse=True)
    
    # Same double-delivery layout here
    return templates.TemplateResponse(request, "gallery.html", {"request": request, "photos": photos})