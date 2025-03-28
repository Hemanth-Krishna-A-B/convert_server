from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import shutil
import os
from pdf2image import convert_from_path
from pptx2pdf import convert as pptx_to_pdf
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
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
    """Convert PPTX to images by first converting it to PDF."""
    try:
        pdf_path = pptx_path.replace(".pptx", ".pdf")
        pptx_to_pdf(pptx_path, pdf_path)  # Convert PPTX to PDF
        return convert_pdf_to_images(pdf_path)  # Convert resulting PDF to images
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting PPTX to images: {e}")

def upload_images_to_supabase(image_paths: list, folder_id: str) -> list:
    """Upload images to Supabase and return a list of public URLs."""
    folder_path = f"images/{folder_id}/"
    public_urls = []
    
    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        dest_path = f"{folder_path}{img_name}"
        
        with open(img_path, "rb") as img_file:
            supabase.storage.from_("images").upload(dest_path, img_file)
        
        public_url = supabase.storage.from_("images").get_public_url(dest_path)
        public_urls.append(public_url)

        os.remove(img_path)  # Cleanup local image

    return public_urls  # Return list of URLs

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Uploads a PDF/PPTX file, converts it to images,
    and returns a list of public image URLs.
    """
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    file_path = save_temp_file(file)
    folder_id = str(uuid4())  
    
    if file.content_type == "application/pdf":
        image_paths = convert_pdf_to_images(file_path)
    else:
        image_paths = convert_pptx_to_images(file_path)
    
    public_urls = upload_images_to_supabase(image_paths, folder_id)

    logging.info(f"File {file.filename} processed successfully. Uploaded images: {public_urls}")

    return JSONResponse(content={"image_urls": public_urls})
