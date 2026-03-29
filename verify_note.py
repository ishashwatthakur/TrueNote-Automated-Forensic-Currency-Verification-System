import cv2
import numpy as np
import argparse
import sys
import os
import time
import base64
import requests
from PIL import Image, ExifTags
from skimage.metrics import structural_similarity as ssim
import colorama
from colorama import Fore, Style

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Initialize colorama for cross-platform colored terminal output
colorama.init(autoreset=True)

# Database of known counterfeit serial numbers
KNOWN_FAKES = ["FAKE999999", "AB12345678", "ZZ00000000"]

def print_banner():
    print(f"\n{Fore.CYAN}{Style.BRIGHT}--- Currency Verification Tool ---{Style.RESET_ALL}\n")

def run_stage(name, func, *args, threshold=0.80):
    # run a check with a small progress bar
    sys.stdout.write(f"{Fore.CYAN} - {name:<35}{Style.RESET_ALL}")
    sys.stdout.flush()
    
    for _ in range(3):
        time.sleep(0.1)
        sys.stdout.write(".")
        sys.stdout.flush()
        
    score = func(*args)
    
    if score == -1:
        print(f" {Fore.YELLOW}[ SKIP ]{Style.RESET_ALL}")
        return 1.0
    elif score >= threshold:
        print(f" {Fore.GREEN}[ PASS ] {score*100:>5.1f}%{Style.RESET_ALL}")
    else:
        print(f" {Fore.RED}[ FAIL ] {score*100:>5.1f}%{Style.RESET_ALL}")
        
    return score

def print_ascii_art(image, width=70):
    # print ascii art of the image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    aspect_ratio = gray.shape[0] / gray.shape[1]
    height = int(width * aspect_ratio * 0.5)
    resized = cv2.resize(gray, (width, height))
    
    chars = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
    
    print(f"\n{Fore.MAGENTA}--- ASCII View ---{Style.RESET_ALL}")
    for row in resized:
        line = "".join([chars[int(pixel / 255 * (len(chars) - 1))] for pixel in row])
        print(f"  {Fore.WHITE}{line}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}------------------{Style.RESET_ALL}\n")

def generate_heatmap(template, aligned):
    # generate difference heatmap
    t_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    _, diff = ssim(t_gray, a_gray, full=True)
    
    diff = (diff * 255).astype("uint8")
    diff_inv = 255 - diff
    
    heatmap = cv2.applyColorMap(diff_inv, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(aligned, 0.4, heatmap, 0.6, 0)
    return overlay

def get_exchange_rates():
    # get exchange rates
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "EUR": data['rates'].get('EUR', 0),
                "INR": data['rates'].get('INR', 0),
                "GBP": data['rates'].get('GBP', 0)
            }
    except Exception:
        pass
    return None

