"""
image_processor.py
──────────────────
Saare photo effects yahan hain:
  1. Subject Detection  — rembg (U2Net AI model)
  2. Subject Sharpening — unsharp mask
  3. Depth-based Blur   — distance map se graduated blur
  4. Lens Bokeh         — disk-shaped kernel (DSLR look)
  5. Edge Protection    — subject boundary smoothing
  6. HD Enhancement     — CLAHE + color boost
  7. Grain Matching     — realistic film grain
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image

executor = ThreadPoolExecutor(max_workers=2)


# ══════════════════════════════════════════════════════════════
# 1. DISK KERNEL — Bokeh ke liye circular blur
# ══════════════════════════════════════════════════════════════
def _disk_kernel(radius: int) -> np.ndarray:
    """Circular disk-shaped convolution kernel for lens bokeh."""
    size = 2 * radius + 1
    kernel = np.zeros((size, size), dtype=np.float32)
    cv2.circle(kernel, (radius, radius), radius, 1.0, -1)
    kernel /= kernel.sum()
    return kernel


# ══════════════════════════════════════════════════════════════
# 2. SUBJECT MASK — AI se subject detect karo
# ══════════════════════════════════════════════════════════════
def _get_subject_mask(pil_img: Image.Image) -> np.ndarray:
    """
    rembg (U2Net) se subject ka alpha mask nikalo.
    Return: float32 mask [0..1], shape (H, W)
    """
    try:
        from rembg import remove
        output = remove(pil_img)               # RGBA output
        alpha  = np.array(output)[:, :, 3]    # alpha channel
    except Exception:
        # Fallback: GrabCut (rembg na ho to)
        alpha = _grabcut_mask(np.array(pil_img))

    mask = alpha.astype(np.float32) / 255.0
    # Soft edges ke liye biraz blur
    mask = cv2.GaussianBlur(mask, (15, 15), 0)
    return mask


def _grabcut_mask(img_rgb: np.ndarray) -> np.ndarray:
    """Lightweight fallback — center rectangle se GrabCut."""
    h, w = img_rgb.shape[:2]
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    mask_gc = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    rect = (w // 8, h // 8, 6 * w // 8, 6 * h // 8)
    cv2.grabCut(img_bgr, mask_gc, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    result = np.where((mask_gc == 2) | (mask_gc == 0), 0, 255).astype(np.uint8)
    return result


# ══════════════════════════════════════════════════════════════
# 3. SUBJECT SHARPENING
# ══════════════════════════════════════════════════════════════
def _sharpen_subject(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Subject (foreground) ko sharpen karo, background untouched."""
    # Unsharp mask
    blurred   = cv2.GaussianBlur(img, (0, 0), sigmaX=2.5)
    sharpened = cv2.addWeighted(img, 1.6, blurred, -0.6, 0)

    m3 = np.stack([mask, mask, mask], axis=2)
    result = img.astype(np.float32) * (1 - m3) + sharpened.astype(np.float32) * m3
    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════
