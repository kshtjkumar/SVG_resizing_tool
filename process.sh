#!/bin/bash
# SVG Processing Script
# Processes all SVG files in the input/ folder and saves them to output/

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PUBLISHER=""
LAYOUT=""
COMBINE=false
ADD_LABELS=false
MAX_PER_ROW=2
COL_GAP=10
ROW_GAP=10
OUTER_PAD=10
LABEL_FIRST="a"
LABEL_SIZE=12
ALIGN=false
ALIGN_MODE="xlabel"
ALIGN_XSPINE=false
ALIGN_YSPINE=false
AUTO_MATCH_SCALE=false

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INPUT_DIR="$SCRIPT_DIR/input"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Process all SVG files in the input/ folder and save them to output/.

OPTIONS:
    --publisher <format>       Publisher format (ieee-access, ieee-trans, ieee-proc, nature)
    --layout <type>            Layout type (single, double, full)
    --combine                  Combine all SVG files into one composite
    --labels                   Add panel labels (a, b, c...)
    --max-per-row <n>          Maximum panels per row (default: 2, only for --combine)
    --col-gap <px>             Column gap in pixels (default: 10, only for --combine)
    --row-gap <px>             Row gap in pixels (default: 10, only for --combine)
    --outer-pad <px>           Outer padding in pixels (default: 10)
    --label-first <char>       First label character (default: 'a')
    --label-size <px>          Label font size (default: 12)
    --align                    Enable post-processing alignment
    --align-mode <mode>        Alignment mode: xlabel or patch-bottom (default: xlabel)
    --align-xspine             Equalize x-axis spine lengths
    --align-yspine             Equalize y-axis spine lengths
    --auto-match-scale         Normalize scales if inputs differ
    --help, -h                 Show this help message

EXAMPLES:
    # Simple usage - process all SVGs individually
    $0

    # Process with publisher settings
    $0 --publisher ieee-trans --layout single

    # Combine all into one composite with labels
    $0 --combine --publisher nature --layout double --labels

    # Interactive mode (will prompt for options)
    $0 --interactive
    # or use short form:
    $0 -i

EOF
}

# Function to prompt for input
prompt_for_options() {
    print_info "Interactive mode - configure processing options"
    echo ""
    
    # Publisher format
    echo "Select publisher format:"
    echo "  1) ieee-access"
    echo "  2) ieee-trans"
    echo "  3) ieee-proc"
    echo "  4) nature"
    echo "  5) None (keep original size)"
    read -p "Enter choice [1-5]: " pub_choice
    case $pub_choice in
        1) PUBLISHER="ieee-access" ;;
        2) PUBLISHER="ieee-trans" ;;
        3) PUBLISHER="ieee-proc" ;;
        4) PUBLISHER="nature" ;;
        5) PUBLISHER="" ;;
        *) PUBLISHER="" ;;
    esac
    
    # Layout type (only if publisher is set)
    if [ -n "$PUBLISHER" ]; then
        echo ""
        echo "Select layout type:"
        echo "  1) single column"
        echo "  2) double column"
        echo "  3) full page"
        read -p "Enter choice [1-3]: " layout_choice
        case $layout_choice in
            1) LAYOUT="single" ;;
            2) LAYOUT="double" ;;
            3) LAYOUT="full" ;;
            *) LAYOUT="single" ;;
        esac
    fi
    
    # Combine files
    echo ""
    read -p "Combine all SVG files into one composite? [y/N]: " combine_choice
    if [[ "$combine_choice" =~ ^[Yy]$ ]]; then
        COMBINE=true
        
        # Ask for max per row
        read -p "Maximum panels per row [2]: " mpr
        MAX_PER_ROW=${mpr:-2}
    fi
    
    # Add labels
    echo ""
    read -p "Add panel labels (a, b, c...)? [y/N]: " label_choice
    if [[ "$label_choice" =~ ^[Yy]$ ]]; then
        ADD_LABELS=true
    fi
    
    echo ""
    print_success "Configuration complete!"
}

