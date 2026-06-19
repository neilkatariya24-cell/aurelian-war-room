from flask import Flask, render_template_string, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import os
import datetime
import random
import json
from sentinel import AurelianWarRoom, DataFetcher, WATCHLIST

app = Flask(__name__)

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
            border-bottom: 2px solid #gold;
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
        }
        .ticker-up { color: #00ff88; }
        .ticker-down { color: #ff4444; }
        
        /* HEADER */
        .header {
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-bottom: 3px solid #gold;
        }
        .header h1 { 
            font-size: 2.5em; 
            background: linear-gradient(90deg, #gold, #fff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
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
            transition: transform 0.3s;
            position: relative;
            overflow: hidden;
        }
        .agent-card:hover { transform: translateY(-5px); border-color: #gold; }
        .agent-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #00ff88, #gold);
        }
        .status-dot {
            width: 12px; height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .online { background: #00ff88; }
        .active { background: #00aaff; }
        
        /* SECTOR HEATMAP */
        .heatmap {
            padding: 30px;
            text-align: center;
        }
        .heatmap-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            max-width: 800px;
            margin: 20px auto;
        }
        .sector-box {
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-weight: bold;
            transition: transform 0.2s;
        }
        .sector-box:hover { transform: scale(1.05); }
        .hot { background: linear-gradient(135deg, #ff4444, #ff8844); }
        .warm { background: linear-gradient(135deg, #ffaa00, #ffdd00); color: #000; }
        .cold { background: linear-gradient(135deg, #4444ff, #8844ff); }
        .neutral { background: #333; }
        
        /* CONFLICT VISUALIZER */
        .conflicts {
            padding: 30px;
            max-width: 900px;
            margin: 0 auto;
        }
        .conflict-card {
            background: #1a1a2e;
            border-left: 4px solid #ff4444;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 10px 10px 0;
        }
        .conflict-resolved {
            border-left-color: #00ff88;
        }
        
        /* PORTFOLIO SIMULATOR */
        .portfolio {
            padding: 30px;
            text-align: center;
        }
        .portfolio-input {
            background: #1a1a2e;
            border: 1px solid #gold;
            color: #fff;
            padding: 12px 20px;
            border-radius: 25px;
            width: 300px;
            font-size: 16px;
            margin: 10px;
        }
        .portfolio-btn {
            background: linear-gradient(135deg, #gold, #ffaa00);
            color: #000;
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        
        /* CHAT INTERFACE */
        .chat-box {
            max-width: 600px;
            margin: 30px auto;
            background: #1a1a2e;
            border-radius: 15px;
            padding: 20px;
            border: 1px solid #333;
        }
        .chat-messages {
            height: 200px;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 10px;
            background: #0a0a0a;
            border-radius: 10px;
        }
        .chat-input {
            width: 80%;
            padding: 10px;
            background: #0a0a0a;
            border: 1px solid #333;
            color: #fff;
            border-radius: 20px;
        }
        .chat-send {
            width: 18%;
            padding: 10px;
            background: #gold;
            border: none;
            border-radius: 20px;
            cursor: pointer;
        }
        
        /* ACTION BUTTONS */
        .actions {
            text-align: center;
            padding: 30px;
        }
        .btn {
            background: linear-gradient(135deg, #gold, #ffaa00);
            color: #000;
            padding: 15px 40px;
            border: none;
            border-radius: 30px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            margin: 10px;
            transition: transform 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        
        /* RUN HISTORY */
        .history {
            max-width: 800px;
            margin: 30px auto;
            padding: 20px;
        }
        .run-item {
            display: flex;
            justify-content: space-between;
            padding: 12px;
            background: #1a1a2e;
            margin: 5px 0;
            border-radius: 8px;
            border-left: 3px solid #00ff88;
        }
        
        /* PREDICTIVE ALERTS */
        .predictions {
            padding: 30px;
            text-align: center;
        }
        .prediction-card {
            display: inline-block;
            background: #1a1a2e;
            border: 1px solid #gold;
            padding: 20px;
            margin: 10px;
            border-radius: 15px;
            width: 250px;
        }
        .prediction-up { color: #00ff88; font-size: 24px; }
        .prediction-down { color: #ff4444; font-size: 24px; }
    </style>
</head>
<body>
    <!-- LIVE TICKER -->
    <div class="ticker">
        <div class="ticker-content">
            {% for stock in stocks %}
            <span class="ticker-item {% if stock.change > 0 %}ticker-up{% else %}ticker-down{% endif %}">
                {{ stock.name }} {{ stock.price }} ({{ stock.change }}%)
            </span>
            {% endfor %}
        </div>
    </div>
    
    <!-- HEADER -->
    <div class="header">
        <h1>🏛️ AURELIAN FINANCE WAR ROOM</h1>
        <p>Autonomous Multi-Agent Market Intelligence</p>
        <p>Last check: {{ last_run }}</p>
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
            <h3>🤖 Claude AI</h3>
            <p><span class="status-dot {% if claude %}online{% else %}offline{% endif %}"></span>{% if claude %}ONLINE{% else %}OFFLINE{% endif %}</p>
            <p>Smart Summaries</p>
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
            <strong>{{ conflict.issue }}</strong><br>
            🤖 {{ conflict.agent_a }}: {{ conflict.position_a }}<br>
            🤖 {{ conflict.agent_b }}: {{ conflict.position_b }}<br>
            {% if conflict.resolved %}
            ✅ Mediator: {{ conflict.resolution }}
            {% else %}
            ⏳ Awaiting mediation...
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <!-- PREDICTIVE ALERTS -->
    <div class="predictions">
        <h2>🔮 PREDICTIVE ALERTS</h2>
        {% for pred in predictions %}
        <div class="prediction-card">
            <h3>{{ pred.stock }}</h3>
            <p class="{% if pred.direction == 'UP' %}prediction-up{% else %}prediction-down{% endif %}">
                {{ pred.direction }} {{ pred.confidence }}%
            </p>
            <p>{{ pred.reason }}</p>
        </div>
        {% endfor %}
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
        <div style="margin-top: 20px; padding: 20px; background: #1a1a2e; border-radius: 15px; max-width: 600px; margin-left: auto; margin-right: auto;">
            <h3>Your Portfolio Analysis</h3>
            <pre style="text-align: left; color: #fff;">{{ portfolio_result }}</pre>
        </div>
        {% endif %}
    </div>
    
    <!-- AI CHAT -->
    <div class="chat-box">
        <h2>💬 ASK THE WAR ROOM</h2>
        <div class="chat-messages" id="chatMessages">
            <p style="color: #888;">🤖 Welcome to Aurelian War Room. Ask me anything about the market.</p>
        </div>
        <input type="text" class="chat-input" id="chatInput" placeholder="Should I buy INFY?">
        <button class="chat-send" onclick="sendChat()">Send</button>
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
        <div class="run-item">
            <span class="{% if 'SUCCESS' in run.status %}online{% else %}red{% endif %}">{{ run.status }}</span>
            <span>{{ run.time }}</span>
        </div>
        {% endfor %}
    </div>
    
    <script>
        function sendChat() {
            const input = document.getElementById('chatInput');
            const messages = document.getElementById('chatMessages');
            const question = input.value;
            if (!question) return;
            
            messages.innerHTML += '<p style="color: #gold;">👤 ' + question + '</p>';
            input.value = '';
            
            // Simple responses (in real app, call Claude API)
            setTimeout(() => {
                let response = "🤖 I'm analyzing that...";
                if (question.toLowerCase().includes('infy')) {
                    response = "🤖 INFY is showing bearish signals. The Forensic Auditor detected high volatility. Consider waiting for support levels.";
                } else if (question.toLowerCase().includes('buy')) {
                    response = "🤖 The Market Analyst suggests defensive positioning. BAJFINANCE shows relative strength. DYOR.";
                } else {
                    response = "🤖 Based on current multi-agent analysis, market sentiment is MIXED. Monitor IT sector closely.";
                }
                messages.innerHTML += '<p style="color: #00ff88;">' + response + '</p>';
                messages.scrollTop = messages.scrollHeight;
            }, 1000);
        }
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
    
    # Mock conflicts (in real app, from sentinel)
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
    
    # Mock predictions
    predictions = [
        {"stock": "INFY", "direction": "DOWN", "confidence": 72, "reason": "Breaking support levels"},
        {"stock": "BAJFINANCE", "direction": "UP", "confidence": 65, "reason": "Relative strength in NBFC"},
        {"stock": "RELIANCE", "direction": "UP", "confidence": 58, "reason": "Energy sector rotation"}
    ]
    
    # Check Claude
    claude_on = bool(os.getenv("CLAUDE_API_KEY", ""))
    
    # Get last run time
    last_run = run_history[-1]["time"] if run_history else "Never"
    
    return render_template_string(DASHBOARD_HTML, 
                                  stocks=stocks, 
                                  sectors=sector_avg,
                                  conflicts=conflicts,
                                  predictions=predictions,
                                  runs=run_history[::-1],
                                  claude=claude_on,
                                  last_run=last_run,
                                  user_stocks="",
                                  portfolio_result=None)

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
    """Analyze user's portfolio."""
    stocks_input = request.form.get('stocks', '')
    user_stocks = [s.strip().upper() for s in stocks_input.split(',') if s.strip()]
    
    # Mock analysis
    result = f"PORTFOLIO ANALYSIS FOR: {', '.join(user_stocks)}\n"
    result += "=" * 50 + "\n\n"
    
    for stock in user_stocks:
        if stock in ["RELIANCE", "INFY", "TCS", "HDFCBANK", "SBIN", "BAJFINANCE", "ASIANPAINT", "TATAMOTORS"]:
            result += f"✅ {stock}: Found in watchlist\n"
            # Add mock analysis
            if stock in ["INFY", "TCS"]:
                result += f"   ⚠️  IT sector under pressure. Consider hedging.\n"
            elif stock in ["BAJFINANCE"]:
                result += f"   🚀 Strong momentum but watch debt levels.\n"
            else:
                result += f"   ✅ Stable. Hold position.\n"
        else:
            result += f"❌ {stock}: Not in current watchlist. Add to tracking.\n"
        result += "\n"
    
    result += "💡 RECOMMENDATION: Diversify across sectors. Monitor IT exposure."
    
    # Re-render dashboard with portfolio result
    return render_template_string(DASHBOARD_HTML,
                                  stocks=DEMO_STOCKS,
                                  sectors={"Energy": -0.14, "IT": -6.85, "Banking": -0.88, "NBFC": 0.64, "Consumer": -0.79, "Auto": -1.2},
                                  conflicts=[],
                                  predictions=[],
                                  runs=run_history[::-1],
                                  claude=bool(os.getenv("CLAUDE_API_KEY", "")),
                                  last_run=run_history[-1]["time"] if run_history else "Never",
                                  user_stocks=stocks_input,
                                  portfolio_result=result)

if __name__ == '__main__':
    # Run once on startup
    run_sentinel()
    # Start web server
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
