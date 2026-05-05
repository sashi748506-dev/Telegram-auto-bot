import cv2
import numpy as np
import torch
from PIL import Image, ImageFilter, ImageEnhance

# 1. AI Depth Model Configuration (MiDaS Open-Source Model)
print("AI Depth Model background mein load ho raha hai...")
model_type = "MiDaS_small"  # Free aur lightweight model taaki processing tez ho
midas = torch.hub.load("intel-isl/MiDaS", model_type)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
midas.to(device)
midas.eval()

# MiDaS Ki image transform processing load karna
midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
transform = midas_transforms.small_transform if model_type == "MiDaS_small" else midas_transforms.dpt_transform

def enhance_photo_with_depth(image_path, output_path):
    # Original Image ko OpenCV aur PIL dono formats mein read karna
    img_cv = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    
    h, w, _ = img_cv.shape

    # ---- STEP 1: AI DEPTH MAP GENERATION ----
    # AI check karega ki foreground (subject) aur background kahan hain
    input_batch = transform(img_rgb).to(device)
    with torch.no_grad():
        prediction = midas(input_batch)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img_cv.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()
    
    depth_map = prediction.cpu().numpy()
    depth_map = cv2.normalize(depth_map, None, 0, 255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    # ---- STEP 2: SUBJECT SHARPENING (FACE & TEXTURE RESTORATION) ----
    # Main subject/face ko HD aur clear texture dene ke liye high sharpening tool
    sharpener = ImageEnhance.Sharpness(pil_img)
    sharpened_img = sharpener.enhance(2.5)  # Chehre aur baalon ke details ko sharp karna
    
    # ---- STEP 3: SMART LENS BLUR & EDGE PROTECTION ----
    # Background ke liye deep lens-like blur texture create karna
    fully_blurred_img = sharpened_img.filter(ImageFilter.GaussianBlur(radius=12))
    
    # Depth map ko blend mask mein badalna
    mask = Image.fromarray(depth_map).convert("L")
    
    # Invert mask taaki background smoothly blur ho aur foreground (subject) ke kinare sharp rahein
    mask_inverted = Image.eval(mask, lambda x: 255 - x) 
    
    # Dono layers ko seamlessly merge karna taaki edges kharab na ho (Cut-Paste look nahi aayega)
    final_blend = Image.composite(fully_blurred_img, sharpened_img, mask_inverted)
    
    # ---- STEP 4: GRAIN MATCHING FOR REALISM ----
    # Foreground aur background ko aapas mein ek jaisa blend karne ke liye halka grain add karna
    blend_np = np.array(final_blend)
    
    # Mild uniform noise generate karna jo digital photography jaisa dikhe
    noise = np.random.normal(0, 4, blend_np.shape).astype(np.uint8) 
    real_hd_img = cv2.add(blend_np, noise)
    
    # Final Result Save karna
    output_rgb = cv2.cvtColor(real_hd_img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, output_rgb)
    print("Photo complete process ho gayi!")
    
