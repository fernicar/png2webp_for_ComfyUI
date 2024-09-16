# png2webp_for_ComfyUI (PNG to WebP Converter)
A PNG converter to WebP while keeping [ComfyUI](https://github.com/comfyanonymous/ComfyUI) embedded workflow and datetime attributes.

This repository contains a Python script to convert PNG images to WebP format. The script can also preserve the original image’s embedded metadata and datetime attributes, and optionally delete the original PNG files after conversion. If you need a converter for webui other than [ComfyUI](https://github.com/comfyanonymous/ComfyUI), you can check out this alternative converter: [Takenoko3333/png2webp-for-a1111-and-NAI](https://github.com/Takenoko3333/png2webp-for-a1111-and-NAI)

## Features

- Convert PNG images to WebP format.
- Will search in subfolders.
- Option to save images with lossless compression.
- Preserve original ComfyUI’s workflow.
- Preserve original image datetime attributes.
- Option to delete original PNG images after conversion (send to Recycle bin).

## Requirements

- Python 3.x
- Pillow
- send2trash

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/fernicar/png2webp-for-ComfyUI.git
    cd png2webp-for-ComfyUI
    ```

2. Install the required packages:
    ```sh
    pip install Pillow send2trash
    ```

## Usage

To convert PNG images to WebP format, run the script with the following command:

```sh
python convert.py --path /path/to/png/images --delete True
```

### Arguments

- `--path`: Path to the directory containing PNG images (required).
- `--delete`: (Optional) Send the PNG images to the recycle bin after converting to WebP. Defaults to `False`.

## Example

```sh
python convert.py --path ./images --delete True
```

This command will convert all PNG images in the `./images` directory to WebP format and send the original PNG images to the recycle bin.

## Code Overview

### `saveWebp` Function

This function loads a PNG image, extracts its metadata, and saves it as a WebP image with the same filename and metadata.

### `convert_png_to_webp` Function

This function converts a PNG image to WebP format, optionally preserving the original image's datetime attributes and sending the original PNG image to the recycle bin.

### `main` Function

This function parses command-line arguments and processes all PNG images in the specified directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
