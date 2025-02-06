# ccleng
C-style Comment Language to ENGlish (or any other language of your choice)

ccleng (Pronounced KLENG) is a Python script designed to automate the extraction, translation, and re-insertion of comments from C++ source files. The tool supports both single-line (`//`) and multi-line (`/* ... */`) comments (with a preference for C++–style multi-line comments), and it produces several translation-friendly output formats that preserve formatting—including tab characters—using a reversible escape mechanism.

> **Note:** This project is intended for projects where source code comments need to be translated (e.g., from Japanese to English) without affecting the underlying code.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [Command-Line Arguments](#command-line-arguments)
  - [Workflow](#workflow)
- [Output Files and Directories](#output-files-and-directories)
- [How It Works](#how-it-works)
  - [Extraction Phase](#extraction-phase)
  - [Translation Phase](#translation-phase)
  - [Re-insertion & Verification Phase](#re-insertion--verification-phase)
- [Customization and Configuration](#customization-and-configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Features

- **Robust Comment Extraction:**  
  Supports both single-line (`//`) and multi-line (`/* ... */`) comments while cleaning formatting artifacts (such as extra leading asterisks in C++ multi-line comments).

- **Multiple Translation Formats:**  
  Automatically generates three different translation files:
  - **Segmented:** One line per comment segment with a unique index.
  - **TSV:** A one-line-per-block file where segments are separated by the literal sequence `\t` and each line is prepended with a four-digit line number.
  - **Bulk:** A structure-preserving file where comment blocks are separated by a unique delimiter.

- **Preservation of Formatting:**  
  Uses a reversible escape mechanism to preserve tab characters in comments. Actual tab characters are replaced with the literal string `\t` unless the sequence is already present.

- **Placeholder-Based Re-insertion:**  
  Creates intermediary copies of the source files with unique placeholders in place of comments. After translation, these placeholders are replaced by the translated text.

- **Verification Checks:**  
  Provides basic verification by comparing placeholder counts and file sizes between intermediary files and the final output.

- **File Identification:**  
  Uses full filenames (with extensions) when generating unique indices, allowing you to distinguish between header and source files.

---

## Requirements

- **Python 3.6+**
- **Dependencies:**
  - [openpyxl](https://pypi.org/project/openpyxl/) (for generating Excel reports)

Install the required module using pip:

```bash
pip install openpyxl
```

---

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/cpp-comment-translator.git
   cd cpp-comment-translator
   ```

2. **(Optional) Create and Activate a Virtual Environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   > **Note:** If a `requirements.txt` file is not provided, simply run `pip install openpyxl`.

---

## Usage

Run the script using Python from the command line. The script accepts a list of files or directories to process and several optional parameters.

### Command-Line Arguments

- **Positional Arguments:**
  - `input_paths`: One or more files or directories containing the C++ source files to process.

- **Optional Arguments:**
  - `-o` or `--output`: Specifies the output Excel report file name (default is `source_code_comments.xlsx`).
  - `-e` or `--extensions`: A space-separated list of file extensions to include (default: `*.hpp *.cpp *.tpp *.h`).

#### Example (POSIX)

```bash
python extract_comments.py ./src -o my_comment_report.xlsx -e "*.cpp" "*.h"
```

#### Example (Windows)

```bash
python extract_comments.py "C:\path\to\your\source" -o my_comment_report.xlsx -e "*.cpp" "*.h"
```

### Workflow

1. **Extraction Phase:**  
   The script scans the provided input paths, extracts comments from each file, replaces them with placeholders in intermediary copies, and generates three translation files along with an Excel summary report.

2. **Translation Phase:**  
   - Choose one of the generated translation files (`comments_to_translate_segmented.txt`, `comments_to_translate_tsv.txt`, or `comments_to_translate_bulk.txt`).
   - Translate the contents (ensuring that literal escape sequences such as `\t` and delimiter markers remain unaltered).
   - Save the translated output as `translated_comments.txt` in the same directory.

3. **Re-insertion & Verification Phase:**  
   The script reads `translated_comments.txt`, replaces placeholders in the intermediary files with the translated comments, writes the final output to `output_dir`, and performs verification checks.

---

## Output Files and Directories

- **`source_code_comments.xlsx`:**  
  An Excel report containing columns for file name, comment type, comment index, and comment segment.

- **Translation Files:**  
  - `comments_to_translate_segmented.txt`
  - `comments_to_translate_tsv.txt`  
    > Each line is prepended with a four-digit line number and segments are separated by the literal `\t`.
  - `comments_to_translate_bulk.txt`

- **`intermediary_dir`:**  
  Contains intermediary copies of the source files with placeholders replacing comments.

- **`output_dir`:**  
  Contains the final source files after the translated comments have been re-inserted.

---

## How It Works

### Extraction Phase

- **File Discovery:**  
  The script recursively scans the specified directories (or individual files) for files matching the given extensions.

- **Comment Extraction:**  
  - Uses regular expressions to extract both single-line (`//`) and multi-line (`/* ... */`) comments.
  - For multi-line comments, especially those in C++ style (e.g., `/** ... */`), the script cleans each line by removing any leading asterisks.
  - Each comment segment is assigned a unique index that includes the full filename (with extension), a block ID, and a segment ID.

- **Placeholder Insertion:**  
  Comments are replaced with unique placeholders in an intermediary copy of each source file to ensure code integrity.

- **Translation File Generation:**  
  Creates three translation files:
  - **Segmented:** One line per comment segment with the format `<index> <escaped comment>`.
  - **TSV:** One line per comment block (with segments separated by the literal `\t` and a four-digit line number).
  - **Bulk:** Blocks separated by unique delimiter lines.

### Translation Phase

- The user selects one of the generated translation files and translates the comments.
- **Important:** The literal escape sequences (e.g., `\t`) and block delimiters must remain unchanged.
- The translated content is saved as `translated_comments.txt`.

### Re-insertion & Verification Phase

- **Parsing Translated Comments:**  
  The script reads `translated_comments.txt` and creates a mapping from each unique index to the translated comment segment.

- **Unescaping Tabs:**  
  (Optional) If desired, the script can reverse the tab escape (i.e., convert literal `\t` back into actual tab characters) during re-insertion.

- **Placeholder Replacement:**  
  The script replaces each placeholder in the intermediary files with its corresponding translated segment.

- **Verification:**  
  It performs checks such as comparing the number of placeholders replaced and file sizes to ensure that the re-insertion was successful.

---

## Customization and Configuration

- **Escape Mechanism:**  
  The function `escape_tabs()` converts actual tab characters to the literal sequence `\t`. An inverse operation can be applied during re-insertion if actual tab characters are desired.

- **Regular Expression Tweaks:**  
  The extraction logic uses regular expressions tuned for C++ style comments. Adjustments can be made if your codebase includes variations in comment formatting.

- **Translation File Format:**  
  The script supports three formats (segmented, TSV, and bulk). Choose the one that best fits your translation workflow.

---

## Troubleshooting

- **Translation File Errors:**  
  - Ensure that literal escape sequences (e.g., `\t`) and delimiters (e.g., `<||...||>`) are not modified during translation.
  - If the script reports mismatches in segment counts, verify that the translation file matches the original structure.

- **Placeholder Replacement Issues:**  
  - Check that all intermediary files in `intermediary_dir` are unmodified before running the re-insertion phase.
  - Review console messages for warnings about missing translations.

- **File Size Discrepancies:**  
  Large differences between intermediary and output file sizes may indicate that some placeholders were not correctly replaced.

---

## Contributing

Contributions are welcome! Porting, adapting, refactoring, and incorporating are all welcome too. If you would like to report a bug, request a feature, or contribute improvements:

1. Fork the repository.
2. Create a feature branch (e.g., `feature/my-new-feature`).
3. Commit your changes.
4. Submit a pull request with a clear description of your changes.

For major changes, please open an issue first to discuss what you would like to change.

---

## License

This project is licensed under the GNU AGPLv3 License. See the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or feedback, please open an issue in the repository or contact the project maintainer via my email listed here on GitHub.

---

Please enjoy!
