#!/usr/bin/env python3
"""
SVG Panel Assembly Tool
Combines multiple SVG panels into publisher-ready figures with automatic scaling and alignment.
"""

import argparse
import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path


# Publisher dimensions in millimeters (width, height for single column)
PUBLISHER_SIZES = {
    'ieee-access': {'single': (88.9, None), 'double': (183.0, None), 'full': (183.0, None)},
    'ieee-trans': {'single': (88.9, None), 'double': (183.0, None), 'full': (183.0, None)},
    'ieee-proc': {'single': (88.9, None), 'double': (183.0, None), 'full': (183.0, None)},
    'nature': {'single': (89.0, None), 'double': (183.0, None), 'full': (247.0, None)},
}


def mm_to_px(mm):
    """Convert millimeters to pixels (SVG units) at 90 DPI."""
    return mm * 90.0 / 25.4


def px_to_mm(px):
    """Convert pixels (SVG units) to millimeters at 90 DPI."""
    return px * 25.4 / 90.0


def parse_svg_dimensions(svg_root):
    """Extract width and height from SVG root element."""
    width_str = svg_root.get('width', '').replace('pt', '').replace('px', '')
    height_str = svg_root.get('height', '').replace('pt', '').replace('px', '')
    
    try:
        width = float(width_str) if width_str else None
        height = float(height_str) if height_str else None
    except ValueError:
        width, height = None, None
    
    # Fallback to viewBox if width/height not found
    if width is None or height is None:
        viewbox = svg_root.get('viewBox', '')
        if viewbox:
            parts = viewbox.split()
            if len(parts) == 4:
                width = float(parts[2])
                height = float(parts[3])
    
    return width, height


def create_composite_svg(panels, output_path, args):
    """Create a composite SVG from multiple panel SVGs."""
    # Load all panel SVGs
    panel_trees = []
    for panel_file in panels:
        try:
            tree = ET.parse(panel_file)
            panel_trees.append((panel_file, tree))
        except Exception as e:
            print(f"Error loading {panel_file}: {e}", file=sys.stderr)
            continue
    
    if not panel_trees:
        print("No valid panels to process", file=sys.stderr)
        return False
    
    # Calculate layout
    num_panels = len(panel_trees)
    max_per_row = args.max_per_row
    num_rows = (num_panels + max_per_row - 1) // max_per_row
    num_cols = min(num_panels, max_per_row)
    
    # Get panel dimensions
    panel_dims = []
    for _, tree in panel_trees:
        width, height = parse_svg_dimensions(tree.getroot())
        panel_dims.append((width or 0, height or 0))
    
    # Calculate max dimensions per row/column
    max_width = max(w for w, h in panel_dims) if panel_dims else 0
    max_height = max(h for w, h in panel_dims) if panel_dims else 0
    
    # Apply publisher sizing if specified
    if args.outer_publisher and args.outer_layout:
        publisher = args.outer_publisher
        layout = args.outer_layout
        if publisher in PUBLISHER_SIZES and layout in PUBLISHER_SIZES[publisher]:
            target_width_mm, _ = PUBLISHER_SIZES[publisher][layout]
            if target_width_mm:
                target_width_px = mm_to_px(target_width_mm)
                # Calculate scale factor
                total_content_width = num_cols * max_width + (num_cols - 1) * args.col_gap
                scale = target_width_px / total_content_width if total_content_width > 0 else 1.0
                max_width *= scale
                max_height *= scale
    
    # Calculate total dimensions
    total_width = num_cols * max_width + (num_cols - 1) * args.col_gap + 2 * args.outer_pad
    total_height = num_rows * max_height + (num_rows - 1) * args.row_gap + 2 * args.outer_pad
    
    # Create root SVG
    svg_ns = "http://www.w3.org/2000/svg"
    ET.register_namespace('', svg_ns)
    root = ET.Element('{%s}svg' % svg_ns, {
        'width': f'{total_width}',
        'height': f'{total_height}',
        'viewBox': f'0 0 {total_width} {total_height}'
    })
    
    # Add panels
    for idx, (panel_file, tree) in enumerate(panel_trees):
        row = idx // max_per_row
        col = idx % max_per_row
        
        x = args.outer_pad + col * (max_width + args.col_gap)
        y = args.outer_pad + row * (max_height + args.row_gap)
        
        # Create group for panel
        group = ET.SubElement(root, 'g', {
            'transform': f'translate({x}, {y})'
        })
        
        # Copy panel content
        panel_root = tree.getroot()
        for child in panel_root:
            group.append(child)
        
        # Add panel label if requested
        if args.add_panel_label:
            label_char = chr(ord(args.panel_label_first) + idx)
            label = ET.SubElement(group, 'text', {
                'x': '5',
                'y': '15',
                'font-size': str(args.panel_label_font_size),
                'font-weight': 'bold',
                'font-family': 'Arial, sans-serif'
            })
            label.text = label_char
    
    # Write output
    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"Composite SVG written to: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Assemble multiple SVG panels into a composite figure'
    )
    parser.add_argument('panels', nargs='+', help='Input SVG panel files')
    parser.add_argument('--output', '-o', required=True, help='Output SVG file')
    
    # Publisher options
    parser.add_argument('--outer-publisher', choices=['ieee-access', 'ieee-trans', 'ieee-proc', 'nature'],
                        help='Target publisher')
    parser.add_argument('--outer-layout', choices=['single', 'double', 'full'],
                        help='Column layout')
    
    # Layout options
    parser.add_argument('--max-per-row', type=int, default=2, help='Maximum panels per row')
    parser.add_argument('--col-gap', type=float, default=10.0, help='Horizontal gap between panels (px)')
    parser.add_argument('--row-gap', type=float, default=10.0, help='Vertical gap between rows (px)')
    parser.add_argument('--outer-pad', type=float, default=10.0, help='Outer frame padding (px)')
    
    # Label options
    parser.add_argument('--add-panel-label', action='store_true', help='Add panel labels')
    parser.add_argument('--panel-label-first', default='a', help='First panel label character')
    parser.add_argument('--panel-label-font-size', type=int, default=12, help='Label font size')
    
    # Alignment options (for future use with align_axes.py)
    parser.add_argument('--align', action='store_true', help='Enable post-processing alignment')
    parser.add_argument('--align-mode', choices=['xlabel', 'patch-bottom'], default='xlabel',
                        help='Alignment target')
    parser.add_argument('--align-xspine-equalize', action='store_true', help='Equalize x-axis spine lengths')
    parser.add_argument('--align-yspine-equalize', action='store_true', help='Equalize y-axis spine lengths')
    parser.add_argument('--auto-match-scale', action='store_true', help='Normalize scales if inputs differ')
    
    args = parser.parse_args()
    
    # Create composite SVG
    success = create_composite_svg(args.panels, args.output, args)
    
    # Apply alignment if requested
    if success and args.align:
        try:
            import align_axes
            print("Applying alignment...")
            align_axes.align_svg_panels(args.output, args)
        except ImportError:
            print("Warning: align_axes module not found, skipping alignment", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Alignment failed: {e}", file=sys.stderr)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