# Parse command line arguments
INTERACTIVE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --publisher)
            PUBLISHER="$2"
            shift 2
            ;;
        --layout)
            LAYOUT="$2"
            shift 2
            ;;
        --combine)
            COMBINE=true
            shift
            ;;
        --labels)
            ADD_LABELS=true
            shift
            ;;
        --max-per-row)
            MAX_PER_ROW="$2"
            shift 2
            ;;
        --col-gap)
            COL_GAP="$2"
            shift 2
            ;;
        --row-gap)
            ROW_GAP="$2"
            shift 2
            ;;
        --outer-pad)
            OUTER_PAD="$2"
            shift 2
            ;;
        --label-first)
            LABEL_FIRST="$2"
            shift 2
            ;;
        --label-size)
            LABEL_SIZE="$2"
            shift 2
            ;;
        --align)
            ALIGN=true
            shift
            ;;
        --align-mode)
            ALIGN_MODE="$2"
            shift 2
            ;;
        --align-xspine)
            ALIGN_XSPINE=true
            shift
            ;;
        --align-yspine)
            ALIGN_YSPINE=true
            shift
            ;;
        --auto-match-scale)
            AUTO_MATCH_SCALE=true
            shift
            ;;
        --interactive|-i)
            INTERACTIVE=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Print header
echo ""
echo "======================================"
echo "  SVG Resizing Tool - Batch Processor"
echo "======================================"
echo ""

# Check if Python 3 is available
print_info "Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not found"
    echo "  Please install Python 3.7 or higher"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_success "Python 3 found (version $PYTHON_VERSION)"

# Verify main.py exists
if [ ! -f "$SCRIPT_DIR/main.py" ]; then
    print_error "main.py not found in $SCRIPT_DIR"
    exit 1
fi

# Interactive mode
if [ "$INTERACTIVE" = true ]; then
    prompt_for_options
fi

# Check if input directory exists and has SVG files
if [ ! -d "$INPUT_DIR" ]; then
    print_error "Input directory not found: $INPUT_DIR"
    exit 1
fi

# Count SVG files
SVG_COUNT=$(find "$INPUT_DIR" -maxdepth 1 -name "*.svg" -type f | wc -l)
if [ "$SVG_COUNT" -eq 0 ]; then
    print_error "No SVG files found in $INPUT_DIR"
    echo ""
    echo "  Please add SVG files to the input/ folder and try again."
    echo "  See input/README.md for instructions."
    exit 1
fi