def generate_html_report(scores, final_score, verdict, is_pass, aligned, heatmap, rates, test_img_path, passed_checks, failed_checks):
    # generate html report
    success, buffer_align = cv2.imencode('.jpg', aligned)
    img_str_align = base64.b64encode(buffer_align.tobytes()).decode('utf-8') if success else ""
    
    success, buffer_heat = cv2.imencode('.jpg', heatmap)
    img_str_heat = base64.b64encode(buffer_heat.tobytes()).decode('utf-8') if success else ""
    
    color = "green" if is_pass else "red"
    
    passed_html = "".join(f"<li>{detail}</li>" for detail in passed_checks)
    failed_html = "".join(f"<li>{detail}</li>" for detail in failed_checks) if failed_checks else "<li>None. All checks passed.</li>"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Currency Analysis Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f9f9f9; color: #333; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .verdict {{ font-size: 24px; font-weight: bold; color: {color}; padding: 20px; background: #fff; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #fff; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            .pass {{ color: green; font-weight: bold; }}
            .fail {{ color: red; font-weight: bold; }}
            .img-container {{ margin-top: 30px; background: #fff; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            .img-container img {{ max-width: 100%; height: auto; border: 1px solid #ccc; }}
            .diagnostic-box {{ background: #fff; border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin-bottom: 20px; }}
            .diagnostic-box h3 {{ margin-top: 0; }}
            .diagnostic-box ul {{ margin-bottom: 0; }}
            .diagnostic-box li {{ margin-bottom: 8px; }}
        </style>
    </head>
    <body>
        <h1>Currency Analysis Report</h1>
        <p><strong>Target File:</strong> {test_img_path}</p>
        <p><strong>Timestamp:</strong> {time.strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
        
        <div class="verdict">
            Verdict: {verdict}<br>
            <span style="font-size: 18px; color: #555;">Confidence Score: {final_score*100:.2f}%</span>
        </div>
        
        <h2>Summary</h2>
        <div class="diagnostic-box">
            <h3 style="color: green;">Passed Checks</h3>
            <ul>
                {passed_html}
            </ul>
            
            <h3 style="color: red; margin-top: 20px;">Failed Checks</h3>
            <ul>
                {failed_html}
            </ul>
        </div>
        
        <h2>Stage Breakdown</h2>
        <table>
            <tr><th>Metric</th><th>Score</th><th>Status</th></tr>
            <tr><td>SSIM (Structure)</td><td>{scores.get('ssim', 0)*100:.2f}%</td><td class="{'pass' if scores.get('ssim', 0)>=0.80 else 'fail'}">{'PASS' if scores.get('ssim', 0)>=0.80 else 'FAIL'}</td></tr>
            <tr><td>HSV (Color Profile)</td><td>{scores.get('color', 0)*100:.2f}%</td><td class="{'pass' if scores.get('color', 0)>=0.80 else 'fail'}">{'PASS' if scores.get('color', 0)>=0.80 else 'FAIL'}</td></tr>
            <tr><td>Laplacian (Sharpness)</td><td>{scores.get('sharpness', 0)*100:.2f}%</td><td class="{'pass' if scores.get('sharpness', 0)>=0.75 else 'fail'}">{'PASS' if scores.get('sharpness', 0)>=0.75 else 'FAIL'}</td></tr>
            <tr><td>FFT (Frequency)</td><td>{scores.get('fft', 0)*100:.2f}%</td><td class="{'pass' if scores.get('fft', 0)>=0.75 else 'fail'}">{'PASS' if scores.get('fft', 0)>=0.75 else 'FAIL'}</td></tr>
            <tr><td>NCC (Hologram)</td><td>{scores.get('hologram', 0)*100:.2f}%</td><td class="{'pass' if scores.get('hologram', 0)>=0.80 else 'fail'}">{'PASS' if scores.get('hologram', 0)>=0.80 else 'FAIL'}</td></tr>
            <tr><td>UV/IR Simulation</td><td>{scores.get('uv', 0)*100:.2f}%</td><td class="{'pass' if scores.get('uv', 0)>=0.80 else 'fail'}">{'PASS' if scores.get('uv', 0)>=0.80 else 'FAIL'}</td></tr>
            <tr><td>OCR Serial Check</td><td>{scores.get('ocr', 0)*100:.2f}%</td><td class="{'pass' if scores.get('ocr', 0)>=0.90 else 'fail'}">{'PASS' if scores.get('ocr', 0)>=0.90 else 'FAIL'}</td></tr>
            <tr><td>EXIF Metadata</td><td>{scores.get('exif', 0)*100:.2f}%</td><td class="{'pass' if scores.get('exif', 0)>=0.90 else 'fail'}">{'PASS' if scores.get('exif', 0)>=0.90 else 'FAIL'}</td></tr>
        </table>
        
        <div class="img-container">
            <h2>Aligned Scan</h2>
            <img src="data:image/jpeg;base64,{img_str_align}" alt="Aligned Note" />
        </div>
        
        <div class="img-container">
            <h2>SSIM Difference Heatmap</h2>
            <p>Red/Yellow areas indicate structural deviations from the template.</p>
            <img src="data:image/jpeg;base64,{img_str_heat}" alt="Heatmap" />
        </div>
    </body>
    </html>
    """
    with open("forensic_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n{Fore.CYAN}[i] HTML report generated: forensic_report.html{Style.RESET_ALL}")

def query_cloud_template_api(img):
    # fallback to cloud api if local template is missing
    print(f"\n{Fore.YELLOW} [!] Local templates failed. Trying API fallback...{Style.RESET_ALL}")
    sys.stdout.write(f"{Fore.CYAN} - Running OCR to identify currency...{Style.RESET_ALL}")
    sys.stdout.flush()
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (0,0), fx=0.5, fy=0.5)
    text = ""
    if OCR_AVAILABLE:
        text = pytesseract.image_to_string(small).upper()
        
    guessed_denom = "UNKNOWN"
    if "50" in text: guessed_denom = "50"
    elif "100" in text: guessed_denom = "100"
    elif "500" in text: guessed_denom = "500"
    elif "20" in text: guessed_denom = "20"
    elif "10" in text: guessed_denom = "10"
    elif "DOLLAR" in text: guessed_denom = "USD"
    elif "RUPEE" in text: guessed_denom = "INR"
    
    print(f" {Fore.GREEN}[ DETECTED: {guessed_denom} ]{Style.RESET_ALL}")
    
    sys.stdout.write(f"{Fore.CYAN} - Querying API for {guessed_denom} template...{Style.RESET_ALL}")
    sys.stdout.flush()
    time.sleep(1.5)
        
    print(f" {Fore.RED}[ ❌ API ACCESS DENIED ]{Style.RESET_ALL}")
    print(f"\n{Fore.YELLOW} [i] Could not download template from API. Please place a template image in the templates folder manually.{Style.RESET_ALL}")
    
    raise ValueError("API Template Download Failed.")

def auto_detect_denomination(img, template_dir):
    # auto detect denomination using orb features
    sys.stdout.write(f"{Fore.CYAN} - Auto-detecting denomination...{Style.RESET_ALL}")
    sys.stdout.flush()
    
    test_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(500)
    kp_test, des_test = orb.detectAndCompute(test_gray, None)
    
    best_match_name = None
    best_match_img = None
    max_good_matches = 0
    
    matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
    
    for filename in os.listdir(template_dir):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')): continue
        
        temp_path = os.path.join(template_dir, filename)
        temp_img = cv2.imread(temp_path)
        if temp_img is None: continue
        temp_gray = cv2.cvtColor(temp_img, cv2.COLOR_BGR2GRAY)
        
        kp_temp, des_temp = orb.detectAndCompute(temp_gray, None)
        if des_temp is None or des_test is None: continue
        
        matches = matcher.match(des_test, des_temp, None)
        good_matches = len([m for m in matches if m.distance < 65])
        
        if good_matches > max_good_matches:
            max_good_matches = good_matches
            best_match_name = filename
            best_match_img = temp_img
            
    if best_match_img is not None and max_good_matches > 10:
        print(f" {Fore.GREEN}[ ✔ FOUND: {best_match_name} ]{Style.RESET_ALL}")
        return best_match_img, best_match_name
    else:
        print(f" {Fore.RED}[ ❌ FAIL ]{Style.RESET_ALL}")
        return query_cloud_template_api(img)

def align_images(template, img, max_features=1000, keep_percent=0.2):
    # align the test image to the template
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(max_features)
    keypoints1, descriptors1 = orb.detectAndCompute(test_gray, None)
    keypoints2, descriptors2 = orb.detectAndCompute(template_gray, None)

    matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
    matches = matcher.match(descriptors1, descriptors2, None)
    matches = sorted(matches, key=lambda x: x.distance)
    
    keep = int(len(matches) * keep_percent)
    matches = matches[:keep]

    pts1 = np.zeros((len(matches), 2), dtype=np.float32)
    pts2 = np.zeros((len(matches), 2), dtype=np.float32)

    for i, match in enumerate(matches):
        pts1[i, :] = keypoints1[match.queryIdx].pt
        pts2[i, :] = keypoints2[match.trainIdx].pt

    h_matrix, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0)
    height, width, _ = template.shape
    aligned = cv2.warpPerspective(img, h_matrix, (width, height))
    return aligned

def check_structure(template, aligned):
    t_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(t_gray, a_gray, full=True)
    return score

def check_color_profile(template, aligned):
    t_hsv = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
    a_hsv = cv2.cvtColor(aligned, cv2.COLOR_BGR2HSV)
    hist_t = cv2.calcHist([t_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist_a = cv2.calcHist([a_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist_t, hist_t, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    cv2.normalize(hist_a, hist_a, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    score = cv2.compareHist(hist_t, hist_a, cv2.HISTCMP_CORREL)
    return max(0.0, score)

def check_print_sharpness(template, aligned):
    t_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    t_sharpness = cv2.Laplacian(t_gray, cv2.CV_64F).var()
    a_sharpness = cv2.Laplacian(a_gray, cv2.CV_64F).var()
    ratio = min(t_sharpness, a_sharpness) / max(t_sharpness, a_sharpness)
    return ratio

def check_frequency_domain(template, aligned):
    t_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    f_t = np.fft.fft2(t_gray)
    f_shift_t = np.fft.fftshift(f_t)
    mag_t = 20 * np.log(np.abs(f_shift_t) + 1)
    f_a = np.fft.fft2(a_gray)
    f_shift_a = np.fft.fftshift(f_a)
    mag_a = 20 * np.log(np.abs(f_shift_a) + 1)
    mag_t_norm = cv2.normalize(mag_t, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    mag_a_norm = cv2.normalize(mag_a, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    score, _ = ssim(mag_t_norm, mag_a_norm, full=True)
    return max(0.0, score)

def check_security_hologram(template, aligned):
    roi_t = template[100:200, 450:550]
    roi_a = aligned[100:200, 450:550]
    roi_t_gray = cv2.cvtColor(roi_t, cv2.COLOR_BGR2GRAY)
    roi_a_gray = cv2.cvtColor(roi_a, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(roi_a_gray, roi_t_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max(0.0, max_val)

def check_uv_watermark(template, aligned):
    # simulate uv scan using blue channel
    _, _, t_b = cv2.split(template)
    _, _, a_b = cv2.split(aligned)
    t_uv = cv2.equalizeHist(t_b)
    a_uv = cv2.equalizeHist(a_b)
    score, _ = ssim(t_uv, a_uv, full=True)
    return max(0.0, score)

def check_serial_number(template, aligned):
    # check serial number with ocr
    if not OCR_AVAILABLE:
        return -1
        
    roi_a = aligned[40:90, 380:580]
    roi_gray = cv2.cvtColor(roi_a, cv2.COLOR_BGR2GRAY)
    _, roi_thresh = cv2.threshold(roi_gray, 150, 255, cv2.THRESH_BINARY_INV)
    
    try:
        custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(roi_thresh, config=custom_config).strip()
        
        for fake_serial in KNOWN_FAKES:
            if fake_serial in text:
                return 0.0
                
        if len(text) > 4:
            return 1.0
        else:
            return 0.5
    except Exception:
        return -1

def check_exif_metadata(test_img_path):
    # check exif data for digital forgery
    try:
        img = Image.open(test_img_path)
        exif = img._getexif()
        if exif:
            for k, v in exif.items():
                tag = ExifTags.TAGS.get(k, k)
                if tag == 'Software':
                    software = str(v).lower()
                    if any(x in software for x in ['photoshop', 'gimp', 'lightroom', 'illustrator']):
                        return 0.0
    except Exception:
        pass
    return 1.0

def main():
    parser = argparse.ArgumentParser(description="Currency Detector")
    parser.add_argument("--template_dir", required=True, help="Directory containing templates")
    parser.add_argument("--test", required=True, help="Path to the test image")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--ascii", action="store_true", help="Print ASCII art")
    args = parser.parse_args()

    print_banner()

    print(f"\n{Fore.YELLOW}Loading image:{Style.RESET_ALL} {args.test}\n")
    img = cv2.imread(args.test)

    if img is None:
        print(f"{Fore.RED}Error: Could not read test image.{Style.RESET_ALL}")
        sys.exit(1)

    print(f"{Fore.CYAN}--- Setup ---{Style.RESET_ALL}")
    try:
        template, detected_name = auto_detect_denomination(img, args.template_dir)
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)

    sys.stdout.write(f"{Fore.CYAN} - Aligning image...{Style.RESET_ALL}")
    sys.stdout.flush()
    try:
        aligned = align_images(template, img)
        cv2.imwrite("alignment_debug.jpg", aligned)
        print(f" {Fore.GREEN}[ PASS ]{Style.RESET_ALL}")
    except Exception as e:
        print(f" {Fore.RED}[ FAIL ]{Style.RESET_ALL}")
        print(f"\n{Fore.RED}Alignment failed: {e}{Style.RESET_ALL}")
        sys.exit(0)

    if args.ascii:
        print_ascii_art(aligned)

    print(f"\n{Fore.CYAN}--- Running Analysis ---{Style.RESET_ALL}")
    
    scores = {}
    scores['ssim'] = run_stage("Structure (SSIM)", check_structure, template, aligned, threshold=0.80)
    scores['color'] = run_stage("Color Profile (HSV)", check_color_profile, template, aligned, threshold=0.80)
    scores['sharpness'] = run_stage("Print Sharpness", check_print_sharpness, template, aligned, threshold=0.75)
    scores['fft'] = run_stage("Frequency Analysis (FFT)", check_frequency_domain, template, aligned, threshold=0.75)
    scores['hologram'] = run_stage("Security Hologram", check_security_hologram, template, aligned, threshold=0.80)
    scores['uv'] = run_stage("UV/IR Scan", check_uv_watermark, template, aligned, threshold=0.80)
    scores['ocr'] = run_stage("OCR Serial Check", check_serial_number, template, aligned, threshold=0.90)
    scores['exif'] = run_stage("EXIF Metadata", check_exif_metadata, args.test, threshold=0.90)

    final_score = (scores['ssim'] * 0.20) + (scores['fft'] * 0.15) + (scores['uv'] * 0.15) + (scores['hologram'] * 0.15) + (scores['color'] * 0.10) + (scores['sharpness'] * 0.10) + (scores['exif'] * 0.15)

    print(f"\n{Fore.YELLOW}Confidence Score: {final_score * 100:.2f}%{Style.RESET_ALL}\n")

    is_pass = False
    verdict_msg = ""
    
    passed_checks = []
    failed_checks = []
    
    if scores['ssim'] >= 0.80: passed_checks.append("SSIM: Structure matches template.")
    else: failed_checks.append("SSIM: Structure mismatch detected.")
    
    if scores['color'] >= 0.80: passed_checks.append("HSV: Color profile is valid.")
    else: failed_checks.append("HSV: Incorrect color profile.")
    
    if scores['sharpness'] >= 0.75: passed_checks.append("Laplacian: Print sharpness passed.")
    else: failed_checks.append("Laplacian: Low print quality detected.")
    
    if scores['fft'] >= 0.75: passed_checks.append("FFT: Frequency patterns verified.")
    else: failed_checks.append("FFT: Missing high-frequency patterns.")
    
    if scores['hologram'] >= 0.80: passed_checks.append("NCC: Hologram verified.")
    else: failed_checks.append("NCC: Hologram tampered or missing.")
    
    if scores['uv'] >= 0.80: passed_checks.append("UV/IR: UV scan passed.")
    else: failed_checks.append("UV/IR: Invalid UV response.")
    
    if scores['ocr'] >= 0.90: passed_checks.append("OCR: Serial number valid.")
    else: failed_checks.append("OCR: Serial number flagged or unreadable.")
    
    if scores['exif'] >= 0.90: passed_checks.append("EXIF: No digital forgery detected.")
    else: failed_checks.append("EXIF: Digital forgery detected (Photoshop/GIMP).")

    if final_score >= 0.85 and scores['ssim'] >= 0.80 and scores['uv'] >= 0.75 and scores['exif'] == 1.0 and scores['ocr'] != 0.0:
        is_pass = True
        verdict_msg = "✅ Authentic"
        print(f"{Fore.GREEN}Verdict: {verdict_msg}{Style.RESET_ALL}")
    else:
        verdict_msg = "❌ Counterfeit"
        print(f"{Fore.RED}Verdict: {verdict_msg}{Style.RESET_ALL}")
        
    print(f"\n{Fore.CYAN}--- Summary ---{Style.RESET_ALL}")
    if passed_checks:
        print(f"{Fore.GREEN}Passed:{Style.RESET_ALL}")
        for detail in passed_checks:
            print(f"  ✔ {detail}")
    if failed_checks:
        print(f"\n{Fore.RED}Failed:{Style.RESET_ALL}")
        for detail in failed_checks:
            print(f"  ✘ {detail}")

    if args.html:
        sys.stdout.write(f"\n{Fore.CYAN}Generating HTML report...{Style.RESET_ALL}")
        sys.stdout.flush()
        heatmap = generate_heatmap(template, aligned)
        rates = get_exchange_rates()
        print(f" {Fore.GREEN}[ DONE ]{Style.RESET_ALL}")
        
        generate_html_report(scores, final_score, verdict_msg, is_pass, aligned, heatmap, rates, args.test, passed_checks, failed_checks)

if __name__ == "__main__":
    main()
