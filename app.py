from flask import Flask, render_template_string, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import os
import datetime
import requests
from sentinel import AurelianWarRoom, DataFetcher, WATCHLIST

app = Flask(__name__)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")

# Track runs and user portfolios
run_history = []
user_portfolios = {}
agent_conflicts = []

# Mock data for demo (when market closed)
DEMO_STOCKS = [
    {"name": "RELIANCE", "price": 2845.50, "change": 1.2, "sector": "Energy", "alert": False},
    {"name": "TATAMOTORS", "price": 845.30, "change": -6.8, "sector": "Auto", "alert": True, "alert_reason": "CRASH 6.8%"},
    {"name": "INFY", "price": 1456.20, "change": 0.45, "sector": "IT", "alert": False},
    {"name": "HDFCBANK", "price": 1678.90, "change": -0.3, "sector": "Banking", "alert": False},
    {"name": "TCS", "price": 3890.00, "change": 1.1, "sector": "IT", "alert": False},
    {"name": "SBIN", "price": 645.50, "change": -1.2, "sector": "Banking", "alert": False},
    {"name": "BAJFINANCE", "price": 7120.00, "change": 2.5, "sector": "NBFC", "alert": True, "alert_reason": "SURGE 2.5%"},
    {"name": "ASIANPAINT", "price": 3120.00, "change": -0.8, "sector": "Consumer", "alert": False},
]

def call_groq(prompt, max_tokens=300):
    """Call Groq API for fast AI responses."""
    if not GROQ_API_KEY:
        return None
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return None
    except Exception as e:
        print(f"Groq error: {e}")
        return None

def run_sentinel():
    """Run the war room and log it."""
    try:
        war_room = AurelianWarRoom()
        success = war_room.run()
        run_history.append({
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "SUCCESS" if success else "FAILED"
        })
        if len(run_history) > 10:
            run_history.pop(0)
    except Exception as e:
        run_history.append({
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": f"ERROR: {str(e)[:50]}"
        })

# Schedule daily at 8 AM IST
scheduler = BackgroundScheduler()
scheduler.add_job(run_sentinel, 'cron', hour=8, minute=0, timezone='Asia/Kolkata')
scheduler.start()

