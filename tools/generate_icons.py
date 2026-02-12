import os
import sys
import subprocess
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

def create_rounded_icon(source_path, size=1024):
    """
    Creates a macOS-style rounded icon (squircle) from the source image.
    The source image is cropped to fill the square and then rounded.
    """
    # 1. Open source
    src_img = Image.open(source_path).convert("RGBA")
    
    # 2. Resize/Crop to fill the square (Center Crop)
    # This ensures no whitespace if the image is rectangular
    # The image will fill the entire 1024x1024 area
    # UPDATE: User requested padding (smaller visual size).
    # Scale factor 0.80 means approx 10% padding on each side.
    scale_factor = 0.80
    inner_size = int(size * scale_factor)
    
    src_img = ImageOps.fit(src_img, (inner_size, inner_size), method=Image.Resampling.LANCZOS)
    
    # 3. Create mask (L mode) for rounded corners on the inner image
    mask = Image.new("L", (inner_size, inner_size), 0)
    draw = ImageDraw.Draw(mask)
    
    # macOS icon radius is approx 22.37% of size (e.g. 229px for 1024px)
    # Apply rounding relative to the inner size
    radius = int(inner_size * 0.2237)
    draw.rounded_rectangle([(0, 0), (inner_size, inner_size)], radius=radius, fill=255)
    
    # 4. Apply mask
    # Create a new transparent image of full size
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    
    # Calculate offset to center the inner image
    offset = (size - inner_size) // 2
    
    # Paste the source image using the mask
    output.paste(src_img, (offset, offset), mask=mask)
    
    return output

def generate_icons(source_image_path):
    """
    Generates macOS .icns and Windows .ico from a source image.
    Uses Pillow for processing and Windows .ico.
    Uses 'iconutil' for macOS .icns (requires intermediate .iconset).
    """
    source_path = Path(source_image_path).resolve()
    if not source_path.exists():
        print(f"Error: Source image not found at {source_path}")
        return

    output_dir = source_path.parent
    base_name = "icon" # Output filename
    
    print(f"Processing: {source_path}")
    
    # Create the styled icon master image (1024x1024)
    try:
        master_icon = create_rounded_icon(source_path)
    except Exception as e:
        print(f"❌ Failed to process image: {e}")
        return

    # --- 1. Generate Windows .ico (using Pillow) ---
    try:
        print("Generating Windows .ico...")
        icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        ico_path = output_dir / f"{base_name}.ico"
        # Resize master icon for each size
        master_icon.save(ico_path, format='ICO', sizes=icon_sizes)
        print(f"✅ Success: {ico_path}")
    except Exception as e:
        print(f"❌ Failed to generate .ico: {e}")

    # --- 2. Generate macOS .icns (using native tools) ---
    if sys.platform != "darwin":
        print("Skipping .icns generation (requires macOS)")
        return

    print("Generating macOS .icns...")
    iconset_dir = output_dir / f"{base_name}.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir()

    # Standard macOS icon sizes
    specs = [
        (16, 1), (16, 2),
        (32, 1), (32, 2),
        (128, 1), (128, 2),
        (256, 1), (256, 2),
        (512, 1), (512, 2)
    ]

    try:
        for size, scale in specs:
            pixel_size = size * scale
            filename = f"icon_{size}x{size}"
            if scale == 2:
                filename += "@2x"
            filename += ".png"
            
            out_file = iconset_dir / filename
            
            # Resize using Pillow
            resized_icon = master_icon.resize((pixel_size, pixel_size), Image.Resampling.LANCZOS)
            resized_icon.save(out_file, format="PNG")
        
        # Convert iconset to icns
        icns_path = output_dir / f"{base_name}.icns"
        subprocess.run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)], check=True)
        
        # Cleanup
        shutil.rmtree(iconset_dir)
        print(f"✅ Success: {icns_path}")
        
    except Exception as e:
        print(f"❌ Failed to generate .icns: {e}")
        if iconset_dir.exists():
            shutil.rmtree(iconset_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/generate_icons.py <path_to_source_image>")
        print("Example: python tools/generate_icons.py assets/logos/my_logo.png")
    else:
        generate_icons(sys.argv[1])
