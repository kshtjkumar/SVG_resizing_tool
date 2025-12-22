#!/usr/bin/env python3
"""
SVG Panel Framing Tool
Fits SVG panels into publisher-specified dimensions with optional scaling.
"""

import argparse
import xml.etree.ElementTree as ET
import sys


# Publisher dimensions in millimeters
PUBLISHER_SIZES = {
    'ieee-access': {'single': (88.9, None), 'double': (183.0, None), 'full': (183.0, None)},
    'ieee-trans': {'single': (88.9, None), 'double': (183.0, None), 'full': (183.0, None)},
    'ieee-proc': {'single': (88.9, None), 'double': (183.0, None), 'full': (183.0, None)},
    'nature': {'single': (89.0, None), 'double': (183.0, None), 'full': (247.0, None)},
}


def mm_to_px(mm):
    """Convert millimeters to pixels at 90 DPI."""
    return mm * 90.0 / 25.4


def px_to_mm(px):
    """Convert pixels to millimeters at 90 DPI."""
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
    
    # Fallback to viewBox
    if width is None or height is None:
        viewbox = svg_root.get('viewBox', '')
        if viewbox:
            parts = viewbox.split()
            if len(parts) == 4:
                width = float(parts[2])
                height = float(parts[3])
    
    return width, height


def frame_panel(input_path, output_path, args):
    """Frame a panel to fit publisher specifications."""
    try:
        tree = ET.parse(input_path)
        root = tree.getroot()
        
        # Get current dimensions
        current_width, current_height = parse_svg_dimensions(root)
        
        if current_width is None or current_height is None:
            print(f"Error: Could not determine dimensions of {input_path}", file=sys.stderr)
            return False
        
        # Get target dimensions
        if args.outer_publisher and args.outer_layout:
            publisher = args.outer_publisher
            layout = args.outer_layout
            
            if publisher in PUBLISHER_SIZES and layout in PUBLISHER_SIZES[publisher]:
                target_width_mm, target_height_mm = PUBLISHER_SIZES[publisher][layout]
                
                if target_width_mm:
                    target_width = mm_to_px(target_width_mm)
                    
                    # Calculate scale factor
                    scale = target_width / current_width
                    
                    # Apply scaling
                    new_width = target_width
                    new_height = current_height * scale
                    
                    # Update SVG dimensions
                    root.set('width', str(new_width))
                    root.set('height', str(new_height))
                    root.set('viewBox', f'0 0 {new_width} {new_height}')
                    
                    # Scale content if needed
                    if abs(scale - 1.0) > 0.01:
                        # Wrap existing content in a scaled group
                        content_group = ET.Element('g', {
                            'transform': f'scale({scale})'
                        })
                        
                        # Move all children to the new group
                        for child in list(root):
                            root.remove(child)
                            content_group.append(child)
                        
                        root.append(content_group)
                    
                    print(f"Scaled from {px_to_mm(current_width):.1f}mm x {px_to_mm(current_height):.1f}mm "
                          f"to {px_to_mm(new_width):.1f}mm x {px_to_mm(new_height):.1f}mm")
        
        # Write output
        ET.indent(tree, space='  ')
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"Framed panel written to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error framing panel: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Fit SVG panel to publisher specifications'
    )
    parser.add_argument('input', help='Input SVG file')
    parser.add_argument('--output', '-o', required=True, help='Output SVG file')
    parser.add_argument('--outer-publisher', 
                        choices=['ieee-access', 'ieee-trans', 'ieee-proc', 'nature'],
                        required=True, help='Target publisher')
    parser.add_argument('--outer-layout', 
                        choices=['single', 'double', 'full'],
                        required=True, help='Column layout')
    
    args = parser.parse_args()
    
    success = frame_panel(args.input, args.output, args)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
