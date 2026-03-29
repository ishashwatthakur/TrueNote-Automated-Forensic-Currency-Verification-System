import cv2
import numpy as np
import os
import random

def draw_guilloche_pattern(img, color):
    """Draws a complex, high-frequency mathematical pattern (Guilloche)."""
    h, w = img.shape[:2]
    center_x, center_y = w // 2, h // 2
    for theta in np.arange(0, 2 * np.pi, 0.05):
        R, r, d = 150, 52, 70
        x = int(center_x + (R - r) * np.cos(theta) + d * np.cos((R - r) / r * theta))
        y = int(center_y + (R - r) * np.sin(theta) - d * np.sin((R - r) / r * theta))
        cv2.circle(img, (x, y), 1, color, -1)
    return img

def create_base_note(denomination="100", serial="AB12345678", color=(200, 230, 200), is_fake=False):
    """Creates a synthetic banknote with serials, UV watermarks, and denominations."""
    img = np.ones((300, 600, 3), dtype=np.uint8) * np.array(color, dtype=np.uint8)
    
    # 1. High-frequency Guilloche pattern
    if not is_fake:
        img = draw_guilloche_pattern(img, (170, 210, 170))
    else:
        img = draw_guilloche_pattern(img, (180, 220, 180))
        img = cv2.GaussianBlur(img, (3, 3), 0) 
    
    # 2. Hidden UV Watermark (Simulated)
    # We draw this with a color VERY close to the background (e.g., +15 on the Blue channel).
    # Invisible to the naked eye, but pops out under histogram equalization (UV simulation).
    if not is_fake:
        uv_color = (min(255, color[0] + 15), color[1], color[2])
        cv2.putText(img, "UV-SECURE", (220, 250), cv2.FONT_HERSHEY_DUPLEX, 1.5, uv_color, 4)
    
    # 3. Borders & Text
    cv2.rectangle(img, (20, 20), (580, 280), (50, 100, 50), 5)
    cv2.rectangle(img, (25, 25), (575, 275), (70, 120, 70), 1)
    
    # Denomination
    cv2.putText(img, denomination, (50, 100), cv2.FONT_HERSHEY_TRIPLEX, 3, (40, 90, 40), 5)
    cv2.putText(img, "BANK OF CV", (180, 150), cv2.FONT_HERSHEY_COMPLEX, 2, (40, 90, 40), 4)
    
    # 4. Serial Number (For OCR)
    cv2.putText(img, f"SN: {serial}", (380, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 200), 2)
    
    # 5. Security Hologram
    cv2.circle(img, (500, 150), 45, (80, 140, 80), -1)
    
    # 6. Micro-text
    if not is_fake:
        cv2.putText(img, "AUTHORIZED TENDER", (180, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (50, 100, 50), 1)
        cv2.circle(img, (500, 150), 35, (100, 160, 100), 2)
    
    # Add paper texture/noise
    noise = np.random.randint(0, 25, (300, 600, 3), dtype=np.uint8)
    img = cv2.add(img, noise)
    
    if is_fake:
        img = cv2.GaussianBlur(img, (3, 3), 0)
        
    return img

def apply_camera_transform(img, angle, scale):
    """Simulates taking a photo of the note at an angle."""
    padded = cv2.copyMakeBorder(img, 150, 150, 150, 150, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    center = (padded.shape[1]//2, padded.shape[0]//2)
    matrix = cv2.getRotationMatrix2D(center, angle, scale) 
    warped = cv2.warpAffine(padded, matrix, (padded.shape[1], padded.shape[0]), borderValue=(255,255,255))
    return warped

def main():
    os.makedirs("samples/templates", exist_ok=True)
    os.makedirs("samples/test_images", exist_ok=True)
    
    denominations = ["10", "50", "100"]
    colors = [(230, 200, 200), (200, 200, 230), (200, 230, 200)] # Different colors for different notes
    
    print("[INFO] Generating Master Templates for Auto-Detection...")
    for denom, color in zip(denominations, colors):
        template = create_base_note(denomination=denom, serial="MASTER000", color=color)
        cv2.imwrite(f"samples/templates/template_{denom}.jpg", template)
    
    print("[INFO] Generating Test Images...")
    # 1. Authentic $50 Note
    auth_50 = create_base_note(denomination="50", serial="XY98765432", color=(200, 200, 230))
    auth_50_photo = apply_camera_transform(auth_50, 12, 0.85)
    auth_50_photo = cv2.convertScaleAbs(auth_50_photo, alpha=0.95, beta=10) # Lighting change
    cv2.imwrite("samples/test_images/test_authentic_50.jpg", auth_50_photo)
    
    # 2. Fake $100 Note (Known counterfeit serial, missing UV, missing microtext)
    fake_100 = create_base_note(denomination="100", serial="FAKE999999", color=(190, 235, 190), is_fake=True)
    fake_100_photo = apply_camera_transform(fake_100, -8, 0.88)
    cv2.imwrite("samples/test_images/test_fake_100.jpg", fake_100_photo)

    print("[INFO] Advanced sample images generated successfully!")
    print("  - Templates saved in: samples/templates/")
    print("  - Test images saved in: samples/test_images/")

if __name__ == "__main__":
    main()
