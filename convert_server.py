from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
import shutil
import os
from pdf2image import convert_from_path
from pptx import Presentation
from PIL import Image
from supabase import create_client

# Supabase Config
SUPABASE_URL = "https://ocuffykvcvgxparyjhbq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9jdWZmeWt2Y3ZneHBhcnlqaGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA3NTI3NzYsImV4cCI6MjA1NjMyODc3Nn0.7IZgiPIkkGOTqcR780mw9Z-LjZ8Kk1qxws_9N7olLbE"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_temp_file(uploaded_file: UploadFile) -> str:
    file_path = os.path.join(UPLOAD_DIR, f"{uuid4()}_{uploaded_file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return file_path

def convert_pdf_to_images(pdf_path: str) -> list:
    images = convert_from_path(pdf_path)
    image_paths = []
    for idx, image in enumerate(images):
        img_path = f"{pdf_path}_{idx}.png"
        image.save(img_path, "PNG")
        image_paths.append(img_path)
    return image_paths

def convert_pptx_to_images(pptx_path: str) -> list:
    prs = Presentation(pptx_path)
    image_paths = []
    for idx, slide in enumerate(prs.slides):
        img = Image.new("RGB", (1280, 720), "white")  # Placeholder
        img_path = f"{pptx_path}_{idx}.png"
        img.save(img_path, "PNG")
        image_paths.append(img_path)
    return image_paths

def upload_images_to_supabase(image_paths: list, folder_name: str) -> str:
    folder_id = str(uuid4())
    folder_path = f"images/{folder_name}/{folder_id}"
    public_urls = []
    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        dest_path = f"{folder_path}/{img_name}"
        with open(img_path, "rb") as img_file:
            supabase.storage.from_("images").upload(dest_path, img_file)
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/images/{dest_path}"
        public_urls.append(public_url)
    return folder_id

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    file_path = save_temp_file(file)
    
    folder_name = os.path.splitext(file.filename)[0]  # Use filename (without extension) as folder name
    
    if file.content_type == "application/pdf":
        image_paths = convert_pdf_to_images(file_path)
    else:
        image_paths = convert_pptx_to_images(file_path)
    
    folder_id = upload_images_to_supabase(image_paths, folder_name)
    
    return JSONResponse(content={"folder_id": folder_id})
