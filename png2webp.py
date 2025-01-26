# Copies the file metadata (modification time, access time, etc.) from the input file to the output file.
import sys
import argparse
import os
from PIL import Image
import json
import shutil
import pathlib

from typing import Dict, Any, Optional

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('png2webp_conversion.log'),
        logging.StreamHandler()
    ]
)

from contextlib import contextmanager

@contextmanager
def open_image(filename: str):
    img = None
    try:
        img = Image.open(filename)
        yield img
    finally:
        if img:
            img.close()

def saveWebp(input_filename: str, lossless: bool = False, quality: int = 100, method: int = 6, use_current_date: bool = False, delete_after: bool = False) -> Dict[str, str]:
    """
    Load an image, extract its metadata, and save it as a webp image with same filename, metadata timedate.

    Args:
        input_filename (str): The filename of the input image.
        lossless (bool, optional): Whether to save the image losslessly. Defaults to False.
        quality (int, optional): The quality of the output image. Defaults to 100.
        method (int, optional): The compression method to use. Quality/speed trade-off (0=fast, 6=slower-better). Defaults to 6.
        use_current_date (bool, optional): Use current date instead of copying original file datetime. Defaults to False.
        delete_after (bool, optional): send to the recycle bin the input image after converting to webp. Defaults to False.

    Returns:
        dict: A dictionary containing information about the output image.
    """
    # Define constants for metadata tags
    PROMPT_TAG = 0x0110
    EXTRA_METADATA_TAG = 0x010f

    # Load the input image and its metadata
    # img = Image.open(input_filename)
    with open_image(input_filename) as img:
        metadata = img.info
        output_metadata = img.getexif()
        logging.info(f"  Converting: {input_filename}")
        for key, value in metadata.items():
            if key == 'prompt':
                prompt_str = json.dumps(json.loads(value))
                output_metadata[PROMPT_TAG] = "Prompt:" + prompt_str
            elif key == 'workflow':
                workflow_str = json.dumps(json.loads(value))
                output_metadata[EXTRA_METADATA_TAG] = "Workflow:" + workflow_str
                EXTRA_METADATA_TAG -= 1
            else:
                value_str = json.dumps(json.loads(value))
                output_metadata[EXTRA_METADATA_TAG] = "{}:{}".format(key, value_str)
                EXTRA_METADATA_TAG -= 1
        for key, value in output_metadata.items():
            logging.info(f"Metadata {key}: {value[:60]}{'...' if len(value) > 60 else ''}")
        exif_data = output_metadata

        # Create the output image
        output_img = img.convert('RGB')

        # Preserve all parts of the filename before the final extension
        base_name = '.'.join(pathlib.Path(input_filename).name.split('.')[:-1])
        base_path = pathlib.Path(input_filename).parent / base_name
        output_path = pathlib.Path(input_filename).parent / f"{base_name}.webp"
        counter = 0
        while output_path.exists():
            counter += 1
            output_path = base_path.parent / f"{base_name}_{counter}.webp"
        output_filename = output_path
        # Save the output image
        output_img.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), output_filename), exif=exif_data, lossless=lossless, quality=quality, method=method)
        logging.info(f"      Output: {output_filename}")

        # Build lists of used and skipped settings
        user_settings = []
        defaults_settings = []
        ignored_settings = []

        # Check each setting
        if lossless:
            user_settings.append('--lossless')
        else:
            ignored_settings.append('--lossless')
    
        if quality != 80:  # Only show if not default
            user_settings.append(f'--quality {quality}')
        else:
            defaults_settings.append(f'--quality {quality}')
    
        if method != 6:  # Only show if not default
            user_settings.append(f'--method {method}')
        else:
            defaults_settings.append(f'--method {method}')
    
        if use_current_date:
            user_settings.append('--use_current_date')
        else:
            ignored_settings.append('--use_current_date')

        if delete_after:
            user_settings.append('--delete_after')
        else:
            ignored_settings.append('--delete_after')

        # Print the settings
        if user_settings:
            logging.info(f"    Settings: {', '.join(user_settings)}")
        if defaults_settings:
            logging.info(f"    Defaults: {', '.join(defaults_settings)}")
        if ignored_settings:
            logging.info(f"     Ignored: {', '.join(ignored_settings)}")

        logging.info(f"Width/Height: {img.size[0]} x {img.size[1]} pixels")
        logging.info("-" * 50)
        # Return information about the output image
        return {
            "filename": output_filename,
        }
