from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
import shutil
import os
from pdf2image import convert_from_path
from pptx import Presentation
from PIL import Image
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
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
    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        dest_path = f"{folder_path}/{img_name}"
        with open(img_path, "rb") as img_file:
            supabase.storage.from_("images").upload(dest_path, img_file)
    return folder_id

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    file_path = save_temp_file(file)
    folder_name = os.path.splitext(file.filename)[0]
    
    if file.content_type == "application/pdf":
        image_paths = convert_pdf_to_images(file_path)
    else:
        image_paths = convert_pptx_to_images(file_path)
    
    folder_id = upload_images_to_supabase(image_paths, folder_name)
    
    return JSONResponse(content={"folder_id": folder_id})

