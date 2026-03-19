# png2webp_for_ComfyUI (PNG to WebP Converter)
A PNG converter to WebP while keeping [ComfyUI](https://github.com/comfyanonymous/ComfyUI) embedded workflow and datetime attributes.

This repository contains both a **GUI application** (`main.py`) and a **CLI script** (`png2webp.py`) to convert PNG images to WebP format. Both tools can preserve the original image's embedded metadata and datetime attributes, and optionally delete the original PNG files after conversion. If you need a converter for webui other than [ComfyUI](https://github.com/comfyanonymous/ComfyUI), you can check out this alternative converter: [Takenoko3333/png2webp-for-a1111-and-NAI](https://github.com/Takenoko3333/png2webp-for-a1111-and-NAI)

## 🖥️ GUI Application (main.py)

### Features
- **User-friendly interface** with drag-and-drop functionality
- **Real-time progress tracking** with file-by-file updates
- **Multi-file selection** - select individual files or entire folders
- **Live conversion log** showing detailed processing information
- **Responsive design** with modern Qt interface
- **Stop button** to cancel long-running conversions
- **Results table** displaying conversion status for each file
- **Settings panel** for quality, compression method, and options

### Quick Start
1. Run the GUI: `python main.py`
2. Click "Select Folder" to choose a directory with PNG files
3. Adjust settings (Quality: 0-100, Method: 0-6, Options)
4. Click "Convert" to start processing
5. Monitor progress in real-time
6. View results and logs in the interface

### Interface Overview
- **Settings Group**: Configure quality (0-100), compression method (0=fast, 6=better), and options
- **File Selection**: Choose individual PNG files or entire folders (recursive search)
- **Progress Bar**: Shows overall conversion progress
- **Results Table**: Lists each file with status and details
- **Log Area**: Detailed conversion information and metadata preservation
- **Stop Button**: Cancel conversion at any time (graceful termination)

### Benefits
- **No command line required** - perfect for users who prefer graphical interfaces
- **Visual feedback** - see exactly what's happening during conversion
- **Easy file management** - select folders with hundreds of images at once
- **Error handling** - clear error messages if conversion fails
- **Responsive** - GUI remains interactive during conversion

## 🖥️ CLI Script (png2webp.py)

### Features
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
    pip install PySide6==6.9.1 Pillow send2trash
    ```

## CLI Usage

To convert PNG images to WebP format using **Command line interface**, here are some examples:

Basic CLI Usage (90% quality, good for most cases)
```sh
python png2webp.py --path ./images --quality 90
```

Faster Conversion (method 4 is slightly faster than default 6)
```sh
python png2webp.py --path ./images --quality 90 --method 4
```

Use current datetime instead of original
```sh
python png2webp.py --path ./images --quality 90 --use_current_date
```

Delete original PNG files after conversion (requires send2trash)
```sh
python png2webp.py --path ./images --quality 90 --delete_after
```

Lossless Conversion (slower process, almost same size as PNG)
```sh
python png2webp.py --path ./images --lossless --quality 90
```

### Arguments

- `--path`: Path to the directory containing PNG images (required)
- `--quality`: WebP quality (0-100, default: 90)
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
- For most use cases, the default quality setting of 90 provides a good balance between size and quality
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
