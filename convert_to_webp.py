#!/usr/bin/python3
import os
import subprocess
import sys
import json
from pathlib import Path

# Configuration
input_dir = "."  # Current directory
output_dir = "webp_output"
quality = 80
formats = [".jpg", ".jpeg", ".png", ".heic", ".HEIC", ".JPG", ".JPEG", ".PNG"]

def check_exiftool():
    """Check if exiftool is installed and return True if it is."""
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_image_metadata(image_path):
    """Get image metadata using exiftool."""
    try:
        result = subprocess.run(["exiftool", "-j", str(image_path)], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)[0]
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None

def copy_metadata(source_path, dest_path):
    """Copy metadata from source to destination image using exiftool."""
    try:
        # Copy all metadata from source to destination
        subprocess.run([
            "exiftool",
            "-TagsFromFile", str(source_path),
            "-all:all",
            "-overwrite_original",
            str(dest_path)
        ], check=True)
        
        # Specifically ensure date fields are preserved
        date_fields = [
            "-CreateDate",
            "-ModifyDate",
            "-DateTimeOriginal",
            "-FileCreateDate",
            "-FileModifyDate"
        ]
        
        # Copy date fields specifically
        subprocess.run([
            "exiftool",
            "-TagsFromFile", str(source_path),
            *date_fields,
            "-overwrite_original",
            str(dest_path)
        ], check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error copying metadata: {e}")
        return False

def convert_heic_to_jpeg(heic_path, jpeg_path):
    """Convert HEIC to JPEG while preserving metadata."""
    try:
        # First convert HEIC to JPEG using sips
        subprocess.run(["sips", "-s", "format", "jpeg", str(heic_path), "--out", str(jpeg_path)], check=True)
        
        # Then copy metadata if exiftool is available
        if check_exiftool():
            print(f"Copying metadata from HEIC to JPEG: {heic_path} -> {jpeg_path}")
            copy_metadata(heic_path, jpeg_path)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error in HEIC to JPEG conversion: {e}")
        return False

def get_unique_output_path(base_path, output_dir):
    """Generate a unique output path by adding a number suffix if needed."""
    counter = 1
    output_path = Path(output_dir) / f"{base_path.stem}.webp"
    
    while output_path.exists():
        output_path = Path(output_dir) / f"{base_path.stem}_{counter}.webp"
        counter += 1
    
    return output_path

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Check for exiftool
has_exiftool = check_exiftool()
if not has_exiftool:
    print("Warning: exiftool not found. Metadata preservation cannot be verified.")
    print("Please install exiftool for better metadata handling:")
    print("  - macOS: brew install exiftool")
    print("  - Linux: sudo apt-get install exiftool")
    print("  - Windows: Download from https://exiftool.org/")

# Get all image files
image_files = []
for fmt in formats:
    image_files.extend(list(Path(input_dir).glob(f"*{fmt}")))

print(f"Found {len(image_files)} images to convert")

# Convert each image
successful_conversions = 0
metadata_preserved = 0

for img_path in image_files:
    output_path = get_unique_output_path(img_path, output_dir)
    
    try:
        # Special handling for HEIC files
        if img_path.suffix.lower() == '.heic':
            # First convert HEIC to JPEG using sips (built into macOS)
            temp_jpg = Path(output_dir) / f"{img_path.stem}_temp.jpg"
            print(f"Converting HEIC to JPEG: {img_path} -> {temp_jpg}")
            
            if not convert_heic_to_jpeg(img_path, temp_jpg):
                raise Exception("Failed to convert HEIC to JPEG")
            
            # Then convert JPEG to WebP
            cmd = ["cwebp", "-q", str(quality), "-metadata", "all", str(temp_jpg), "-o", str(output_path)]
            print(f"Converting JPEG to WebP: {temp_jpg} -> {output_path}")
            subprocess.run(cmd, check=True)
            
            # Remove temporary JPEG
            temp_jpg.unlink()
        else:
            # Direct conversion for other formats
            cmd = ["cwebp", "-q", str(quality), "-metadata", "all", str(img_path), "-o", str(output_path)]
            print(f"Converting {img_path} to WebP")
            subprocess.run(cmd, check=True)
        
        # Copy metadata from original to converted file if exiftool is available
        if has_exiftool:
            if copy_metadata(img_path, output_path):
                metadata_preserved += 1
                print(f"Metadata successfully preserved for {img_path}")
            else:
                print(f"Warning: Failed to preserve metadata for {img_path}")
        
        successful_conversions += 1
    
    except subprocess.CalledProcessError as e:
        print(f"Error converting {img_path}: {e}")
        print(f"Command that failed: {' '.join(e.cmd) if isinstance(e.cmd, list) else e.cmd}")
        print(f"Return code: {e.returncode}")
        if hasattr(e, 'output') and e.output:
            print(f"Output: {e.output}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Error: {e.stderr}")
    except Exception as e:
        print(f"Unexpected error converting {img_path}: {e}")

print(f"\nConversion Summary:")
print(f"Successfully converted {successful_conversions} out of {len(image_files)} images to WebP format")
if has_exiftool:
    print(f"Metadata preserved for {metadata_preserved} out of {successful_conversions} images")