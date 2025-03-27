from fastapi import FastAPI, File, UploadFile, HTTPException, Query
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
    allow_origins=["*"],  # You can restrict this to specific domains like ["https://example.com"]
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set the upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_temp_file(uploaded_file: UploadFile) -> str:
    file_path = os.path.join(UPLOAD_DIR, f"{uuid4()}_{uploaded_file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return file_path

def convert_pdf_to_images(pdf_path: str) -> list:
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
    try:
        prs = Presentation(pptx_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting PPTX to images: {e}")
    
    image_paths = []
    for idx, slide in enumerate(prs.slides):
        img = Image.new("RGB", (1280, 720), "white")  # Placeholder for PPTX slide conversion
        img_path = f"{pptx_path}_{idx}.png"
        img.save(img_path, "PNG")
        image_paths.append(img_path)
    return image_paths

def upload_images_to_supabase(image_paths: list, p_url: str) -> str:
    folder_path = f"images/{p_url}"  # Directly store images inside `images/{p_url}/`
    
    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        dest_path = f"{folder_path}/{img_name}"
        with open(img_path, "rb") as img_file:
            supabase.storage.from_("images").upload(dest_path, img_file)
        os.remove(img_path)  # Clean up local image after upload
    
    return folder_path

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), p_url: str = Query(...)):
    """
    Uploads a PDF/PPTX file, converts it to images, and saves the images
    directly inside `images/{p_url}/` in Supabase storage.
    """
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    file_path = save_temp_file(file)
    
    if file.content_type == "application/pdf":
        image_paths = convert_pdf_to_images(file_path)
    else:
        image_paths = convert_pptx_to_images(file_path)
    
    uploaded_folder = upload_images_to_supabase(image_paths, p_url)
    
    logging.info(f"File {file.filename} processed successfully. Uploaded to: {uploaded_folder}")
    
    return JSONResponse(content={"uploaded_folder": uploaded_folder})