# Attempt to import send2trash
try:
    import send2trash
except ImportError:
    send2trash = None  # Set to None if the import fails

def convert_png_to_webp(input_filename, lossless: bool = False, quality: int = 80, method: int = 6, use_current_date: bool = False, delete_after: bool = False):
    """
    Convert a PNG image to WebP format.

    Args:
        input_filename (str): The filename of the input image.
        lossless (bool, optional): Whether to save the image losslessly. Defaults to False.
        quality (int, optional): The quality of the output image. Defaults to 80.
        method (int, optional): The compression method to use. Quality/speed trade-off (0=fast, 6=slower-better). Defaults to 6.
        use_current_date (bool, optional): Use current date instead of copying original file datetime. Defaults to False.
        delete_after (bool, optional): send to the recycle bin the input image after converting to webp. Defaults to False.

    Returns:
        None
    """
    if not os.path.exists(input_filename):
        raise FileNotFoundError(f"Input file {input_filename} does not exist")
    
    if not input_filename.lower().endswith('.png'):
        raise ValueError("Input file must be a PNG image")
    error_saving = False
    try:
        results = saveWebp(input_filename, lossless=lossless, quality=quality, method=method, use_current_date=use_current_date, delete_after=delete_after)
        # print(results)

    except Exception as e:
        logging.error(f"Error converting {input_filename}: {str(e)}")
        error_saving = True

    if not use_current_date and not error_saving:  # Copy the original file's datetime attributes
        shutil.copystat(input_filename, results['filename'])

    # Check if send2trash is available
    if delete_after and not error_saving:
        if send2trash is None:
            user_input = input("The 'send2trash' module is not installed. Would you like to continue without deleting the original PNG files? (yes/no): ")
            if user_input.lower() == 'no':
                print("Please install 'send2trash' and run the script again.")
                return
            else:
                print("Continuing without deleting the original files.")
        else:
            send2trash.send2trash(input_filename)

def main():
    notice="""
example usage:

    Basic Usage (80% quality, good for most cases):
python png2webp.py --path ./images --quality 80

    Faster Conversion (method 4 is slightly faster than default 6, see if you like it):
python png2webp.py --path ./images --quality 80 --method 4

    WebP files will use current datetime of creation:
python png2webp.py --path ./images --quality 80 --use_current_date

    To delete the original PNG files after conversion will require  the 'send2trash' module to be installed.
python png2webp.py --path ./images --quality 80 --delete_after
    
    Lossless Conversion (slower process, almost same size to PNG, generally not advised for most scenarios):
    Caution: Utilizing --lossless combined with --quality 100 significantly increases conversion time.
python png2webp.py --path ./images --lossless --quality 80 --use_current_date
"""
    parser = argparse.ArgumentParser(
        description='Convert PNG images to WebP format while preserving ComfyUI\'s metadata and timestamps.',
    )
    parser.add_argument('--path', help='Path to the directory containing PNG images', type=str, required=True)
    parser.add_argument('--delete_after', help='Send to the recycle bin the PNG images after converting to WebP', action='store_true', default=False)
    parser.add_argument('--use_current_date', help='Use current date instead of copying original file datetime', action='store_true', default=False)
    parser.add_argument('--quality', help='WebP quality (0-100)', type=int, default=80)
    parser.add_argument('--lossless', help='Use lossless compression', action='store_true', default=False)
    parser.add_argument('--method', help='Compression method (0=fast, 6=better)', type=int, choices=range(7), default=6)
    
    if len(sys.argv) == 1:  # No arguments provided
        parser.print_help()
        print(notice)
        return
    # Add this line to parse the arguments
    args = parser.parse_args()

    # Then use args.path instead of parser.path
    if not os.path.exists(args.path):
        print(f"Error: {args.path} does not exist")
        return
    logging.info("Starting PNG to WebP conversion process")
    logging.info("-" * 50)
    for root, dirs, files in os.walk(args.path):
        for file in files:
            if file.endswith('.png'):
                input_filename = os.path.join(root, file)
                convert_png_to_webp(input_filename, lossless=args.lossless, quality=args.quality, method=args.method, use_current_date=args.use_current_date, delete_after=args.delete_after)
    logging.info("Conversion process completed\n")

if __name__ == "__main__":
    main()