import os
import requests
import json
import time
import base64
import mimetypes
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import uuid


load_dotenv()
API_KEY = os.getenv("WSAI_KEY")
# Create result folder if it doesn't exist
os.makedirs("result/videos", exist_ok=True)
os.makedirs("result/images", exist_ok=True)

def compress_image(image_path, max_size_kb=900, quality=85):
    """
    Compress image to target size while maintaining quality.
    Only compresses if image is larger than max_size_kb.

    Args:
        image_path: Path to the image file
        max_size_kb: Target maximum size in KB (default 900KB)
        quality: JPEG quality 1-100 (default 85)

    Returns:
        Compressed image as BytesIO object, or None if no compression needed
    """
    try:
        # Check current file size first
        current_size_kb = os.path.getsize(image_path) / 1024

        # If already small enough, return None (no compression needed)
        if current_size_kb <= max_size_kb:
            print(f"Image already optimized: {current_size_kb:.1f}KB (target: {max_size_kb}KB) - skipping compression")
            return None

        print(f"Image size: {current_size_kb:.1f}KB - compressing to {max_size_kb}KB...")

        img = Image.open(image_path)

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Resize if image is too large (optional - maintains aspect ratio)
        max_dimension = 2048  # Max width or height
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            print(f"Resized from {img.size} to {new_size}")

        # Compress to target size
        output = BytesIO()
        current_quality = quality

        while current_quality > 20:  # Don't go below quality 20
            output.seek(0)
            output.truncate()
            img.save(output, format='JPEG', quality=current_quality, optimize=True)
            size_kb = output.tell() / 1024

            if size_kb <= max_size_kb:
                break

            current_quality -= 5

        output.seek(0)
        print(f"✓ Compressed: {current_size_kb:.1f}KB → {size_kb:.1f}KB (quality: {current_quality})")
        return output

    except Exception as e:
        print(f"Error compressing image: {e}")
        return None


def file_to_base64(file_path, compress=False, max_size_kb=900):
    """
    Helper function to convert a file to a base64 string with the correct MIME type.

    Args:
        file_path: Path to the file
        compress: Whether to compress images (default False)
        max_size_kb: Maximum size in KB for compression (default 900KB)
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "image/jpeg"

    # Compress image if requested and it's an image file
    if compress and mime_type and mime_type.startswith('image/'):
        compressed = compress_image(file_path, max_size_kb=max_size_kb, quality=85)

        # If compression returned data, use it; otherwise use original
        if compressed:
            encoded_string = base64.b64encode(compressed.read()).decode('utf-8')
            return f"data:{mime_type};base64,{encoded_string}"

    # Standard encoding for non-compressed files or when compression not needed
    with open(file_path, "rb") as f:
        encoded_string = base64.b64encode(f.read()).decode('utf-8')

    return f"data:{mime_type};base64,{encoded_string}"

def nano_banana_edit(img_person,img_garment,prompt):
    # 1. Convert User Uploaded Image (img1) to Base64 WITH COMPRESSION
    img_person_b64 = file_to_base64(img_person, compress=True, max_size_kb=900)
    img_garment_b64 = file_to_base64(img_garment, compress=True, max_size_kb=900)



    # Request to Nano Banana Pro API
    url = "https://api.wavespeed.ai/api/v3/google/nano-banana-pro/edit"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "aspect_ratio": "9:16", 
        "enable_base64_output": False,
        "enable_sync_mode": False,
        "images": [img_person_b64, img_garment_b64],  # Up to 3 images supported
        "output_format": "jpeg",  # or "png" if you prefer
        "prompt": prompt,
        "resolution": "1k"  # Options: "1k", "2k", "4k"
    }

    begin = time.time()
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        result = response.json()["data"]
        request_id = result["id"]
        print(f"Task submitted successfully. Request ID: {request_id}")
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

    # Poll for results
    url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    max_retries = 360
    retry_count = 0
    while retry_count < max_retries:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            result = response.json()["data"]
            status = result["status"]
            if status == "completed":
                end = time.time()
                print(f"Task completed in {end - begin} seconds.")
                return result["outputs"][0]  # Returns a URL
            elif status == "failed":
                print(f"Task failed: {result.get('error')}")
                return None
            else:
                print(f"Task still processing. Status: {status}")
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None
        time.sleep(0.1)
        retry_count += 1
    
    print("Task timed out after maximum retries")
    return None



def wani2v(img, prompt, last_img=None, duration=5):
    """
    Updates the Wan Image-to-Video task using the 480p Ultra Fast endpoint.
    
    Args:
        img (str): URL of the starting image.
        prompt (str): Text description of the animation.
        last_img (str, optional): URL of the ending image for interpolation.
        duration (int): Duration of the video in seconds (default 5).
    """
    
    # New Wan 2.2 Ultra Fast Endpoint
    url = "https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.2/i2v-480p-ultra-fast"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    
    # Updated payload structure
    payload = {
        "image": img,
        "prompt": prompt,
        "duration": duration,
        "seed": -1
    }
    
    # Optional: Add last_image if you are doing a transition between two images
    if last_img:
        payload["last_image"] = last_img

    begin = time.time()
    
    # Submit the task
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()["data"]
        request_id = result["id"]
        print(f"Task submitted successfully. Request ID: {request_id}")
    except Exception as e:
        print(f"Submission Error: {e}")
        return None

    # Polling logic
    poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
    max_retries = 240
    retry_count = 0
    
    while retry_count < max_retries:
        response = requests.get(poll_url, headers=headers)
        if response.status_code == 200:
            result = response.json()["data"]
            status = result["status"]
            
            if status == "completed":
                end = time.time()
                print(f"Task completed in {end - begin:.2f} seconds.")
                return result["outputs"][0] # Returns the video URL
            elif status == "failed":
                print(f"Task failed: {result.get('error')}")
                return None
            else:
                print(f"Task still processing. Status: {status}")
        else:
            print(f"Polling Error: {response.status_code}")
            return None
            
        time.sleep(1.0) # Increased slightly to be polite to the API
        retry_count += 1
        
    return None



def save_video(url):
    """Downloads a video from a URL and saves it with a unique UUID name."""
    if url is None:
        print("Error: No URL provided")
        return None
    
    # Ensure the directory exists
    os.makedirs("result/videos", exist_ok=True)
    
    # Generate a unique ID
    unique_id = uuid.uuid4()
    file_path = f"result/videos/{unique_id}.mp4"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"Video saved successfully to {file_path}")
            return file_path
        else:
            print(f"Error downloading video: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def save_photo(url,type):
    """Downloads an image from a URL and saves it with a unique UUID name."""
    if url is None:
        print("Error: No URL provided")
        return None
    
    # Ensure the directory exists
    os.makedirs("result/images", exist_ok=True)
    
    # Generate a unique ID
    unique_id = uuid.uuid4()
    file_path = f"result/images/{unique_id}_{type}.jpeg"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"Image saved successfully to {file_path}")
            return file_path
        else:
            print(f"Error downloading image: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None