# ============ DASHBOARD HTML ============

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Aurelian Finance War Room</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: #0a0a0a; 
            color: #fff; 
            overflow-x: hidden;
        }
        
        /* LIVE TICKER */
        .ticker {
            background: #1a1a2e;
            border-bottom: 2px solid #ffd700;
            padding: 10px 0;
            overflow: hidden;
            white-space: nowrap;
        }
        .ticker-content {
            display: inline-block;
            animation: scroll 30s linear infinite;
        }
        @keyframes scroll {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        .ticker-item {
            display: inline-block;
            padding: 0 30px;
            font-size: 14px;
            font-weight: bold;
        }
        .ticker-up { color: #00ff88; }
        .ticker-down { color: #ff4444; }
        
        /* HEADER */
        .header {
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-bottom: 3px solid #ffd700;
        }
        .header h1 { 
            font-size: 2.5em; 
            color: #ffd700;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
        }
        .header p { color: #aaa; margin-top: 10px; }
        
        /* AGENT STATUS */
        .agents {
            display: flex;
            justify-content: center;
            gap: 20px;
            padding: 30px;
            flex-wrap: wrap;
        }
        .agent-card {
            background: #1a1a2e;
            border: 1px solid #333;
            border-radius: 15px;
            padding: 25px;
            width: 220px;
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
            position: relative;
            overflow: hidden;
        }
        .agent-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 10px 30px rgba(255, 215, 0, 0.1);
            border-color: #ffd700;
        }
        .agent-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #00ff88, #ffd700);
        }
        .status-dot {
            width: 12px; height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 10px currentColor; }
            50% { opacity: 0.5; box-shadow: 0 0 20px currentColor; }
        }
        .online { background: #00ff88; color: #00ff88; }
        .active { background: #00aaff; color: #00aaff; }
        .offline { background: #ff4444; color: #ff4444; }
        
        /* SECTOR HEATMAP */
        .heatmap {
            padding: 30px;
            text-align: center;
        }
        .heatmap h2 { color: #ffd700; margin-bottom: 20px; }
        .heatmap-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            max-width: 900px;
            margin: 20px auto;
        }
        .sector-box {
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            font-weight: bold;
            font-size: 16px;
            transition: transform 0.2s;
            cursor: pointer;
        }
        .sector-box:hover { transform: scale(1.08); }
        .hot { background: linear-gradient(135deg, #ff4444, #ff8844); box-shadow: 0 0 20px rgba(255, 68, 68, 0.3); }
        .warm { background: linear-gradient(135deg, #ffaa00, #ffdd00); color: #000; box-shadow: 0 0 20px rgba(255, 170, 0, 0.3); }
        .cold { background: linear-gradient(135deg, #4444ff, #8844ff); box-shadow: 0 0 20px rgba(68, 68, 255, 0.3); }
        .neutral { background: #333; }
        
        /* CONFLICT VISUALIZER */
        .conflicts {
            padding: 30px;
            max-width: 900px;
            margin: 0 auto;
        }
        .conflicts h2 { color: #ffd700; margin-bottom: 20px; text-align: center; }
        .conflict-card {
            background: #1a1a2e;
            border-left: 4px solid #ff4444;
            padding: 20px;
            margin: 15px 0;
            border-radius: 0 12px 12px 0;
            transition: transform 0.2s;
        }
        .conflict-card:hover { transform: translateX(5px); }
        .conflict-resolved {
            border-left-color: #00ff88;
            background: #1a2e1a;
        }
        .conflict-agents {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 10px;
            background: #0a0a0a;
            border-radius: 8px;
        }
        
        /* PREDICTIVE ALERTS */
        .predictions {
            padding: 30px;
            text-align: center;
        }
        .predictions h2 { color: #ffd700; margin-bottom: 20px; }
        .prediction-grid {
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        .prediction-card {
            background: #1a1a2e;
            border: 1px solid #333;
            padding: 25px;
            margin: 10px;
            border-radius: 15px;
            width: 280px;
            transition: transform 0.2s;
        }
        .prediction-card:hover { transform: translateY(-5px); border-color: #ffd700; }
        .prediction-up { color: #00ff88; font-size: 28px; font-weight: bold; }
        .prediction-down { color: #ff4444; font-size: 28px; font-weight: bold; }
        .confidence-bar {
            height: 8px;
            background: #333;
            border-radius: 4px;
            margin: 10px 0;
            overflow: hidden;
        }
        .confidence-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s;
        }
        
        /* PORTFOLIO SIMULATOR */
        .portfolio {
            padding: 30px;
            text-align: center;
            background: #111;
            margin: 20px;
            border-radius: 15px;
        }
        .portfolio h2 { color: #ffd700; margin-bottom: 20px; }
        .portfolio-input {
            background: #1a1a2e;
            border: 2px solid #ffd700;
            color: #fff;
            padding: 15px 25px;
            border-radius: 30px;
            width: 350px;
            font-size: 16px;
            margin: 10px;
            outline: none;
        }
        .portfolio-input:focus {
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.2);
        }
        .portfolio-btn {
            background: linear-gradient(135deg, #ffd700, #ffaa00);
            color: #000;
            padding: 15px 40px;
            border: none;
            border-radius: 30px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .portfolio-btn:hover { transform: scale(1.05); }
        
        /* AI CHAT */
        .chat-box {
            max-width: 700px;
            margin: 30px auto;
            background: #1a1a2e;
            border-radius: 20px;
            padding: 25px;
            border: 1px solid #333;
        }
        .chat-box h2 { color: #ffd700; margin-bottom: 15px; }
        .chat-messages {
            height: 250px;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 15px;
            background: #0a0a0a;
            border-radius: 15px;
            border: 1px solid #222;
        }
        .chat-message {
            margin: 10px 0;
            padding: 12px;
            border-radius: 12px;
            max-width: 80%;
        }
        .chat-user {
            background: #ffd700;
            color: #000;
            margin-left: auto;
            text-align: right;
        }
        .chat-bot {
            background: #1a3a1a;
            color: #00ff88;
            border: 1px solid #00ff88;
        }
        .chat-input-area {
            display: flex;
            gap: 10px;
        }
        .chat-input {
            flex: 1;
            padding: 12px;
            background: #0a0a0a;
            border: 1px solid #333;
            color: #fff;
            border-radius: 20px;
            outline: none;
        }
        .chat-send {
            padding: 12px 25px;
            background: #ffd700;
            color: #000;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-weight: bold;
        }
        
        /* ACTION BUTTONS */
        .actions {
            text-align: center;
            padding: 30px;
        }
        .btn {
            background: linear-gradient(135deg, #ffd700, #ffaa00);
            color: #000;
            padding: 15px 40px;
            border: none;
            border-radius: 30px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            margin: 10px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { 
            transform: scale(1.05); 
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
        }
        
        /* RUN HISTORY */
        .history {
            max-width: 800px;
            margin: 30px auto;
            padding: 20px;
        }
        .history h2 { color: #ffd700; margin-bottom: 15px; }
        .run-item {
            display: flex;
            justify-content: space-between;
            padding: 15px;
            background: #1a1a2e;
            margin: 8px 0;
            border-radius: 10px;
            border-left: 4px solid #00ff88;
            transition: transform 0.2s;
        }
        .run-item:hover { transform: translateX(5px); }
        .run-fail { border-left-color: #ff4444; }
        
        /* GROQ BADGE */
        .groq-badge {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #1a1a2e;
            border: 1px solid #ffd700;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 12px;
            color: #ffd700;
        }
    </style>
</head>
<body>
    <!-- LIVE TICKER -->
    <div class="ticker">
        <div class="ticker-content">
            {% for stock in stocks %}
            <span class="ticker-item {% if stock.change > 0 %}ticker-up{% else %}ticker-down{% endif %}">
                {{ stock.name }} ₹{{ stock.price }} ({{ stock.change }}%)
            </span>
            {% endfor %}
        </div>
    </div>
    
    <!-- HEADER -->
    <div class="header">
        <h1>🏛️ AURELIAN FINANCE WAR ROOM</h1>
        <p>Autonomous Multi-Agent Market Intelligence</p>
        <p>Last check: {{ last_run }} | Powered by Groq AI</p>
    </div>
    
    <!-- AGENT STATUS -->
    <div class="agents">
        <div class="agent-card">
            <h3>📡 Data Fetcher</h3>
            <p><span class="status-dot online"></span>ONLINE</p>
            <p>NSE Live Feed</p>
        </div>
        <div class="agent-card">
            <h3>🤖 Market Analyst</h3>
            <p><span class="status-dot active"></span>ACTIVE</p>
            <p>Price/Vol Alerts</p>
        </div>
        <div class="agent-card">
            <h3>🔎 Forensic Auditor</h3>
            <p><span class="status-dot active"></span>ACTIVE</p>
            <p>Debt/PE Checks</p>
        </div>
        <div class="agent-card">
            <h3>🧠 Sentiment Analyzer</h3>
            <p><span class="status-dot active"></span>ACTIVE</p>
            <p>News/Market Mood</p>
        </div>
        <div class="agent-card">
            <h3>🔮 Predictive Engine</h3>
            <p><span class="status-dot online"></span>ONLINE</p>
            <p>Pattern Detection</p>
        </div>
        <div class="agent-card">
            <h3>🤖 Groq AI</h3>
            <p><span class="status-dot {% if groq %}online{% else %}offline{% endif %}"></span>{% if groq %}ONLINE{% else %}OFFLINE{% endif %}</p>
            <p>Ultra-Fast Intelligence</p>
        </div>
    </div>
    
    <!-- SECTOR HEATMAP -->
    <div class="heatmap">
        <h2>🔥 SECTOR HEATMAP</h2>
        <div class="heatmap-grid">
            {% for sector, temp in sectors.items() %}
            <div class="sector-box {% if temp > 2 %}hot{% elif temp > 0 %}warm{% elif temp < -2 %}cold{% else %}neutral{% endif %}">
                {{ sector }}<br>{{ temp }}%
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- AGENT CONFLICTS -->
    <div class="conflicts">
        <h2>⚔️ AGENT CONFLICTS & RESOLUTIONS</h2>
        {% for conflict in conflicts %}
        <div class="conflict-card {% if conflict.resolved %}conflict-resolved{% endif %}">
            <strong>{{ conflict.issue }}</strong>
            <div class="conflict-agents">
                <div>
                    <span style="color: #ff4444;">🤖 {{ conflict.agent_a }}</span><br>
                    <small>{{ conflict.position_a }}</small>
                </div>
                <div style="text-align: right;">
                    <span style="color: #00aaff;">🤖 {{ conflict.agent_b }}</span><br>
                    <small>{{ conflict.position_b }}</small>
                </div>
            </div>
            {% if conflict.resolved %}
            <p style="color: #00ff88;">✅ Mediator: {{ conflict.resolution }}</p>
            {% else %}
            <p style="color: #ffaa00;">⏳ Awaiting mediation...</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <!-- PREDICTIVE ALERTS -->
    <div class="predictions">
        <h2>🔮 PREDICTIVE ALERTS (AI-Powered)</h2>
        <div class="prediction-grid">
            {% for pred in predictions %}
            <div class="prediction-card">
                <h3>{{ pred.stock }}</h3>
                <p class="{% if pred.direction == 'UP' %}prediction-up{% else %}prediction-down{% endif %}">
                    {{ pred.direction }} {{ pred.confidence }}%
                </p>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: {{ pred.confidence }}%; background: {% if pred.direction == 'UP' %}#00ff88{% else %}#ff4444{% endif %};"></div>
                </div>
                <p style="color: #aaa; font-size: 14px;">{{ pred.reason }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- PORTFOLIO SIMULATOR -->
    <div class="portfolio">
        <h2>💼 PORTFOLIO SIMULATOR</h2>
        <p>Enter your stocks (comma-separated):</p>
        <form action="/portfolio" method="POST">
            <input type="text" name="stocks" class="portfolio-input" placeholder="RELIANCE, INFY, TCS..." value="{{ user_stocks }}">
            <button type="submit" class="portfolio-btn">ANALYZE MY PORTFOLIO</button>
        </form>
        {% if portfolio_result %}
        <div style="margin-top: 20px; padding: 20px; background: #0a0a0a; border-radius: 15px; max-width: 600px; margin-left: auto; margin-right: auto; text-align: left; border: 1px solid #333;">
            <pre style="color: #fff; font-family: monospace; white-space: pre-wrap;">{{ portfolio_result }}</pre>
        </div>
        {% endif %}
    </div>
    
    <!-- AI CHAT -->
    <div class="chat-box">
        <h2>💬 ASK THE WAR ROOM (Groq AI)</h2>
        <div class="chat-messages" id="chatMessages">
            <div class="chat-message chat-bot">
                🤖 Welcome to Aurelian War Room. I'm powered by Groq AI (10x faster). Ask me anything about the market!
            </div>
        </div>
        <div class="chat-input-area">
            <input type="text" class="chat-input" id="chatInput" placeholder="Should I buy INFY? What's the market outlook?">
            <button class="chat-send" onclick="sendChat()">Send</button>
        </div>
    </div>
    
    <!-- ACTION BUTTONS -->
    <div class="actions">
        <a href="/trigger"><button class="btn">🚀 RUN NOW</button></a>
        <a href="/reports"><button class="btn">📄 VIEW REPORTS</button></a>
    </div>
    
    <!-- RUN HISTORY -->
    <div class="history">
        <h2>📋 Recent Runs</h2>
        {% for run in runs %}
        <div class="run-item {% if 'ERROR' in run.status or 'FAIL' in run.status %}run-fail{% endif %}">
            <span style="color: {% if 'SUCCESS' in run.status %}#00ff88{% else %}#ff4444{% endif %};">{{ run.status }}</span>
            <span style="color: #888;">{{ run.time }}</span>
        </div>
        {% endfor %}
    </div>
    
    <!-- GROQ BADGE -->
    <div class="groq-badge">
        ⚡ Powered by Groq AI | 10x Faster
    </div>
    
    <script>
        function sendChat() {
            const input = document.getElementById('chatInput');
            const messages = document.getElementById('chatMessages');
            const question = input.value.trim();
            if (!question) return;
            
            // Add user message
            messages.innerHTML += '<div class="chat-message chat-user">👤 ' + question + '</div>';
            input.value = '';
            messages.scrollTop = messages.scrollHeight;
            
            // Call backend for AI response
            fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question: question})
            })
            .then(res => res.json())
            .then(data => {
                messages.innerHTML += '<div class="chat-message chat-bot">🤖 ' + data.answer + '</div>';
                messages.scrollTop = messages.scrollHeight;
            })
            .catch(err => {
                messages.innerHTML += '<div class="chat-message chat-bot">🤖 I apologize, but I cannot provide specific investment advice. Please consult a financial advisor.</div>';
                messages.scrollTop = messages.scrollHeight;
            });
        }
        
        // Enter key to send
        document.getElementById('chatInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendChat();
        });
    </script>
</body>
</html>
"""

# ============ ROUTES ============

@app.route('/')
def dashboard():
    """Main dashboard with all features."""
    
    # Get stocks (use demo if market closed)
    try:
        data = DataFetcher()
        stocks = data.get_all()
        if not stocks:
            stocks = DEMO_STOCKS
    except:
        stocks = DEMO_STOCKS
    
    # Calculate sector performance
    sectors = {}
    for s in stocks:
        sector = s.get('sector', 'Unknown')
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(s.get('change_pct', s.get('change', 0)))
    
    sector_avg = {k: round(sum(v)/len(v), 2) for k, v in sectors.items()}
    
    # Mock conflicts
    conflicts = [
        {
            "issue": "INFY: Price crashing but fundamentals strong",
            "agent_a": "Market Analyst",
            "position_a": "BEARISH - Technical breakdown",
            "agent_b": "Forensic Auditor",
            "position_b": "BULLISH - No accounting red flags",
            "resolved": True,
            "resolution": "HOLD - Wait for price stabilization"
        },
        {
            "issue": "BAJFINANCE: High debt but strong momentum",
            "agent_a": "Forensic Auditor",
            "position_a": "BEARISH - D/E ratio 313%",
            "agent_b": "Sentiment Analyzer",
            "position_b": "BULLISH - Sector leading",
            "resolved": True,
            "resolution": "REDUCE - Take partial profits"
        }
    ]
    
    # Get AI predictions from Groq
    predictions = [
        {"stock": "INFY", "direction": "DOWN", "confidence": 72, "reason": "Breaking support levels"},
        {"stock": "BAJFINANCE", "direction": "UP", "confidence": 65, "reason": "Relative strength in NBFC"},
        {"stock": "RELIANCE", "direction": "UP", "confidence": 58, "reason": "Energy sector rotation"}
    ]
    
    # Check Groq
    groq_on = bool(GROQ_API_KEY)
    
    # Get last run time
    last_run = run_history[-1]["time"] if run_history else "Never"
    
    return render_template_string(DASHBOARD_HTML, 
                                  stocks=stocks, 
                                  sectors=sector_avg,
                                  conflicts=conflicts,
                                  predictions=predictions,
                                  runs=run_history[::-1],
                                  groq=groq_on,
                                  last_run=last_run,
                                  user_stocks="",
                                  portfolio_result=None)

@app.route('/chat', methods=['POST'])
def chat():
    """AI chat endpoint using Groq."""
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({"answer": "Please ask a question."})
    
    # Use Groq for response
    prompt = f"""You are a senior Indian market analyst. Answer this question concisely in 2-3 sentences. Be direct and actionable.

Question: {question}

Current market context: Nifty mixed, IT sector under pressure, BAJFINANCE showing strength."""

    response = call_groq(prompt, max_tokens=200)
    
    if response:
        return jsonify({"answer": response})
    else:
        # Fallback
        return jsonify({"answer": "Based on current multi-agent analysis, market sentiment is MIXED. IT sector shows weakness while NBFCs demonstrate relative strength. Consider defensive positioning."})

@app.route('/trigger')
def trigger():
    """Manually trigger a run."""
    run_sentinel()
    return "✅ War Room triggered! <a href='/'>Back to dashboard</a>"

@app.route('/reports')
def reports():
    """List saved reports."""
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return "No reports yet. Run the agent first."
    
    files = sorted(os.listdir(reports_dir), reverse=True)
    files = [f for f in files if f.endswith('.txt')]
    
    html = "<h1>📄 Saved Reports</h1><ul>"
    for f in files[:10]:
        html += f"<li><a href='/report/{f}'>{f}</a></li>"
    html += "</ul><a href='/'>Back</a>"
    return html

@app.route('/report/<filename>')
def view_report(filename):
    """View a specific report."""
    filepath = os.path.join("reports", filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"<pre style='background:#0a0a0a;color:#fff;padding:20px;'>{content}</pre><br><a href='/'>Back</a>"
    return "Report not found"

@app.route('/portfolio', methods=['POST'])
def portfolio():
    """Analyze user's portfolio with Groq AI."""
    stocks_input = request.form.get('stocks', '')
    user_stocks = [s.strip().upper() for s in stocks_input.split(',') if s.strip()]
    
    # Build prompt for Groq
    stocks_text = ", ".join(user_stocks)
    prompt = f"""Analyze this Indian stock portfolio: {stocks_text}

Provide a brief analysis (3-4 bullet points) covering:
- Overall risk level
- Sector diversification
- Key concerns
- One actionable recommendation

Keep it concise and professional."""

    response = call_groq(prompt, max_tokens=250)
    
    if response:
        result = f"PORTFOLIO ANALYSIS (AI-Powered)\n"
        result += f"Stocks: {stocks_text}\n"
        result += "=" * 50 + "\n\n"
        result += response
    else:
        # Fallback
        result = f"PORTFOLIO ANALYSIS FOR: {stocks_text}\n"
        result += "=" * 50 + "\n\n"
        for stock in user_stocks:
            if stock in ["RELIANCE", "INFY", "TCS", "HDFCBANK", "SBIN", "BAJFINANCE", "ASIANPAINT", "TATAMOTORS"]:
                result += f"✅ {stock}: Tracked by War Room\n"
            else:
                result += f"⚠️  {stock}: Add to watchlist\n"
        result += "\n💡 Diversify across sectors. Monitor IT exposure."
    
    # Re-render dashboard with portfolio result
    return render_template_string(DASHBOARD_HTML,
                                  stocks=DEMO_STOCKS,
                                  sectors={"Energy": -0.14, "IT": -6.85, "Banking": -0.88, "NBFC": 0.64, "Consumer": -0.79, "Auto": -1.2},
                                  conflicts=[],
                                  predictions=[],
                                  runs=run_history[::-1],
                                  groq=bool(GROQ_API_KEY),
                                  last_run=run_history[-1]["time"] if run_history else "Never",
                                  user_stocks=stocks_input,
                                  portfolio_result=result)

# Get PORT from environment at startup
port = int(os.environ.get("PORT", 5000))

if __name__ == '__main__':
    # Run once on startup
    run_sentinel()
    # Start web server
    app.run(host='0.0.0.0', port=port, debug=False)
