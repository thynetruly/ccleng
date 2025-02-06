#!/usr/bin/env python3
"""
extract_comments.py

This script automates the extraction, translation, and re-insertion of comments from C++ source files.
It supports single-line (//) and multi-line (/* ... */) comments (with a preference for C++ style multi-line comments),
and it produces three translation files (segmented, TSV, and bulk) that preserve formatting (including tab characters)
using an optional escape mechanism.

Usage:
    python extract_comments.py <input_paths>... [-o output.xlsx] [-e <extensions>...] [--escape-tabs | --no-escape-tabs]

Example:
    python extract_comments.py ./src -o my_comment_report.xlsx -e "*.cpp" "*.h" --escape-tabs

Before running the re-insertion phase, translate one of the generated files and save the result as
translated_comments.txt in the same directory.
"""

import os
import re
import sys
import argparse
import shutil

try:
    from openpyxl import Workbook
except ImportError:
    print("Please install openpyxl: pip install openpyxl")
    sys.exit(1)

# Global container for Excel rows.
excel_rows = []

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract, translate, and reinsert source code comments."
    )
    parser.add_argument("input_paths", nargs="+",
                        help="One or more file or directory paths to process.")
    parser.add_argument("-o", "--output", default="source_code_comments.xlsx",
                        help="File path for the output XLSX spreadsheet (default: source_code_comments.xlsx)")
    parser.add_argument("-e", "--extensions", nargs="+",
                        default=["*.hpp", "*.cpp", "*.tpp", "*.h"],
                        help="File extensions to include (default: *.hpp *.cpp *.tpp *.h)")
    # Optional flag to enable or disable tab escaping.
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--escape-tabs", dest="escape_tabs", action="store_true",
                       help="Enable tab escaping (convert actual tabs to literal '\\t').")
    group.add_argument("--no-escape-tabs", dest="escape_tabs", action="store_false",
                       help="Disable tab escaping; leave tab characters intact.")
    parser.set_defaults(escape_tabs=True)
    return parser.parse_args()

def discover_files(input_paths, extensions):
    """Discover files from provided files and directories matching the given extensions."""
    found_files = set()
    for path in input_paths:
        if os.path.isfile(path):
            for ext in extensions:
                ext_norm = ext.replace("*", "")
                if path.lower().endswith(ext_norm.lower()):
                    found_files.add(os.path.abspath(path))
                    break
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    for ext in extensions:
                        ext_norm = ext.replace("*", "")
                        if file.lower().endswith(ext_norm.lower()):
                            found_files.add(os.path.abspath(os.path.join(root, file)))
                            break
        else:
            print(f"Warning: {path} is not a file or directory.")
    return list(found_files)

def clean_multiline_lines(lines):
    """
    For each line in a multi-line comment, remove any leading asterisks and adjacent whitespace.
    This is especially useful for C++ style multi-line comments (e.g., those starting with /**).
    """
    cleaned = []
    for line in lines:
        # Remove leading whitespace, one or more asterisks, and an optional following space.
        cleaned_line = re.sub(r'^\s*\*+\s?', '', line)
        cleaned.append(cleaned_line)
    return cleaned