print_success "Found $SVG_COUNT SVG file(s) in input/"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Process files
echo ""
if [ "$COMBINE" = true ]; then
    # Combine mode - create one composite from all SVG files
    print_info "Processing mode: Combine all files into one composite"
    
    OUTPUT_FILE="$OUTPUT_DIR/combined_output.svg"
    
    # Build command as array (safer than eval)
    CMD_ARRAY=(python3 "$SCRIPT_DIR/main.py")
    for svg_file in "$INPUT_DIR"/*.svg; do
        if [ -f "$svg_file" ]; then
            CMD_ARRAY+=("$svg_file")
        fi
    done
    CMD_ARRAY+=(--output "$OUTPUT_FILE" --max-per-row "$MAX_PER_ROW" --col-gap "$COL_GAP" --row-gap "$ROW_GAP" --outer-pad "$OUTER_PAD")
    
    # Add optional arguments
    if [ -n "$PUBLISHER" ]; then
        CMD_ARRAY+=(--outer-publisher "$PUBLISHER")
    fi
    if [ -n "$LAYOUT" ]; then
        CMD_ARRAY+=(--outer-layout "$LAYOUT")
    fi
    if [ "$ADD_LABELS" = true ]; then
        CMD_ARRAY+=(--add-panel-label --panel-label-first "$LABEL_FIRST" --panel-label-font-size "$LABEL_SIZE")
    fi
    if [ "$ALIGN" = true ]; then
        CMD_ARRAY+=(--align --align-mode "$ALIGN_MODE")
        if [ "$ALIGN_XSPINE" = true ]; then
            CMD_ARRAY+=(--align-xspine-equalize)
        fi
        if [ "$ALIGN_YSPINE" = true ]; then
            CMD_ARRAY+=(--align-yspine-equalize)
        fi
        if [ "$AUTO_MATCH_SCALE" = true ]; then
            CMD_ARRAY+=(--auto-match-scale)
        fi
    fi
    
    print_info "Running: main.py with $SVG_COUNT input file(s)"
    
    # Execute command
    if "${CMD_ARRAY[@]}"; then
        print_success "Composite SVG created: $OUTPUT_FILE"
    else
        print_error "Failed to create composite SVG"
        exit 1
    fi
else
    # Individual mode - process each file separately
    print_info "Processing mode: Individual files"
    
    # Check if publisher and layout are set (required for panel_frame_fit.py)
    if [ -z "$PUBLISHER" ] || [ -z "$LAYOUT" ]; then
        print_warning "Publisher and layout not specified. Files will be copied to output/ without processing."
        print_info "Use --publisher and --layout options to resize files to publisher specifications."
        echo ""
        
        # Just copy files
        PROCESSED=0
        for svg_file in "$INPUT_DIR"/*.svg; do
            if [ ! -f "$svg_file" ]; then
                continue
            fi
            
            filename=$(basename "$svg_file")
            filename_noext="${filename%.svg}"
            output_file="$OUTPUT_DIR/${filename_noext}_processed.svg"
            
            print_info "Copying: $filename"
            cp "$svg_file" "$output_file"
            print_success "  Saved to: $output_file"
            PROCESSED=$((PROCESSED + 1))
        done
        
        echo ""
        print_success "Copying complete!"
        echo "  Copied: $PROCESSED file(s)"
    else
        # Process each SVG file with panel_frame_fit.py
        PROCESSED=0
        FAILED=0
        
        for svg_file in "$INPUT_DIR"/*.svg; do
            if [ ! -f "$svg_file" ]; then
                continue
            fi
            
            filename=$(basename "$svg_file")
            filename_noext="${filename%.svg}"
            output_file="$OUTPUT_DIR/${filename_noext}_processed.svg"
            
            print_info "Processing: $filename"
            
            # Build command as array (safer than eval)
            CMD_ARRAY=(python3 "$SCRIPT_DIR/panel_frame_fit.py" "$svg_file" --output "$output_file")
            if [ -n "$PUBLISHER" ]; then
                CMD_ARRAY+=(--outer-publisher "$PUBLISHER")
            fi
            if [ -n "$LAYOUT" ]; then
                CMD_ARRAY+=(--outer-layout "$LAYOUT")
            fi
            
            # Execute command and check exit status
            if "${CMD_ARRAY[@]}"; then
                print_success "  Saved to: $output_file"
                PROCESSED=$((PROCESSED + 1))
            else
                print_error "  Failed to process $filename"
                FAILED=$((FAILED + 1))
            fi
        done
        
        echo ""
        print_success "Processing complete!"
        echo "  Processed: $PROCESSED file(s)"
        if [ "$FAILED" -gt 0 ]; then
            print_warning "  Failed: $FAILED file(s)"
        fi
    fi
fi

# Summary
echo ""
echo "======================================"
print_success "All done!"
echo ""
echo "Output files saved to: $OUTPUT_DIR"
echo ""
if [ "$COMBINE" = true ]; then
    echo "Combined output: $OUTPUT_DIR/combined_output.svg"
else
    echo "Processed files: $OUTPUT_DIR/*_processed.svg"
fi
echo "======================================"
echo ""
