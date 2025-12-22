# SVG Resizing Tool

A comprehensive Python toolkit for extracting, aligning, and compositing Matplotlib SVG panels into publisher-ready figures with automatic scaling and alignment.

## Features

- 🎨 **Multi-panel SVG extraction and assembly** - Combine multiple Matplotlib figures into publication mosaics
- 📏 **Automatic axis alignment** - Align panels by x-axis label baseline or patch bottom
- 📐 **Spine equalization** - Normalize x/y-axis spine lengths across panels
- 📰 **Publisher presets** - IEEE Access, IEEE Trans, IEEE Proc, Nature journal sizing
- 🔲 **Grid layout** - Configurable rows, columns, gaps, and padding
- 🔤 **Panel labeling** - Automatic sequential labels (a, b, c, ...)
- 🎯 **Content-aware bounding** - Smart detection of axes, figure, and content boundaries

## Requirements

- Python 3.7+ (standard library only, no external dependencies)

## Installation

```bash
git clone https://github.com/kshtjkumar/SVG_resizing_tool.git
cd SVG_resizing_tool
chmod +x run_example.sh
```

## Quick Start

```bash
# Assemble panels into IEEE double-column figure
python3 main.py output_panels/panel_*.svg \
  --output final_figure.svg \
  --outer-publisher ieee-trans \
  --outer-layout double \
  --max-per-row 2 \
  --col-gap 0 \
  --row-gap 0 \
  --outer-pad 0 \
  --add-panel-label \
  --panel-label-first a \
  --panel-label-font-size 8 \
  --align \
  --auto-match-scale \
  --align-mode patch-bottom \
  --align-xspine-equalize \
  --align-yspine-equalize
```

## Usage

### Main Assembly Pipeline (`main.py`)

```bash
python3 main.py <file1.svg> <file2.svg> ... --output <output.svg> [options]
```

**Publisher Mode Options:**
- `--outer-publisher {ieee-access,ieee-trans,ieee-proc,nature}` - Target journal
- `--outer-layout {single,double,full}` - Column layout
- `--max-per-row N` - Panels per row (default: 2)
- `--col-gap MM` - Horizontal gap between panels
- `--row-gap MM` - Vertical gap between rows
- `--outer-pad MM` - Outer frame padding

**Alignment Options:**
- `--align` - Enable post-processing alignment
- `--align-mode {xlabel,patch-bottom}` - Alignment target
- `--align-xspine-equalize` - Match x-axis spine lengths
- `--align-yspine-equalize` - Match y-axis spine lengths
- `--auto-match-scale` - Normalize scales if inputs differ

**Labeling:**
- `--add-panel-label` - Add sequential labels
- `--panel-label-first a` - Starting label (default: 'a')
- `--panel-label-font-size PX` - Label font size

### Standalone Panel Framing (`panel_frame_fit.py`)

```bash
python3 panel_frame_fit.py panel.svg \
  --outer-publisher ieee-trans \
  --outer-layout single \
  --output framed.svg
```

### Panel Extraction (`extras/extract_panel_svg_og.py`)

```bash
# List available panels
python3 extras/extract_panel_svg_og.py mosaic.svg --list

# Extract by letter
python3 extras/extract_panel_svg_og.py mosaic.svg --panel a --output panel_a.svg
```

## Examples

See `run_example.sh` for a complete working example.

## Project Structure

- `main.py` - Main mosaic assembly script
- `align_axes.py` - Post-processing alignment utility
- `panel_frame_fit.py` - Single/multi-panel framing tool
- `extras/extract_panel_svg_og.py` - Panel extraction from composite SVGs
- `run_example.sh` - Demo script

## Known Limitations

- Transform matrices with nonzero skew (b or c terms) may produce approximate bounding boxes in extraction mode
- Alignment requires Matplotlib-style SVG structure (axes groups with matplotlib.axis_* children)

## Testing

Validate all scripts compile correctly:
```bash
python3 -m py_compile main.py align_axes.py panel_frame_fit.py extras/extract_panel_svg_og.py
```

## Contributing

Contributions welcome! Please ensure:
- All scripts pass `python3 -m py_compile <script.py>`
- Test end-to-end pipeline with sample SVGs
- Document any new publisher presets or alignment modes

## License

MIT License

## Citation

If you use this tool in your research, please cite:
```
@software{svg_resizing_tool,
  author = {Kumar, Kshtij},
  title = {SVG Resizing Tool: Publisher-ready Matplotlib figure composition},
  year = {2025},
  url = {https://github.com/kshtjkumar/SVG_resizing_tool}
}
```

## Acknowledgments

Designed for reproducible scientific figure preparation with precise control over panel layout and publisher specifications.