def extract_comments_from_content(content, filename):
    """
    Given the content of a file and its filename, extract comments and return:
      - new_content: The file content with comments replaced by unique placeholders.
      - blocks: A list of comment blocks extracted from this file.
    
    Each comment block is represented as a dictionary with:
       - file: The full filename (with extension).
       - block_id: An integer (per file, starting at 1).
       - type: "single-line" or "multi-line".
       - segments: A list of tuples (index, comment_segment_text).
    
    Placeholders are inserted in the file to maintain code integrity.
    """
    # Regex for single-line and multi-line comments.
    pattern = re.compile(r'//.*?$|/\*.*?\*/', re.MULTILINE | re.DOTALL)
    new_content_parts = []
    last_idx = 0
    blocks = []
    file_block_counter = 1
    base = os.path.basename(filename)  # full filename including extension

    for m in pattern.finditer(content):
        start, end = m.span()
        # Append content before the comment.
        new_content_parts.append(content[last_idx:start])
        comment_text = m.group()

        if comment_text.strip().startswith("//"):
            # Single-line comment processing.
            comment_type = "single-line"
            seg_text = comment_text[2:].strip()  # remove the '//' marker.
            index = f"{base}-{file_block_counter:03d}-01"
            block = {
                "file": filename,
                "block_id": file_block_counter,
                "type": comment_type,
                "segments": [(index, seg_text)]
            }
            blocks.append(block)
            excel_rows.append((filename, comment_type, index, seg_text))
            placeholder = f"//PLACEHOLDER_{index}"
            new_content_parts.append(placeholder)
            file_block_counter += 1

        else:
            # Multi-line comment processing.
            comment_type = "multi-line"
            # Prioritize C++ style multi-line comments (starting with "/**").
            if comment_text.startswith("/**"):
                inner = comment_text[3:-2]  # remove '/**' and '*/'
            else:
                inner = comment_text[2:-2]  # remove '/*' and '*/'
            lines = inner.splitlines()
            lines = clean_multiline_lines(lines)
            segments = []
            placeholder_lines = []
            seg_counter = 1
            for line in lines:
                seg_line = line.strip()
                # Skip completely empty lines (but if all lines are empty, we add one empty segment).
                if seg_line == "":
                    continue
                index = f"{base}-{file_block_counter:03d}-{seg_counter:02d}"
                segments.append((index, seg_line))
                excel_rows.append((filename, comment_type, index, seg_line))
                placeholder_lines.append(f"PLACEHOLDER_{index}")
                seg_counter += 1
            if not segments:
                index = f"{base}-{file_block_counter:03d}-01"
                segments.append((index, ""))
                excel_rows.append((filename, comment_type, index, ""))
                placeholder_lines.append(f"PLACEHOLDER_{index}")
            block = {
                "file": filename,
                "block_id": file_block_counter,
                "type": comment_type,
                "segments": segments
            }
            blocks.append(block)
            file_block_counter += 1
            # Rebuild the multi-line placeholder with preserved comment delimiters.
            placeholder = "/*\n" + "\n".join(placeholder_lines) + "\n*/"
            new_content_parts.append(placeholder)
        last_idx = end

    new_content_parts.append(content[last_idx:])
    new_content = "".join(new_content_parts)
    return new_content, blocks

