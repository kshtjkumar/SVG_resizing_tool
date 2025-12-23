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


def parse_transform(transform_str):
    """
    Parse SVG transform attribute and return (tx, ty, sx, sy) tuple.
    Supports: translate(x[, y]), scale(sx[, sy]), matrix(a, b, c, d, e, f)
    """
    if not transform_str:
        return (0, 0, 1, 1)
    
    tx, ty, sx, sy = 0, 0, 1, 1
    
    # Parse translate
    translate_match = re.search(r'translate\s*\(\s*([^,\s]+)(?:\s*,\s*([^)]+))?\s*\)', transform_str)
    if translate_match:
        tx = float(translate_match.group(1))
        ty = float(translate_match.group(2)) if translate_match.group(2) else 0
    
    # Parse scale
    scale_match = re.search(r'scale\s*\(\s*([^,\s]+)(?:\s*,\s*([^)]+))?\s*\)', transform_str)
    if scale_match:
        sx = float(scale_match.group(1))
        sy = float(scale_match.group(2)) if scale_match.group(2) else sx
    
    # Parse matrix (simplified - only handles translation and scale in matrix form)
    matrix_match = re.search(r'matrix\s*\(\s*([^,\s]+)\s*,\s*([^,\s]+)\s*,\s*([^,\s]+)\s*,\s*([^,\s]+)\s*,\s*([^,\s]+)\s*,\s*([^)]+)\s*\)', transform_str)
    if matrix_match:
        a, b, c, d, e, f = [float(x) for x in matrix_match.groups()]
        # For matrices without rotation/skew: a=sx, d=sy, e=tx, f=ty
        sx = a
        sy = d
        tx = e
        ty = f
    
    return (tx, ty, sx, sy)


def get_path_bounds(path_data):
    """
    Parse SVG path 'd' attribute and return bounding box.
    Returns (min_x, min_y, max_x, max_y) or None if no valid coordinates found.
    """
    if not path_data:
        return None
    
    # Extract all numeric coordinates from path data
    # Match numbers (including negative and decimal)
    coords = re.findall(r'-?\d+\.?\d*', path_data)
    if not coords:
        return None
    
    coords = [float(c) for c in coords]
    
    # Split into x,y pairs
    x_coords = coords[0::2]
    y_coords = coords[1::2]
    
    if not x_coords or not y_coords:
        return None
    
    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))


def get_content_bounds(element, transform=(0, 0, 1, 1)):
    """
    Recursively calculate the actual content bounding box of SVG elements.
    Returns (min_x, min_y, max_x, max_y) of visible content.
    
    Handles: rect, line, circle, ellipse, path, polygon, polyline, text, g (groups)
    Accounts for transforms: translate, scale, matrix
    """
    tx, ty, sx, sy = transform
    
    # Parse element's own transform and combine with parent
    elem_transform_str = element.get('transform', '')
    if elem_transform_str:
        etx, ety, esx, esy = parse_transform(elem_transform_str)
        tx = tx + etx * sx
        ty = ty + ety * sy
        sx = sx * esx
        sy = sy * esy
    
    # Get element tag without namespace
    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
    
    bounds = None
    
    # Handle different element types
    if tag == 'rect':
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))
        bounds = (x, y, x + width, y + height)
    
    elif tag == 'circle':
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        r = float(element.get('r', 0))
        bounds = (cx - r, cy - r, cx + r, cy + r)
    
    elif tag == 'ellipse':
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        rx = float(element.get('rx', 0))
        ry = float(element.get('ry', 0))
        bounds = (cx - rx, cy - ry, cx + rx, cy + ry)
    
    elif tag == 'line':
        x1 = float(element.get('x1', 0))
        y1 = float(element.get('y1', 0))
        x2 = float(element.get('x2', 0))
        y2 = float(element.get('y2', 0))
        bounds = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    
    elif tag == 'polyline' or tag == 'polygon':
        points_str = element.get('points', '')
        if points_str:
            coords = re.findall(r'-?\d+\.?\d*', points_str)
            if coords:
                coords = [float(c) for c in coords]
                x_coords = coords[0::2]
                y_coords = coords[1::2]
                if x_coords and y_coords:
                    bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
    
    elif tag == 'path':
        d = element.get('d', '')
        bounds = get_path_bounds(d)
    
    elif tag == 'text':
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        # Rough estimate for text bounds (actual rendering varies by font)
        bounds = (x, y - 10, x + 50, y + 5)
    
    # Apply transform to bounds
    if bounds:
        min_x, min_y, max_x, max_y = bounds
        min_x = min_x * sx + tx
        min_y = min_y * sy + ty
        max_x = max_x * sx + tx
        max_y = max_y * sy + ty
        bounds = (min_x, min_y, max_x, max_y)
    
    # Process child elements recursively
    for child in element:
        child_bounds = get_content_bounds(child, (tx, ty, sx, sy))
        if child_bounds:
            if bounds:
                # Merge bounds
                bounds = (
                    min(bounds[0], child_bounds[0]),
                    min(bounds[1], child_bounds[1]),
                    max(bounds[2], child_bounds[2]),
                    max(bounds[3], child_bounds[3])
                )
            else:
                bounds = child_bounds
    
    return bounds


