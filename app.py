import os
import sqlite3
import threading
import random
from flask import Flask, request, jsonify, render_template_string
import telebot

# --- ENVIRONMENT VARIABLES ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL") # Railway डिप्लॉय के बाद मिलने वाला लिंक

# --- FLASK & BOT SETUP ---
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

# --- DATABASE SETUP (LOCAL) ---
def init_db():
    conn = sqlite3.connect('aviator.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (telegram_id INTEGER PRIMARY KEY, balance REAL)''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('aviator.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- HTML/FRONTEND CODE (EMBEDDED) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Live Aviator</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { margin: 0; padding: 0; background-color: #121212; color: #fff; font-family: Arial, sans-serif; overflow: hidden; }
        .header { display: flex; justify-content: space-between; padding: 15px; background: #000; font-size: 18px; border-bottom: 2px solid #333; }
        .wallet { color: #28a745; font-weight: bold; }
        #game-area { height: 40vh; background: #1a1a1a; display: flex; align-items: center; justify-content: center; flex-direction: column; border-bottom: 3px solid #ff3333; }
        #multiplier { font-size: 70px; font-weight: 900; }
        .waiting { color: #ffcc00; font-size: 24px !important; }
        .flying { color: #fff; }
        .crashed { color: #ff3333; }
        .controls { padding: 20px; text-align: center; }
        input { background: #000; border: 1px solid #444; color: #fff; padding: 15px; font-size: 20px; width: 50%; text-align: center; border-radius: 8px; margin-bottom: 15px; }
        button { background: #28a745; border: none; width: 80%; padding: 15px; font-size: 24px; color: #fff; font-weight: bold; border-radius: 8px; cursor: pointer; }
        button:disabled { background: #555; }
    </style>
</head>
<body>
    <div class="header">
        <div>LIVE ACCOUNT</div>
        <div class="wallet">₹<span id="balance">Loading...</span></div>
    </div>
    <div id="game-area">
        <div id="multiplier" class="waiting">CONNECTING...</div>
    </div>
    <div class="controls">
        <input type="number" id="betAmount" value="10" min="10">
        <button id="actionBtn">BET</button>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        let userId = tg.initDataUnsafe?.user?.id || 12345;
        let balance = 0;
        let isPlaying = false;
        let currentMultiplier = 1.00;
        let gameInterval;
        let betAmount = 0;

        const display = document.getElementById('multiplier');
        const btn = document.getElementById('actionBtn');
        const balanceDisplay = document.getElementById('balance');

        // Fetch & Refill Balance
        function syncBalance() {
            fetch('/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ telegram_id: userId })
            }).then(r => r.json()).then(data => {
                balance = data.balance;
                balanceDisplay.innerText = balance.toFixed(2);
            });
        }
        syncBalance();

        function runGame() {
            btn.disabled = true;
            display.className = "flying";
            currentMultiplier = 1.00;
            
            // Random Crash Logic (1 in 100 chance for 1000x)
            let crashPoint = (Math.floor(Math.random() * 100) === 1) ? 
                (Math.random() * (5000 - 1000) + 1000) : 
                (Math.random() * (30 - 1) + 1);

            gameInterval = setInterval(() => {
                currentMultiplier += 0.01 + (currentMultiplier * 0.005);
                if (currentMultiplier >= crashPoint) {
                    clearInterval(gameInterval);
                    display.innerText = "FLEW AWAY\\n" + crashPoint.toFixed(2) + "x";
                    display.className = "crashed";
                    btn.disabled = false;
                    btn.innerText = "BET";
                    isPlaying = false;
                    syncBalance(); // Force balance update on loss
                } else {
                    display.innerText = currentMultiplier.toFixed(2) + "x";
                }
            }, 50);
        }

        btn.addEventListener('click', () => {
            if (!isPlaying) {
                betAmount = parseFloat(document.getElementById('betAmount').value);
                if (betAmount < 10) return tg.showAlert("Min bet ₹10");
                if (betAmount > balance) return tg.showAlert("Low Balance");
                
                // Deduct locally and play
                balance -= betAmount;
                balanceDisplay.innerText = balance.toFixed(2);
                isPlaying = true;
                btn.innerText = "CASH OUT";
                runGame();
            } else {
                // Cashout logic
                clearInterval(gameInterval);
                let winAmount = betAmount * currentMultiplier;
                balance += winAmount;
                balanceDisplay.innerText = balance.toFixed(2);
                display.innerText = "WON ₹" + winAmount.toFixed(2);
                display.className = "waiting";
                btn.disabled = false;
                btn.innerText = "BET";
                isPlaying = false;
                
                // Update DB
                fetch('/api/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ telegram_id: userId, balance: balance })
                });
            }
        });
    </script>
</body>
</html>
"""

# --- WEB ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_CONTENT)

@app.route('/api/sync', methods=['POST'])
def sync_balance():
    data = request.json
    tid = data.get('telegram_id')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (tid,)).fetchone()
    
    if user is None:
        balance = 1000.0
        conn.execute('INSERT INTO users (telegram_id, balance) VALUES (?, ?)', (tid, balance))
    else:
        balance = user['balance']
        if balance < 10.0:  # Auto refill logic when under 10
            balance = 1000.0
            conn.execute('UPDATE users SET balance = ? WHERE telegram_id = ?', (balance, tid))
            
    conn.commit()
    conn.close()
    return jsonify({'balance': balance})

@app.route('/api/update', methods=['POST'])
def update_balance():
    data = request.json
    conn = get_db_connection()
    conn.execute('UPDATE users SET balance = ? WHERE telegram_id = ?', (data['balance'], data['telegram_id']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# --- BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not WEBAPP_URL:
        bot.send_message(message.chat.id, "Error: WEBAPP_URL is missing in server environment variables.")
        return
        
    markup = telebot.types.InlineKeyboardMarkup()
    btn = telebot.types.InlineKeyboardButton("✈️ PLAY NOW", web_app=telebot.types.WebAppInfo(url=WEBAPP_URL))
    markup.add(btn)
    bot.send_message(message.chat.id, "Welcome to Aviator. Click to play:", reply_markup=markup)

# --- EXECUTION ---
if __name__ == '__main__':
    # Start bot polling in a background thread
    threading.Thread(target=lambda: bot.polling(none_stop=True), daemon=True).start()
    
    # Start Flask Web Server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