# 4. DEPTH-DEPENDENT BLUR + LENS BOKEH
# ══════════════════════════════════════════════════════════════
def _apply_depth_bokeh(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Background me depth-wise bokeh blur:
    • Depth map — subject se distance ke hisaab se
    • Jitna door, utna zyada blur
    • Disk kernel = DSLR-style bokeh circles
    """
    mask_u8 = (mask * 255).astype(np.uint8)

    # Distance map (subject se kitni door hai background)
    inv_mask = cv2.bitwise_not(mask_u8)
    dist_map = cv2.distanceTransform(inv_mask, cv2.DIST_L2, 5)
    if dist_map.max() > 0:
        dist_map /= dist_map.max()  # 0..1

    # 4 layer graduated blur
    blur_layers = [
        (0.25, _disk_kernel(4)),   # slight blur near subject
        (0.50, _disk_kernel(9)),   # medium
        (0.75, _disk_kernel(14)),  # heavy
        (1.00, _disk_kernel(20)),  # maximum
    ]

    composite = img.astype(np.float32)
    prev_t = 0.0

    for threshold, kernel in blur_layers:
        blurred = cv2.filter2D(img, -1, kernel).astype(np.float32)
        # Sirf is depth band ka mask
        band = np.clip((dist_map - prev_t) / (threshold - prev_t + 1e-6), 0, 1)
        b3   = np.stack([band, band, band], axis=2)
        composite = composite * (1 - b3) + blurred * b3
        prev_t = threshold

    # Subject puri tarah sharp rakho
    m3 = np.stack([mask, mask, mask], axis=2)
    result = img.astype(np.float32) * m3 + composite * (1 - m3)
    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════
# 5. EDGE PROTECTION
# ══════════════════════════════════════════════════════════════
def _protect_edges(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Subject boundary ke aas-paas ek 'protection zone' banao.
    Wahan background blur thoda kam hoga — harsh cutout look avoid.
    """
    mask_u8  = (mask * 255).astype(np.uint8)
    edges    = cv2.Canny(mask_u8, 40, 120)

    # Edge zone dilate karo
    k        = np.ones((7, 7), np.uint8)
    edge_dil = cv2.dilate(edges, k, iterations=3)
    edge_f   = cv2.GaussianBlur(
        edge_dil.astype(np.float32), (21, 21), 0
    ) / 255.0

    # Edge zone me thoda fine blur (fringe artifacts hatao)
    fine_blur = cv2.GaussianBlur(img, (5, 5), 0).astype(np.float32)
    e3 = np.stack([edge_f, edge_f, edge_f], axis=2) * 0.4
    result = img.astype(np.float32) * (1 - e3) + fine_blur * e3
    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════
# 6. HD ENHANCEMENT — CLAHE + Color Vibrancy
# ══════════════════════════════════════════════════════════════
def _enhance_hd(img: np.ndarray) -> np.ndarray:
    """CLAHE contrast + subtle color boost + mild sharpening."""
    # CLAHE on L channel
    lab   = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l     = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    # Subtle saturation boost
    hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.15, 0, 255)
    enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # Light sharpening pass
    sharp_k = np.array([
        [ 0, -0.5,  0],
        [-0.5, 3, -0.5],
        [ 0, -0.5,  0]
    ], dtype=np.float32)
    sharpened = cv2.filter2D(enhanced, -1, sharp_k)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════
# 7. GRAIN MATCHING — Realistic film grain
# ══════════════════════════════════════════════════════════════
def _add_grain(img: np.ndarray, intensity: float = 0.015) -> np.ndarray:
    """
    Luminance-aware film grain:
    • Shadows me zyada grain (realistic)
    • Highlights me kam grain
    """
    h, w = img.shape[:2]

    # Luminance map (0..1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    # Shadows me grain zyada chahiye
    grain_strength = (1.0 - gray) * 0.7 + 0.3   # range 0.3..1.0

    noise = np.random.normal(0, 1, (h, w)).astype(np.float32)
    noise = cv2.GaussianBlur(noise, (3, 3), 0)   # slight smoothing = film-like
    noise = noise * grain_strength * intensity * 255

    noise_3d = np.stack([noise, noise, noise], axis=2)
    result = img.astype(np.float32) + noise_3d
    return np.clip(result, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════
def _process_sync(input_path: str, output_path: str):
    """Synchronous full pipeline (runs in thread pool)."""
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Image load nahi hui: {input_path}")

    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    print("[1/6] Subject detect ho raha hai...")
    mask = _get_subject_mask(pil_img)

    print("[2/6] Subject sharpen ho raha hai...")
    img = _sharpen_subject(img, mask)

    print("[3/6] Depth bokeh apply ho raha hai...")
    img = _apply_depth_bokeh(img, mask)

    print("[4/6] Edges protect ho rahe hain...")
    img = _protect_edges(img, mask)

    print("[5/6] HD enhance ho raha hai...")
    img = _enhance_hd(img)

    print("[6/6] Grain match ho raha hai...")
    img = _add_grain(img)

    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 97])
    print("✅ Done!")


# Lightweight fallback (rembg na ho to)
def _process_lite_sync(input_path: str, output_path: str):
    """GrabCut-based lite pipeline."""
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError("Image load nahi hui")

    pil_img   = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    alpha_arr = _grabcut_mask(np.array(pil_img))
    mask = alpha_arr.astype(np.float32) / 255.0
    mask = cv2.GaussianBlur(mask, (15, 15), 0)

    img = _sharpen_subject(img, mask)
    img = _apply_depth_bokeh(img, mask)
    img = _protect_edges(img, mask)
    img = _enhance_hd(img)
    img = _add_grain(img)
    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 97])


# ──────────────────────────────────────────────────────────────
# Async wrappers (bot.py inhe call karta hai)
# ──────────────────────────────────────────────────────────────
async def enhance_image(input_path: str, output_path: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, _process_sync, input_path, output_path)


async def enhance_image_lite(input_path: str, output_path: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, _process_lite_sync, input_path, output_path)
