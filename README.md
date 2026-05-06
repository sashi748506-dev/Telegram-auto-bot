# 📸 Photo Enhancer Telegram Bot
### Step-by-Step Setup Guide (Hindi)

---

## 🗂️ Files aur unke kaam

| File | Kaam |
|------|------|
| `bot.py` | Main bot — Telegram se baat karta hai |
| `image_processor.py` | Saare photo effects ka engine |
| `requirements.txt` | Python libraries list |
| `Procfile` | Server ko batata hai kya chalana hai |
| `.env.example` | Environment variables ka template |

---

## 🧠 Bot kya kya karta hai?

1. **Subject Detection** — AI (U2Net) se pata lagata hai ki photo me kya main subject hai
2. **Subject Sharpening** — Subject ko razor-sharp karta hai
3. **Depth-based Blur** — Background me distance ke hisaab se blur (paas = kam blur, door = zyada blur)
4. **Lens Bokeh** — DSLR camera jaisa circular bokeh effect
5. **Edge Protection** — Subject aur background ke beech ki line clean rakhi jaati hai
6. **HD Enhancement** — CLAHE se local contrast boost + color vibrancy
7. **Grain Matching** — Realistic film grain (shadows me zyada, highlights me kam)

---

## 🚀 STEP 1 — Telegram Bot Token Banao (Free)

1. Telegram pe `@BotFather` search karo
2. `/newbot` type karo
3. Bot ka naam do (e.g., `My Photo Enhancer`)
4. Username do (e.g., `myphotoenhancer_bot`)
5. BotFather ek **token** dega — ise copy karke rakho
   ```
   1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
6. Bot ki privacy settings ke liye:
   - `/mybots` → apna bot → Bot Settings → Group Privacy → Turn OFF

---

## 💻 STEP 2 — GitHub Pe Code Upload Karo (Free)

1. **github.com** pe account banao (free)
2. "New Repository" click karo
3. Naam rakho: `photo-enhancer-bot`
4. Public rakho (free hosting ke liye zaroori)
5. "Add file" → "Upload files" → Ye 5 files upload karo:
   - `bot.py`
   - `image_processor.py`
   - `requirements.txt`
   - `Procfile`
   - `.env.example` (iska naam badlo `.env.example` hi rakho — token yahan mat dalo)
6. "Commit changes" click karo

---

## 🌐 STEP 3 — Free Server Pe Deploy Karo

### 🥇 BEST OPTION: Koyeb (Sabse achha free option)
**Kyun?** — 24/7 chalta hai, kabhi nahi sota, free me 2 services

1. **koyeb.com** pe jaao — GitHub se login karo
2. "Create Service" → "GitHub" select karo
3. Apna `photo-enhancer-bot` repo choose karo
4. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Run command:** `python bot.py`
   - **Instance type:** `nano` (free)
5. "Environment Variables" section me:
   - Key: `BOT_TOKEN`
   - Value: apna token paste karo
6. "Deploy" click karo — Done! ✅

### 🥈 ALTERNATIVE: Render.com (Also free)
**Note:** 15 min inactive rehne ke baad sota hai — photo bhejne pe 30 sec lag sakte hain

1. **render.com** pe GitHub se login karo
2. "New" → "Web Service"
3. Apna repo connect karo
4. Settings:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
   - **Instance type:** Free
5. "Environment Variables" me `BOT_TOKEN` add karo
6. "Create Web Service" — Done! ✅

**Render Free Tip:** UptimeRobot (free) se apni service ka URL ping karao har 14 min me — service kabhi nahi soegi!

---

## 📱 STEP 4 — Mobile Pe Test Karo

1. Telegram kholo
2. Apna bot search karo (username se)
3. `/start` bhejo
4. Koi bhi photo bhejo
5. 20-40 second wait karo
6. Enhanced HD photo mil jayegi! 🎉

---

## ⚡ STEP 5 — Sab Kuch Off Ho Jaye Toh Bhi Chalega?

**Haan! Isliye hum server pe deploy kar rahe hain.**

- Koyeb/Render ke servers 24/7 chalte hain
- Tumhara mobile band ho, internet na ho — bot chalta rahega
- Koi bhi tumhara bot use kar sakta hai

---

## 🔧 Local Testing (Optional — PC pe test karne ke liye)

```bash
# Python install hona chahiye (3.9+)

# Folder banao
mkdir photo-enhancer-bot
cd photo-enhancer-bot

# Files copy karo

# Libraries install karo
pip install -r requirements.txt

# Token set karo (Windows)
set BOT_TOKEN=your_token_here

# Token set karo (Linux/Mac)
export BOT_TOKEN=your_token_here

# Bot chalao
python bot.py
```

---

## ❓ Common Problems

| Problem | Solution |
|---------|----------|
| Bot respond nahi kar raha | Token sahi hai? Koyeb/Render me deploy hua? |
| "rembg" error | `pip install rembg onnxruntime` chalao |
| Photo bahut slow process ho rahi | Normal hai — AI model 20-40 sec leta hai |
| Model download ho raha pehli baar | U2Net model (~170MB) ek baar download hota hai |
| Memory error on server | Koyeb pe nano se micro instance upgrade karo |

---

## 🆓 Free Limits

| Service | Limit |
|---------|-------|
| Telegram Bot API | Unlimited (free) |
| Koyeb nano | 512MB RAM, 0.1 vCPU — enough for bot |
| GitHub | Unlimited public repos |
| rembg/U2Net | Completely free, local model |

---

## 📈 Future Upgrades (Jab chahein)

- [ ] Super Resolution (Real-ESRGAN via Replicate API — 100 free calls/day)
- [ ] Denoising (DeepAI API — 100 free/day)
- [ ] Face Enhancement (GFPGAN)
- [ ] Background Replacement

---

*Bot banake share karna mat bhoolna! 🎉*
