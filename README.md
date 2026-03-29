# TrueNote: Automated Forensic Currency Verification System

TrueNote is a comprehensive, computer-vision-based forensic analysis pipeline designed to authenticate currency notes. By leveraging advanced image processing algorithms, frequency domain analysis, and optical character recognition (OCR), the system performs a rigorous multi-stage inspection to detect both physical counterfeits and digital forgeries.

This repository contains the 491-line Python implementation (`verify_note.py`) that automatically aligns suspect notes, runs 8 distinct forensic checks, and generates an interactive HTML diagnostic report.

---

## 🌟 System Architecture & Features

The verification pipeline evaluates a suspect currency note against a verified master template across multiple dimensions:

*   **Automated Template Matching:** Utilizes ORB (Oriented FAST and Rotated BRIEF) feature detection to automatically identify the denomination of the suspect note from a local database of master templates.
*   **Geometric Alignment:** Computes a homography matrix using RANSAC to perfectly align and warp the suspect note to the master template's perspective and scale.
*   **8-Stage Forensic Analysis:**
    1.  **Structural Similarity (SSIM) [20% weight]:** Evaluates the structural integrity of micro-patterns and overall layout.
    2.  **HSV Color Profiling [10% weight]:** Computes 2D histogram correlation to verify ink color distributions.
    3.  **Laplacian Sharpness [10% weight]:** Measures the variance of the Laplacian to evaluate print quality and simulate intaglio print depth checks.
    4.  **Frequency Domain Analysis (FFT) [15% weight]:** Applies a Fast Fourier Transform to analyze high-frequency spatial patterns (e.g., guilloche patterns).
    5.  **Hologram Validation (NCC) [15% weight]:** Uses Normalized Cross-Correlation to validate the presence and reflective properties of security holograms.
    6.  **UV/IR Simulation [15% weight]:** Isolates specific color channels and applies histogram equalization to simulate ultraviolet and infrared watermark responses.
    7.  **OCR Serial Validation:** Extracts serial numbers using Tesseract OCR and cross-references them against a database of known counterfeit serials (`KNOWN_FAKES`).
    8.  **EXIF Metadata Analysis [15% weight]:** Inspects image metadata to detect signatures of digital forgery (e.g., Adobe Photoshop, GIMP).
*   **Interactive HTML Reporting:** Generates a detailed, standalone HTML dashboard (`forensic_report.html`) featuring a performance radar chart, SSIM difference heatmaps, live exchange rates, and a comprehensive diagnostic summary.
*   **ASCII Art Rendering:** Optional terminal-based ASCII visualization of the aligned note.

---

## 🛠️ Prerequisites & System Requirements

To run this project, your system must have the following installed:

1.  **Python 3.8 or higher**
2.  **Tesseract OCR Engine** (Required for Stage 7: Serial Number Validation)
    *   **Windows:** Download the installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) and ensure the installation path (e.g., `C:\Program Files\Tesseract-OCR`) is added to your System Environment `PATH` variables.
    *   **macOS:** Install via Homebrew:
        ```bash
        brew install tesseract
        ```
    *   **Linux (Ubuntu/Debian):**
        ```bash
        sudo apt-get update
        sudo apt-get install tesseract-ocr
        ```

---

## 📦 Step-by-Step Setup & Installation

Follow these exact steps to configure the project on your local machine:

### Step 1: Clone the Repository
Open your terminal or command prompt and clone the project files to your local machine.
```bash
git clone https://github.com/ishashwatthakur/TrueNote-Automated-Forensic-Currency-Verification-System.git
cd TrueNote
```

### Step 2: Create a Virtual Environment (Recommended)
It is highly recommended to use a virtual environment to manage dependencies.
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies
Install the required computer vision and utility libraries using `pip`.
```bash
pip install opencv-python numpy scikit-image Pillow requests colorama pytesseract
```

### Step 4: Prepare the Directory Structure
The script requires specific folders to locate the master templates and the suspect images. Create the following directories in the root of your project:
```bash
mkdir -p samples/templates
mkdir -p samples/test_images
```

### Step 5: Add Image Assets
1.  **Master Templates:** Place your authentic, high-resolution, unwatermarked master template images inside the `samples/templates/` folder (e.g., `USD_100_template.jpg`). The system will auto-detect which template to use based on ORB features.
2.  **Test Images:** Place the suspect currency images you want to verify inside the `samples/test_images/` folder (e.g., `suspect_note_1.jpg`).

---

## 🚀 Usage Instructions

Execute the pipeline via the command-line interface. The script requires the paths to your template directory and your specific test image.

### Basic Execution
```bash
python verify_note.py --template_dir samples/templates --test samples/test_images/suspect_note_1.jpg
```

### Full Execution (Recommended)
To generate the detailed HTML report and view the ASCII art in the terminal, append the `--html` and `--ascii` flags:
```bash
python verify_note.py --template_dir samples/templates --test samples/test_images/suspect_note_1.jpg --html --ascii
```

### Command-Line Arguments Breakdown:
*   `--template_dir`: **(Required)** Path to the directory containing authentic master templates.
*   `--test`: **(Required)** Path to the specific suspect currency image you are testing.
*   `--html`: *(Optional)* Generates `forensic_report.html` in the root directory, containing visual telemetry, heatmaps, and diagnostic breakdowns.
*   `--ascii`: *(Optional)* Renders a low-resolution ASCII art representation of the aligned note directly in the terminal output.

---

## 📊 Understanding the Output

### 1. Terminal Interface
The CLI provides a structured, real-time breakdown of the analysis:
*   **Setup & Alignment:** Displays the auto-detected denomination and confirms successful homography alignment.
*   **Analysis Execution:** Shows a live progress indicator for each of the 8 forensic stages, outputting `[ PASS ]` or `[ FAIL ]` alongside the specific similarity score for that metric.
*   **Confidence Score:** Calculates the final weighted percentage. A score $\ge 85\%$ (alongside passing critical thresholds like SSIM and OCR) is required for an "Authentic" verdict.
*   **Summary:** A plain-English diagnostic summary listing exactly which checks passed and which failed (e.g., "Laplacian: Low print quality detected").

### 2. HTML Forensic Report (`forensic_report.html`)
If the `--html` flag is utilized, open the generated `forensic_report.html` file in any modern web browser (Chrome, Firefox, Edge). The dashboard includes:
*   **Final Verdict:** The ultimate determination (Authentic vs. Counterfeit) and overall confidence score.
*   **Diagnostic Summary:** A clear list of passed and failed checks.
*   **Stage Breakdown Table:** A tabular view of all metrics, scores, and status flags.
*   **Performance Radar:** An interactive Chart.js visualization mapping the note's performance across all vectors.
*   **Aligned Scan:** The warped and perspective-corrected version of the suspect note.
*   **SSIM Difference Heatmap:** A visual overlay highlighting structural deviations. Red and yellow areas indicate potential physical tampering, print inaccuracies, or layout mismatches compared to the master template.

---

## ⚠️ Academic & Legal Disclaimer
This software is provided for educational, academic, and research purposes only. It demonstrates the application of computer vision algorithms to image authentication. It is **not** a substitute for professional, hardware-based currency authentication equipment (such as magnetic ink scanners or multispectral UV/IR sensors) used by financial institutions and law enforcement.
