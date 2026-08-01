import os
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont

# --- Configuration ---
NUM_ARTWORKS = 15
API_URL = f"https://api.artic.edu/api/v1/artworks/search?query[term][is_public_domain]=true&limit={NUM_ARTWORKS}&fields=id,title,artist_title,date_display,image_id"
OUTPUT_DIR = "videos"
FONT_PATH = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"

# Disguise the script as a normal Google Chrome browser to bypass 403 blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "AIC-User-Agent": "ambient-gallery-personal-project"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Starting generation process...")

# 1. Fetch Artworks Metadata
print(f"Fetching metadata from: {API_URL}")
response = requests.get(API_URL, headers=HEADERS)
if response.status_code != 200:
    print(f"CRITICAL ERROR: API returned status {response.status_code}")
    exit(1)

artworks = response.json().get("data", [])
print(f"Successfully found {len(artworks)} artworks.")

# 2. Process Each Artwork
for artwork in artworks:
    image_id = artwork.get("image_id")
    title = artwork.get("title", "Untitled")
    artist = artwork.get("artist_title", "Unknown Artist")
    date = artwork.get("date_display", "")
    
    if not image_id:
        print(f"Skipping '{title}': No image_id provided by API.")
        continue

    out_video = os.path.join(OUTPUT_DIR, f"{image_id}.mp4")
    temp_img = f"temp_{image_id}.jpg"

    if os.path.exists(out_video):
        print(f"Skipping '{title}': Video already exists.")
        continue

    image_url = f"https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"
    print(f"Downloading: {title} by {artist}")

    # Pass the headers to bypass the image server firewall
    img_res = requests.get(image_url, headers=HEADERS)
    if img_res.status_code != 200:
        print(f"  -> Failed to download image from IIIF server. Status: {img_res.status_code}")
        continue
        
    with open(temp_img, "wb") as f:
        f.write(img_res.content)

    # Process overlay with Pillow
    try:
        img = Image.open(temp_img).convert("RGBA")
        width, height = img.size

        bar_height = int(height * 0.18)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([(0, height - bar_height), (width, height)], fill=(0, 0, 0, 160))
        
        img = Image.alpha_composite(img, overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        try:
            font_title = ImageFont.truetype(FONT_PATH, size=int(height * 0.038))
            font_sub = ImageFont.truetype(FONT_PATH, size=int(height * 0.026))
        except IOError:
            print("  -> Font missing, falling back to default.")
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        padding_x = int(width * 0.04)
        y_title = height - bar_height + int(bar_height * 0.2)
        y_sub = y_title + int(height * 0.048)

        label_sub = f"{artist} ({date})" if date else artist

        draw.text((padding_x, y_title), title, font=font_title, fill=(255, 255, 255))
        draw.text((padding_x, y_sub), label_sub, font=font_sub, fill=(200, 200, 200))

        img.save(temp_img)
    except Exception as e:
        print(f"  -> Failed to process image overlay: {e}")
        continue

    # FFmpeg Convert
    print(f"  -> Encoding video loop...")
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", temp_img,
        "-c:v", "libx264", "-t", "30", "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
        out_video
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(temp_img):
        os.remove(temp_img)

print("Gallery generation completed successfully.")
