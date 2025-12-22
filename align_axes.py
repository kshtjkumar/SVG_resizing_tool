#!/usr/bin/env python3
"""
SVG Axes Alignment Tool
Aligns matplotlib-generated SVG panels by axis positions and spine lengths.
"""

import xml.etree.ElementTree as ET
import re
import sys


def parse_transform(transform_str):
    """Parse SVG transform string into translation values."""
    if not transform_str:
        return 0, 0
    
    # Match translate(x, y) or translate(x,y)
    match = re.search(r'translate\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', transform_str)
    if match:
        return float(match.group(1)), float(match.group(2))
    
    return 0, 0


def get_element_bounds(element, current_transform=(0, 0)):
    """Recursively calculate bounding box of an SVG element."""
    tx, ty = current_transform
    
    # Check for transform on this element
    transform = element.get('transform', '')
    if transform:
        dx, dy = parse_transform(transform)
        tx += dx
        ty += dy
    
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    # Check element attributes for position
    if element.tag.endswith('rect'):
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))
        min_x = min(min_x, tx + x)
        min_y = min(min_y, ty + y)
        max_x = max(max_x, tx + x + width)
        max_y = max(max_y, ty + y + height)
    elif element.tag.endswith('line'):
        x1 = float(element.get('x1', 0))
        y1 = float(element.get('y1', 0))
        x2 = float(element.get('x2', 0))
        y2 = float(element.get('y2', 0))
        min_x = min(min_x, tx + x1, tx + x2)
        min_y = min(min_y, ty + y1, ty + y2)
        max_x = max(max_x, tx + x1, tx + x2)
        max_y = max(max_y, ty + y1, ty + y2)
    elif element.tag.endswith('text'):
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        min_x = min(min_x, tx + x)
        min_y = min(min_y, ty + y)
        max_x = max(max_x, tx + x)
        max_y = max(max_y, ty + y)
    
    # Recursively process children
    for child in element:
        child_min_x, child_min_y, child_max_x, child_max_y = get_element_bounds(child, (tx, ty))
        if child_min_x != float('inf'):
            min_x = min(min_x, child_min_x)
            min_y = min(min_y, child_min_y)
            max_x = max(max_x, child_max_x)
            max_y = max(max_y, child_max_y)
    
    return min_x, min_y, max_x, max_y


def find_axes_groups(root):
    """Find all matplotlib axes groups in SVG."""
    axes_groups = []
    
    def search_element(element):
        # Check if this is an axes group (matplotlib uses specific IDs)
        element_id = element.get('id', '')
        if 'axes' in element_id.lower() or 'axis' in element_id.lower():
            axes_groups.append(element)
        
        # Recursively search children
        for child in element:
            search_element(child)
    
    search_element(root)
    return axes_groups


def align_svg_panels(svg_path, args):
    """Align panels in an SVG file according to specified parameters."""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Find all axes groups
        axes_groups = find_axes_groups(root)
        
        if len(axes_groups) < 2:
            print("Not enough axes groups found for alignment", file=sys.stderr)
            return False
        
        # Get bounds for each axes group
        axes_bounds = []
        for axes_group in axes_groups:
            bounds = get_element_bounds(axes_group)
            axes_bounds.append(bounds)
        
        # Alignment based on mode
        if args.align_mode == 'patch-bottom':
            # Align by bottom edge of plot area
            min_bottom = min(bounds[3] for bounds in axes_bounds)
            
            for axes_group, bounds in zip(axes_groups, axes_bounds):
                current_bottom = bounds[3]
                offset = current_bottom - min_bottom
                
                if abs(offset) > 0.1:  # Only adjust if significant difference
                    current_transform = axes_group.get('transform', '')
                    tx, ty = parse_transform(current_transform)
                    new_transform = f'translate({tx}, {ty - offset})'
                    axes_group.set('transform', new_transform)
        
        elif args.align_mode == 'xlabel':
            # Align by x-axis label baseline
            # This is a simplified version - full implementation would find text elements
            print("xlabel alignment mode - simplified implementation", file=sys.stderr)
        
        # Equalize spine lengths if requested
        if args.align_xspine_equalize or args.align_yspine_equalize:
            print("Spine equalization requested but not yet implemented", file=sys.stderr)
        
        # Write back to file
        ET.indent(tree, space='  ')
        tree.write(svg_path, encoding='utf-8', xml_declaration=True)
        print(f"Alignment applied to: {svg_path}")
        return True
        
    except Exception as e:
        print(f"Error during alignment: {e}", file=sys.stderr)
        return False


def main():
    """Standalone alignment tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Align SVG panels by axes')
    parser.add_argument('input', help='Input SVG file')
    parser.add_argument('--align-mode', choices=['xlabel', 'patch-bottom'], 
                        default='patch-bottom', help='Alignment target')
    parser.add_argument('--align-xspine-equalize', action='store_true',
                        help='Equalize x-axis spine lengths')
    parser.add_argument('--align-yspine-equalize', action='store_true',
                        help='Equalize y-axis spine lengths')
    
    args = parser.parse_args()
    
    success = align_svg_panels(args.input, args)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
