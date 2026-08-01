import os
import subprocess
import requests
import re

# --- Configuration ---
# Searching specifically for "painting" to eliminate sculptures and artifacts
API_URL = "https://api.artic.edu/api/v1/artworks/search?q=painting&query[term][is_public_domain]=true&limit=40&fields=id,title,artist_title,date_display,image_id,classification_title"
OUTPUT_DIR = "videos"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "AIC-User-Agent": "ambient-gallery-personal-project"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_filename(text):
    """Strips illegal characters so the OS saves the file correctly"""
    if not text:
        return "Unknown"
    return re.sub(r'[\\/*?:"<>|]', "", str(text)).strip()

print("Starting generation process...")

response = requests.get(API_URL, headers=HEADERS)
if response.status_code != 200:
    print(f"CRITICAL ERROR: API returned status {response.status_code}")
    exit(1)

artworks = response.json().get("data", [])
print(f"Successfully found {len(artworks)} artworks.")

processed_count = 0

for artwork in artworks:
    if processed_count >= 15:
        break # Stop once we have 15 perfect, landscape-cropped paintings
        
    # Strictly enforce paintings only
    classification = str(artwork.get("classification_title", "")).lower()
    if "painting" not in classification:
        continue 

    image_id = artwork.get("image_id")
    title = artwork.get("title", "Untitled")
    artist = artwork.get("artist_title", "Unknown Artist")
    
    if not image_id:
        continue

    # Create a beautiful filename for Aerial Views to read as metadata natively
    clean_title = clean_filename(title)
    clean_artist = clean_filename(artist)
    file_name = f"{clean_title} - {clean_artist}.mp4"
    out_video = os.path.join(OUTPUT_DIR, file_name)
    temp_img = f"temp_{image_id}.jpg"

    if os.path.exists(out_video):
        print(f"Skipping '{file_name}': Already exists.")
        processed_count += 1
        continue

    # Download high-quality source image
    image_url = f"https://www.artic.edu/iiif/2/{image_id}/full/1000,/0/default.jpg"
    print(f"Downloading: {file_name}")

    img_res = requests.get(image_url, headers=HEADERS)
    if img_res.status_code != 200:
        continue
        
    with open(temp_img, "wb") as f:
        f.write(img_res.content)

    print(f"  -> Cropping to perfect 16:9 and encoding...")
    
    # FFmpeg smart crop: Zooms to fill 1920x1080 without stretching or black bars
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", temp_img,
        "-c:v", "libx264", "-t", "30", "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
        out_video
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(temp_img):
        os.remove(temp_img)
        
    processed_count += 1

print(f"Gallery generation completed! {processed_count} videos processed.")