def crop_svg_to_content(svg_root):
    """
    Crop an SVG to its actual content bounds, removing excess whitespace.
    Returns (cropped_root, width, height) with content starting at (0,0).
    """
    # Get content bounds
    bounds = get_content_bounds(svg_root)
    
    if not bounds:
        # No content found, return original
        width, height = parse_svg_dimensions(svg_root)
        return svg_root, width or 0, height or 0
    
    min_x, min_y, max_x, max_y = bounds
    content_width = max_x - min_x
    content_height = max_y - min_y
    
    # Create new root with adjusted viewBox
    svg_ns = "http://www.w3.org/2000/svg"
    new_root = ET.Element('{%s}svg' % svg_ns, {
        'width': f'{content_width}',
        'height': f'{content_height}',
        'viewBox': f'{min_x} {min_y} {content_width} {content_height}'
    })
    
    # Copy attributes except width, height, viewBox
    for attr, value in svg_root.attrib.items():
        if attr not in ['width', 'height', 'viewBox']:
            new_root.set(attr, value)
    
    # Copy all child elements
    for child in svg_root:
        new_root.append(child)
    
    return new_root, content_width, content_height


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
    
    # Crop panels if requested
    if hasattr(args, 'crop') and args.crop:
        cropped_trees = []
        for panel_file, tree in panel_trees:
            cropped_root, width, height = crop_svg_to_content(tree.getroot())
            # Create new tree with cropped root
            new_tree = ET.ElementTree(cropped_root)
            cropped_trees.append((panel_file, new_tree))
        panel_trees = cropped_trees
    
    # Get panel dimensions
    panel_dims = []
    for _, tree in panel_trees:
        width, height = parse_svg_dimensions(tree.getroot())
        panel_dims.append((width or 0, height or 0))
    
    # Calculate max dimensions per row/column
    max_width = max(w for w, h in panel_dims) if panel_dims else 0
    max_height = max(h for w, h in panel_dims) if panel_dims else 0
    
    # Calculate gaps based on options
    col_gap = args.col_gap
    row_gap = args.row_gap
    
    # Apply --tight option (override gaps to 0)
    if hasattr(args, 'tight') and args.tight:
        col_gap = 0
        row_gap = 0
    # Apply --gap-ratio option (proportional gaps)
    elif hasattr(args, 'gap_ratio') and args.gap_ratio is not None:
        avg_width = sum(w for w, h in panel_dims) / len(panel_dims) if panel_dims else 0
        avg_height = sum(h for w, h in panel_dims) / len(panel_dims) if panel_dims else 0
        col_gap = avg_width * args.gap_ratio
        row_gap = avg_height * args.gap_ratio
    
    # Apply publisher sizing if specified
    if args.outer_publisher and args.outer_layout:
        publisher = args.outer_publisher
        layout = args.outer_layout
        if publisher in PUBLISHER_SIZES and layout in PUBLISHER_SIZES[publisher]:
            target_width_mm, _ = PUBLISHER_SIZES[publisher][layout]
            if target_width_mm:
                target_width_px = mm_to_px(target_width_mm)
                # Calculate scale factor
                total_content_width = num_cols * max_width + (num_cols - 1) * col_gap
                scale = target_width_px / total_content_width if total_content_width > 0 else 1.0
                max_width *= scale
                max_height *= scale
    
    # Calculate total dimensions
    total_width = num_cols * max_width + (num_cols - 1) * col_gap + 2 * args.outer_pad
    total_height = num_rows * max_height + (num_rows - 1) * row_gap + 2 * args.outer_pad
    
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
        
        x = args.outer_pad + col * (max_width + col_gap)
        y = args.outer_pad + row * (max_height + row_gap)
        
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
    
    # Content-aware cropping options
    parser.add_argument('--crop', action='store_true', help='Auto-crop panels to content bounds')
    parser.add_argument('--tight', action='store_true', help='Zero gaps between panels')
    parser.add_argument('--gap-ratio', type=float, help='Gap as ratio of panel size (e.g., 0.02 = 2%%)')
    
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
