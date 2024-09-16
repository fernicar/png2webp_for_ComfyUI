import argparse
import os
from PIL import Image
import json
import shutil
import pathlib
import send2trash

def saveWebp(input_filename: str, lossless: bool = False, quality: int = 100, method: int = 6) -> dict:
    """
    Load an image, extract its metadata, and save it as a webp image with same filename, metadata timedate.

    Args:
        input_filename (str): The filename of the input image.
        lossless (bool, optional): Whether to save the image losslessly. Defaults to False.
        quality (int, optional): The quality of the output image. Defaults to 100.
        method (int, optional): The compression method to use. Quality/speed trade-off (0=fast, 6=slower-better). Defaults to 6.

    Returns:
        dict: A dictionary containing information about the output image.
    """
    # Define constants for metadata tags
    PROMPT_TAG = 0x0110
    EXTRA_METADATA_TAG = 0x010f

    # Load the input image and its metadata
    img = Image.open(input_filename)
    metadata = img.info

    output_metadata = img.getexif()
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
        print(f"\t{key}: {value[:60]}{'...' if len(value) > 60 else ''}")
    exif_data = output_metadata

    # Create the output image
    output_img = img.convert('RGB')

    base_path = pathlib.Path(input_filename).with_suffix('')
    output_path = base_path.with_suffix('.webp')
    counter = 0
    while output_path.exists():
        counter += 1
        output_path = base_path.with_stem(f"{base_path.stem}_{counter}").with_suffix('.webp')
    output_filename = output_path

    # Save the output image
    output_img.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), output_filename), exif=exif_data, lossless=lossless, quality=quality, method=method)

    # Return information about the output image
    return {
        "filename": output_filename,
    }

def convert_png_to_webp(input_filename, lossless: bool = False, quality: int = 100, method: int = 6, same_datetime: bool = True, delete_after: bool = False):
    """
    Convert a PNG image to WebP format.

    Args:
        input_filename (str): The filename of the input image.
        lossless (bool, optional): Whether to save the image losslessly. Defaults to False.
        quality (int, optional): The quality of the output image. Defaults to 100.
        method (int, optional): The compression method to use. Quality/speed trade-off (0=fast, 6=slower-better). Defaults to 6.
        same_datetime (bool, optional): Whether to copy the image datetime to the new webp. Defaults to True.
        delete_after (bool, optional): send to the recycle bin the input image after converting to webp. Defaults to False.

    Returns:
        None
    """
    error_saving = False
    try:
        results = saveWebp(input_filename, lossless=lossless, quality=quality, method=method)
        print(results)

    except Exception as e:
        print(f"Error converting {input_filename}: {str(e)}")
        error_saving = True

    if same_datetime and not error_saving: # Copy the original file's datetime attributes
        shutil.copystat(input_filename, results['filename'])

    # Using the send2trash library, which is a cross-platform library that provides a simple way to move files to the recycle bin
    if delete_after and not error_saving: 
        send2trash.send2trash(input_filename)


def main():
    parser = argparse.ArgumentParser(description='Convert PNG images to WebP format')
    parser.add_argument('--path', help='Path to the directory containing PNG images', required=True)
    parser.add_argument('--delete', help='(bool, optional): send to the recycle bin the PNG images after converting to webp. Defaults to False.', required=False)
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: {args.path} does not exist")
        return

    for root, dirs, files in os.walk(args.path):
        for file in files:
            if file.endswith('.png'):
                input_filename = os.path.join(root, file)
                convert_png_to_webp(input_filename, delete_after=args.delete)

if __name__ == "__main__":
    main()