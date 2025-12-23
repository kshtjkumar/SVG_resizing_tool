# Input Folder

Place your SVG files in this folder to process them with the SVG Resizing Tool.

## Instructions

1. Copy or move your SVG files into this `input/` directory
2. Run `./process.sh` from the repository root
3. Find your processed files in the `output/` folder

## Supported File Types

- `.svg` - Scalable Vector Graphics files

## Example Files

You can use SVG files exported from:
- Matplotlib (Python)
- MATLAB
- Inkscape
- Adobe Illustrator
- Any other tool that creates valid SVG files

## Notes

- The script will process all `.svg` files in this directory
- Original files are not modified - processed versions are saved to `output/`
- You can customize processing options when running `process.sh` (see `./process.sh --help`)
