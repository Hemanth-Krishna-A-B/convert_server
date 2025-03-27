from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import shutil
import os
from pdf2image import convert_from_path
from pptx import Presentation
from PIL import Image
from supabase import create_client
from dotenv import load_dotenv
import logging

# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or Key not set in the environment variables")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize FastAPI app
app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific domains if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set the upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_temp_file(uploaded_file: UploadFile) -> str:
    """Save uploaded file temporarily."""
    file_path = os.path.join(UPLOAD_DIR, f"{uuid4()}_{uploaded_file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return file_path

def convert_pdf_to_images(pdf_path: str) -> list:
    """Convert PDF to images."""
    try:
        images = convert_from_path(pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting PDF to images: {e}")
    
    image_paths = []
    for idx, image in enumerate(images):
        img_path = f"{pdf_path}_{idx}.png"
        image.save(img_path, "PNG")
        image_paths.append(img_path)
    return image_paths

def convert_pptx_to_images(pptx_path: str) -> list:
    """Convert PPTX to images."""
    try:
        prs = Presentation(pptx_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting PPTX to images: {e}")
    
    image_paths = []
    for idx, slide in enumerate(prs.slides):
        img = Image.new("RGB", (1280, 720), "white")  # Placeholder
        img_path = f"{pptx_path}_{idx}.png"
        img.save(img_path, "PNG")
        image_paths.append(img_path)
    return image_paths

def upload_images_to_supabase(image_paths: list, folder_id: str) -> str:
    """Upload images to Supabase bucket in `images/{id}/` format and return folder URL."""
    folder_path = f"images/{folder_id}/"
    
    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        dest_path = f"{folder_path}{img_name}"  # `images/{id}/image1.png`
        with open(img_path, "rb") as img_file:
            supabase.storage.from_("images").upload(dest_path, img_file)
        os.remove(img_path)  # Clean up local image after upload
    
    return f"https://{SUPABASE_URL}/storage/v1/object/public/{folder_path}"

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Uploads a PDF/PPTX file, converts it to images,
    and saves them inside `images/{id}/` folder in Supabase.
    Returns the public folder URL.
    """
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    file_path = save_temp_file(file)
    folder_id = str(uuid4())  # Generate a unique folder ID
    
    if file.content_type == "application/pdf":
        image_paths = convert_pdf_to_images(file_path)
    else:
        image_paths = convert_pptx_to_images(file_path)
    
    folder_url = upload_images_to_supabase(image_paths, folder_id)
    
    logging.info(f"File {file.filename} processed successfully. Folder URL: {folder_url}")
    
    return JSONResponse(content={"folder_url": folder_url})
