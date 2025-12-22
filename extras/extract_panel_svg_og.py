#!/usr/bin/env python3
"""
SVG Panel Extraction Tool
Extracts individual panels from composite matplotlib SVG figures.
"""

import argparse
import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path


def parse_transform_matrix(transform_str):
    """Parse SVG transform matrix into components."""
    if not transform_str:
        return {'a': 1, 'b': 0, 'c': 0, 'd': 1, 'e': 0, 'f': 0}
    
    # Match matrix(a, b, c, d, e, f)
    matrix_match = re.search(r'matrix\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', transform_str)
    if matrix_match:
        return {
            'a': float(matrix_match.group(1)),
            'b': float(matrix_match.group(2)),
            'c': float(matrix_match.group(3)),
            'd': float(matrix_match.group(4)),
            'e': float(matrix_match.group(5)),
            'f': float(matrix_match.group(6))
        }
    
    # Match translate(x, y)
    translate_match = re.search(r'translate\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', transform_str)
    if translate_match:
        return {
            'a': 1, 'b': 0, 'c': 0, 'd': 1,
            'e': float(translate_match.group(1)),
            'f': float(translate_match.group(2))
        }
    
    # Match scale(sx, sy)
    scale_match = re.search(r'scale\s*\(\s*([-\d.]+)(?:\s*,\s*([-\d.]+))?\s*\)', transform_str)
    if scale_match:
        sx = float(scale_match.group(1))
        sy = float(scale_match.group(2)) if scale_match.group(2) else sx
        return {'a': sx, 'b': 0, 'c': 0, 'd': sy, 'e': 0, 'f': 0}
    
    return {'a': 1, 'b': 0, 'c': 0, 'd': 1, 'e': 0, 'f': 0}


def get_element_bounds(element, parent_transform=None):
    """Calculate bounding box of an element considering transforms."""
    if parent_transform is None:
        parent_transform = {'a': 1, 'b': 0, 'c': 0, 'd': 1, 'e': 0, 'f': 0}
    
    # Parse this element's transform
    transform_str = element.get('transform', '')
    local_transform = parse_transform_matrix(transform_str)
    
    # Combine with parent transform (simplified - assumes no skew)
    combined_transform = {
        'a': parent_transform['a'] * local_transform['a'],
        'b': parent_transform['b'] + local_transform['b'],
        'c': parent_transform['c'] + local_transform['c'],
        'd': parent_transform['d'] * local_transform['d'],
        'e': parent_transform['e'] + local_transform['e'],
        'f': parent_transform['f'] + local_transform['f']
    }
    
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    # Check element type and extract bounds
    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
    
    if tag == 'rect':
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))
        
        # Apply transform
        x_transformed = combined_transform['a'] * x + combined_transform['e']
        y_transformed = combined_transform['d'] * y + combined_transform['f']
        width_transformed = combined_transform['a'] * width
        height_transformed = combined_transform['d'] * height
        
        min_x = x_transformed
        min_y = y_transformed
        max_x = x_transformed + width_transformed
        max_y = y_transformed + height_transformed
    
    elif tag == 'line':
        x1 = float(element.get('x1', 0))
        y1 = float(element.get('y1', 0))
        x2 = float(element.get('x2', 0))
        y2 = float(element.get('y2', 0))
        
        x1_t = combined_transform['a'] * x1 + combined_transform['e']
        y1_t = combined_transform['d'] * y1 + combined_transform['f']
        x2_t = combined_transform['a'] * x2 + combined_transform['e']
        y2_t = combined_transform['d'] * y2 + combined_transform['f']
        
        min_x = min(x1_t, x2_t)
        min_y = min(y1_t, y2_t)
        max_x = max(x1_t, x2_t)
        max_y = max(y1_t, y2_t)
    
    elif tag == 'text':
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        
        x_t = combined_transform['a'] * x + combined_transform['e']
        y_t = combined_transform['d'] * y + combined_transform['f']
        
        min_x = x_t
        min_y = y_t - 10  # Approximate text height
        max_x = x_t + 50  # Approximate text width
        max_y = y_t
    
    # Process children recursively
    for child in element:
        child_bounds = get_element_bounds(child, combined_transform)
        if child_bounds[0] != float('inf'):
            min_x = min(min_x, child_bounds[0])
            min_y = min(min_y, child_bounds[1])
            max_x = max(max_x, child_bounds[2])
            max_y = max(max_y, child_bounds[3])
    
    return min_x, min_y, max_x, max_y


def find_panels(svg_root):
    """Find all labeled panels in an SVG (e.g., groups with panel labels)."""
    panels = {}
    
    def search_for_panels(element, depth=0):
        # Look for groups that might be panels
        element_id = element.get('id', '')
        
        # Check if this looks like a panel group
        if element.tag.endswith('g'):
            # Look for text labels in this group
            for child in element:
                if child.tag.endswith('text'):
                    text = (child.text or '').strip()
                    # Check if it's a single letter label
                    if len(text) == 1 and text.isalpha():
                        panels[text.lower()] = element
                        return
        
        # Recursively search children
        for child in element:
            search_for_panels(child, depth + 1)
    
    search_for_panels(svg_root)
    return panels


def list_panels(svg_path):
    """List all available panels in an SVG file."""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        panels = find_panels(root)
        
        if panels:
            print(f"Found {len(panels)} panels:")
            for label in sorted(panels.keys()):
                print(f"  - {label}")
        else:
            print("No labeled panels found in the SVG")
            print("Tip: This tool looks for single-letter text labels (a, b, c, etc.)")
        
        return True
        
    except Exception as e:
        print(f"Error reading SVG: {e}", file=sys.stderr)
        return False


def extract_panel(svg_path, panel_label, output_path):
    """Extract a specific panel from a composite SVG."""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        panels = find_panels(root)
        
        if panel_label not in panels:
            print(f"Panel '{panel_label}' not found", file=sys.stderr)
            print(f"Available panels: {', '.join(sorted(panels.keys()))}", file=sys.stderr)
            return False
        
        panel_group = panels[panel_label]
        
        # Calculate bounds of the panel
        bounds = get_element_bounds(panel_group)
        
        if bounds[0] == float('inf'):
            print(f"Could not determine bounds for panel '{panel_label}'", file=sys.stderr)
            return False
        
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        
        # Create new SVG with just this panel
        svg_ns = "http://www.w3.org/2000/svg"
        ET.register_namespace('', svg_ns)
        
        new_root = ET.Element('svg', {
            'xmlns': svg_ns,
            'width': str(width),
            'height': str(height),
            'viewBox': f'0 0 {width} {height}'
        })
        
        # Create a group with translation to origin
        content_group = ET.SubElement(new_root, 'g', {
            'transform': f'translate({-min_x}, {-min_y})'
        })
        
        # Copy panel content
        for child in panel_group:
            content_group.append(child)
        
        # Write output
        new_tree = ET.ElementTree(new_root)
        ET.indent(new_tree, space='  ')
        new_tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        print(f"Extracted panel '{panel_label}' to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error extracting panel: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Extract individual panels from composite SVG figures'
    )
    parser.add_argument('input', help='Input composite SVG file')
    parser.add_argument('--list', action='store_true', help='List available panels')
    parser.add_argument('--panel', help='Panel label to extract (e.g., a, b, c)')
    parser.add_argument('--output', '-o', help='Output SVG file')
    
    args = parser.parse_args()
    
    if args.list:
        success = list_panels(args.input)
    elif args.panel and args.output:
        success = extract_panel(args.input, args.panel.lower(), args.output)
    else:
        parser.print_help()
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
