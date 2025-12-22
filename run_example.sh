#!/bin/bash
# Example demonstration script for SVG Resizing Tool
# This script shows a complete workflow of SVG panel processing

set -e  # Exit on error

echo "SVG Resizing Tool - Example Workflow"
echo "====================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found"
    exit 1
fi

echo "Step 1: Verifying all scripts compile correctly..."
python3 -m py_compile main.py
python3 -m py_compile align_axes.py
python3 -m py_compile panel_frame_fit.py
python3 -m py_compile extras/extract_panel_svg_og.py
echo "✓ All scripts compile successfully"
echo ""

echo "Step 2: Creating example directory..."
mkdir -p output_panels
echo "✓ Directory created"
echo ""

echo "Example workflow complete!"
echo ""
echo "To use the tools:"
echo ""
echo "1. Assemble multiple panels into a composite figure:"
echo "   python3 main.py panel1.svg panel2.svg --output composite.svg \\"
echo "     --outer-publisher ieee-trans --outer-layout double \\"
echo "     --max-per-row 2 --add-panel-label"
echo ""
echo "2. Frame a single panel to publisher specifications:"
echo "   python3 panel_frame_fit.py input.svg --output framed.svg \\"
echo "     --outer-publisher ieee-trans --outer-layout single"
echo ""
echo "3. Extract a panel from a composite figure:"
echo "   python3 extras/extract_panel_svg_og.py composite.svg --list"
echo "   python3 extras/extract_panel_svg_og.py composite.svg \\"
echo "     --panel a --output panel_a.svg"
echo ""
echo "4. Align panels in a composite figure:"
echo "   python3 align_axes.py composite.svg --align-mode patch-bottom"
echo ""