def write_intermediary_file(original_file, new_content, intermediary_dir):
    """
    Write the new content (with placeholders) to the intermediary directory,
    preserving the relative path of the original file.
    """
    rel_path = os.path.relpath(original_file, os.getcwd())
    dest_path = os.path.join(intermediary_dir, rel_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(new_content)

def generate_excel_report(excel_rows, excel_filename):
    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"
    ws.append(["File Name", "Comment Type", "Comment Index", "Comment Segment"])
    for row in excel_rows:
        ws.append(list(row))
    try:
        wb.save(excel_filename)
        print(f"Excel report saved as {excel_filename}")
    except Exception as e:
        print(f"Error saving Excel file: {e}")

def escape_tabs(text):
    """
    Replace any actual tab characters in the text with the literal string "\t".
    """
    return text.replace("\t", r"\t")

def unescape_tabs(text):
    """
    Replace the literal string "\t" with an actual tab character.
    """
    return text.replace(r"\t", "\t")

def generate_translation_files(blocks_all, base_dir, do_escape_tabs):
    """
    Generate three translation files in the current working directory:
      - comments_to_translate_segmented.txt
      - comments_to_translate_tsv.txt
      - comments_to_translate_bulk.txt

    The behavior of tab escaping is controlled by do_escape_tabs (True/False).
    """
    segmented_filename = os.path.join(base_dir, "comments_to_translate_segmented.txt")
    tsv_filename = os.path.join(base_dir, "comments_to_translate_tsv.txt")
    bulk_filename = os.path.join(base_dir, "comments_to_translate_bulk.txt")

    # Segmented translation file.
    with open(segmented_filename, "w", encoding="utf-8") as f_seg:
        for block in blocks_all:
            for (index, seg) in block["segments"]:
                seg_text = escape_tabs(seg) if do_escape_tabs else seg
                f_seg.write(f"{index} {seg_text}\n")
    print(f"Segmented translation file created: {segmented_filename}")

    # TSV translation file.
    with open(tsv_filename, "w", encoding="utf-8") as f_tsv:
        line_number = 1
        for block in blocks_all:
            seg_texts = [escape_tabs(seg) if do_escape_tabs else seg for (idx, seg) in block["segments"]]
            joined_segments = r'\t'.join(seg_texts)
            f_tsv.write(f"{line_number:04d} {joined_segments}\n")
            line_number += 1
    print(f"TSV translation file created: {tsv_filename}")

    # Bulk translation file.
    with open(bulk_filename, "w", encoding="utf-8") as f_bulk:
        for block in blocks_all:
            base = os.path.basename(block["file"])
            delimiter = f"<||{base}_{block['block_id']:03d}_block_delimiter||>"
            f_bulk.write(delimiter + "\n")
            for (idx, seg) in block["segments"]:
                f_bulk.write(seg + "\n")
        f_bulk.write("\n")
    print(f"Bulk translation file created: {bulk_filename}")

def prompt_for_translation():
    print("\n=== Translation Phase ===")
    print("Three translation files have been generated in the current directory:")
    print("  1. comments_to_translate_segmented.txt")
    print("  2. comments_to_translate_tsv.txt")
    print("  3. comments_to_translate_bulk.txt (recommended)")
    print("\nPlease choose one of these files to translate.")
    print("IMPORTANT: Do not alter the literal escape sequences (e.g., '\\t') or delimiters.")
    print("After translating, save your translations as 'translated_comments.txt' in the same directory.")
    input("Press Enter when 'translated_comments.txt' is ready...")

def detect_translation_format(translated_filename):
    """
    Detect the translation file format used in translated_comments.txt.
    Returns one of: "segmented", "tsv", or "bulk".
    """
    with open(translated_filename, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if content.startswith("<||") or "<||" in content:
        return "bulk"
    elif "\t" in content:
        return "tsv"
    else:
        return "segmented"

def parse_translated_comments(translated_filename, translation_format, blocks_all):
    """
    Parse translated_comments.txt and build a mapping from comment index to the translated segment.
    The parsing strategy depends on the translation file format.
    """
    translation_mapping = {}
    with open(translated_filename, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    if translation_format == "segmented":
        for line in lines:
            if not line.strip():
                continue
            parts = line.split(" ", 1)
            if len(parts) != 2:
                print(f"Warning: Could not parse line in segmented translation: {line}")
                continue
            index, translated = parts
            translation_mapping[index] = translated
    elif translation_format == "tsv":
        if len(lines) != len(blocks_all):
            print("Error: The number of lines in the TSV translation file does not match the number of comment blocks.")
            sys.exit(1)
        for block, line in zip(blocks_all, lines):
            # Remove the four-digit line number and the following space.
            line = line[5:]
            segments_translated = line.split(r'\t')
            if len(segments_translated) != len(block["segments"]):
                print(f"Error: Number of segments in a block does not match (File: {block['file']}, Block: {block['block_id']}).")
                sys.exit(1)
            for (idx, _), trans in zip(block["segments"], segments_translated):
                translation_mapping[idx] = trans
    elif translation_format == "bulk":
        block_translations = []
        current_block_lines = []
        for line in lines:
            if line.startswith("<||") and line.endswith("||>"):
                if current_block_lines:
                    block_translations.append(current_block_lines)
                    current_block_lines = []
            else:
                if line.strip() == "" and not current_block_lines:
                    continue
                current_block_lines.append(line)
        if current_block_lines:
            block_translations.append(current_block_lines)
        if len(block_translations) != len(blocks_all):
            print("Error: The number of blocks in the bulk translation file does not match the extraction.")
            sys.exit(1)
        for block, trans_lines in zip(blocks_all, block_translations):
            if len(trans_lines) != len(block["segments"]):
                print(f"Error: Block segment count mismatch in bulk translation for file {block['file']} block {block['block_id']}.")
                sys.exit(1)
            for (idx, _), trans in zip(block["segments"], trans_lines):
                translation_mapping[idx] = trans
    else:
        print("Error: Unknown translation format.")
        sys.exit(1)
    return translation_mapping

def reinsert_translations(intermediary_dir, output_dir, translation_mapping, do_escape_tabs):
    """
    Walk through the intermediary_dir, replace placeholders with translated text from the translation mapping,
    and write the resulting files to output_dir, preserving the original relative paths.
    
    If do_escape_tabs is True, then the translation mapping values are processed with unescape_tabs() before insertion.
    """
    total_placeholders_replaced = 0

    for root, dirs, files in os.walk(intermediary_dir):
        for file in files:
            in_path = os.path.join(root, file)
            with open(in_path, "r", encoding="utf-8") as f:
                content = f.read()
            def repl(match):
                nonlocal total_placeholders_replaced
                ph = match.group()
                index = ph.replace("PLACEHOLDER_", "").strip()
                if index in translation_mapping:
                    total_placeholders_replaced += 1
                    trans_text = translation_mapping[index]
                    if do_escape_tabs:
                        trans_text = unescape_tabs(trans_text)
                    return trans_text
                else:
                    print(f"Warning: No translation found for placeholder {index}")
                    return ph
            new_content = re.sub(r'PLACEHOLDER_[\w\-\d\.]+', repl, content)
            rel_path = os.path.relpath(in_path, intermediary_dir)
            out_path = os.path.join(output_dir, rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(new_content)
    return total_placeholders_replaced

def verification_checks(original_files, intermediary_dir, output_dir, translation_mapping):
    """
    Perform basic verification:
      - Compare the number of placeholders in the intermediary files with the expected number.
      - Compare file sizes between intermediary and output files.
    """
    placeholder_pattern = re.compile(r'PLACEHOLDER_[\w\-\d\.]+')
    total_placeholders = 0
    total_intermediary_size = 0
    for root, dirs, files in os.walk(intermediary_dir):
        for file in files:
            path = os.path.join(root, file)
            total_intermediary_size += os.path.getsize(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            total_placeholders += len(placeholder_pattern.findall(content))
    expected = len(translation_mapping)
    print(f"Placeholders in intermediary files: {total_placeholders}")
    print(f"Expected translations: {expected}")
    if total_placeholders < expected:
        print("Warning: Fewer placeholders found than expected!")
    total_output_size = 0
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            total_output_size += os.path.getsize(os.path.join(root, file))
    size_diff = abs(total_intermediary_size - total_output_size)
    print(f"Total intermediary files size: {total_intermediary_size} bytes")
    print(f"Total output files size: {total_output_size} bytes")
    if size_diff > 0.1 * total_intermediary_size:
        print("Warning: Large file size difference between intermediary and output files. Check for errors.")
    else:
        print("Verification passed: File sizes are similar.")
    print("Translation re-insertion appears complete.")

def main():
    args = parse_arguments()

    file_list = discover_files(args.input_paths, args.extensions)
    if not file_list:
        print("No files found matching the specified paths and extensions.")
        sys.exit(1)
    print(f"Found {len(file_list)} file(s) to process.")

    intermediary_dir = os.path.join(os.getcwd(), "intermediary_dir")
    if os.path.exists(intermediary_dir):
        shutil.rmtree(intermediary_dir)
    os.makedirs(intermediary_dir)
    print(f"Intermediary directory created at: {intermediary_dir}")

    all_blocks = []
    for file in file_list:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue
        new_content, blocks = extract_comments_from_content(content, file)
        all_blocks.extend(blocks)
        write_intermediary_file(file, new_content, intermediary_dir)

    base_dir = os.getcwd()
    generate_excel_report(excel_rows, args.output)
    generate_translation_files(all_blocks, base_dir, args.escape_tabs)

    print("\n=== Extraction Phase Complete ===")
    print(f"Extracted {len(excel_rows)} comment segments from {len(file_list)} files.")

    prompt_for_translation()

    translated_filename = os.path.join(base_dir, "translated_comments.txt")
    if not os.path.exists(translated_filename):
        print("Error: translated_comments.txt not found. Exiting.")
        sys.exit(1)
    translation_format = detect_translation_format(translated_filename)
    print(f"Detected translation format: {translation_format}")
    translation_mapping = parse_translated_comments(translated_filename, translation_format, all_blocks)
    print(f"Parsed {len(translation_mapping)} translated segments.")

    output_dir = os.path.join(os.getcwd(), "output_dir")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    placeholders_replaced = reinsert_translations(intermediary_dir, output_dir, translation_mapping, args.escape_tabs)
    print(f"Total placeholders replaced: {placeholders_replaced}")

    verification_checks(file_list, intermediary_dir, output_dir, translation_mapping)
    print(f"\nAll translated files are available in the directory: {output_dir}")

if __name__ == "__main__":
    main()
