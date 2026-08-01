import os
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont

# --- Configuration ---
NUM_ARTWORKS = 15
API_URL = f"https://api.artic.edu/api/v1/artworks/search?query[term][is_public_domain]=true&limit={NUM_ARTWORKS}&fields=id,title,artist_title,date_display,image_id"
OUTPUT_DIR = "videos"
FONT_PATH = "Roboto-Regular.ttf"
FONT_URL = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Download Font if missing
if not os.path.exists(FONT_PATH):
    print("Downloading font...")
    r = requests.get(FONT_URL)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)

# 2. Fetch Artworks Metadata
print("Fetching artwork metadata from museum API...")
response = requests.get(API_URL)
artworks = response.json().get("data", [])

# 3. Process Each Artwork
for artwork in artworks:
    image_id = artwork.get("image_id")
    if not image_id:
        continue

    title = artwork.get("title", "Untitled")
    artist = artwork.get("artist_title", "Unknown Artist")
    date = artwork.get("date_display", "")
    
    out_video = os.path.join(OUTPUT_DIR, f"{image_id}.mp4")
    temp_img = f"temp_{image_id}.jpg"

    if os.path.exists(out_video):
        print(f"Video already exists for '{title}'. Skipping.")
        continue

    image_url = f"https://www.artic.edu/iiif/2/{image_id}/full/1920,/0/default.jpg"
    print(f"Processing: {title} by {artist}")

    # Download source image
    img_res = requests.get(image_url)
    if img_res.status_code != 200:
        continue
    with open(temp_img, "wb") as f:
        f.write(img_res.content)

    # Process overlay with Pillow
    img = Image.open(temp_img).convert("RGBA")
    width, height = img.size

    # Create dark gradient/shadow bar at the bottom for readability
    bar_height = int(height * 0.18)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, height - bar_height), (width, height)], fill=(0, 0, 0, 160))
    
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Load font sizes scaled to image height
    font_title = ImageFont.truetype(FONT_PATH, size=int(height * 0.038))
    font_sub = ImageFont.truetype(FONT_PATH, size=int(height * 0.026))

    padding_x = int(width * 0.04)
    y_title = height - bar_height + int(bar_height * 0.2)
    y_sub = y_title + int(height * 0.048)

    label_sub = f"{artist} ({date})" if date else artist

    # Draw Title and Subtitle
    draw.text((padding_x, y_title), title, font=font_title, fill=(255, 255, 255))
    draw.text((padding_x, y_sub), label_sub, font=font_sub, fill=(200, 200, 200))

    img.save(temp_img)

    # FFmpeg: Convert image to 1080p 30-sec MP4 video loop
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
