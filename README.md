# png2webp_for_ComfyUI (PNG to WebP Converter)
A PNG converter to WebP while keeping [ComfyUI](https://github.com/comfyanonymous/ComfyUI) embedded workflow and datetime attributes.

This repository contains a Python script to convert PNG images to WebP format. The script can also preserve the original image’s embedded metadata and datetime attributes, and optionally delete the original PNG files after conversion. If you need a converter for webui other than [ComfyUI](https://github.com/comfyanonymous/ComfyUI), you can check out this alternative converter: [Takenoko3333/png2webp-for-a1111-and-NAI](https://github.com/Takenoko3333/png2webp-for-a1111-and-NAI)

## Features

- Convert PNG images to WebP format
- Will search in subfolders
- Configurable quality settings (0-100)
- Configurable compression method (0=fast, 6=better)
- Option to save images with lossless compression
- Preserve original ComfyUI's workflow
- Preserve original image datetime attributes
- Option to use current date instead of original datetime
- Option to delete original PNG images after conversion (send to Recycle bin)
- Detailed conversion logging to 'png2webp_conversion.log'

## File Naming
When converting files, the script automatically handles naming conflicts by appending a counter (e.g., image_1.webp, image_2.webp) if a file with the same name already exists.

## Logging
The script automatically logs all conversion operations to 'png2webp_conversion.log', providing detailed information about each conversion process including success and any potential errors.

## Requirements

- Python 3.x
- Pillow
- send2trash (optional, required only for delete functionality)

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/fernicar/png2webp_for_ComfyUI.git
    cd png2webp_for_ComfyUI
    ```

2. Install the required packages:
    ```sh
    pip install Pillow send2trash
    ```

## Usage

To convert PNG images to WebP format, here are some example commands:

Basic Usage (80% quality, good for most cases)
```sh
python png2webp.py --path ./images --quality 80
```

Faster Conversion (method 4 is slightly faster than default 6)
```sh
python png2webp.py --path ./images --quality 80 --method 4
```

Use current datetime instead of original
```sh
python png2webp.py --path ./images --quality 80 --use_current_date
```

Delete original PNG files after conversion (requires send2trash)
```sh
python png2webp.py --path ./images --quality 80 --delete_after
```

Lossless Conversion (slower process, almost same size as PNG)
```sh
python png2webp.py --path ./images --lossless --quality 80
```

### Arguments

- `--path`: Path to the directory containing PNG images (required)
- `--quality`: WebP quality (0-100, default: 80)
- `--method`: Compression method (0=fast, 6=better, default: 6)
- `--lossless`: Use lossless compression (optional)
- `--use_current_date`: Use current date instead of original file datetime (optional)
- `--delete_after`: Send the PNG images to the recycle bin after converting to WebP (optional)

## Example
```sh
python png2webp.py --path ./images --delete_after
```
This command will convert all PNG images in the `./images` directory and subdirectoriesto WebP format and send the original PNG images to the recycle bin.

## Best Practices
- For most use cases, the default quality setting of 80 provides a good balance between size and quality
- Use `--method 4` for faster conversion if speed is priority
- The `--lossless` option with `--quality 100` will significantly increase conversion time
- Always backup important files before using the `--delete_after` option

## Output Information
During conversion, the script displays:
- Input and output filenames
- Applied settings and defaults
- Image dimensions
- Preserved metadata
- Conversion status

## Code Overview

### `saveWebp` Function

This function loads a PNG image, extracts its metadata, and saves it as a WebP image with the same filename and metadata.

### `convert_png_to_webp` Function

This function converts a PNG image to WebP format, optionally preserving the original image's datetime attributes and sending the original PNG image to the recycle bin.

### `main` Function

This function parses command-line arguments and processes all PNG images in the specified directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
