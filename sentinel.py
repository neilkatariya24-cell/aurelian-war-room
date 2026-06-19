#!/usr/bin/env python3
"""
AURELIAN MARKET SENTINEL v2.0
CRAZY MODE - Multi-Agent Finance Intelligence
"""

import os
import sys
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
load_dotenv()

import requests
import yfinance as yf

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
EMAIL_USER = "neilkatariya24@gmail.com"
EMAIL_PASS = "zfgz zjxq zswo wdgl"

WATCHLIST = {
    "RELIANCE.NS": {"sector": "Energy", "weight": 10},
    "TATAMOTORS.NS": {"sector": "Auto", "weight": 8},
    "INFY.NS": {"sector": "IT", "weight": 9},
    "HDFCBANK.NS": {"sector": "Banking", "weight": 10},
    "TCS.NS": {"sector": "IT", "weight": 9},
    "SBIN.NS": {"sector": "Banking", "weight": 8},
    "BAJFINANCE.NS": {"sector": "NBFC", "weight": 7},
    "ASIANPAINT.NS": {"sector": "Consumer", "weight": 7},
}

PRICE_MOVE_THRESHOLD = 3.0
VOLUME_SPIKE_THRESHOLD = 2.0

# ============ LOGGING ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AurelianSentinel")

# ============ DATA FETCHER ============

class DataFetcher:
    """Fetches live market data."""
    
    def get_stock(self, ticker: str) -> Optional[Dict]:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="30d")
            
            if hist.empty or len(hist) < 2:
                return None
            
            current = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            change_pct = ((current - prev) / prev) * 100
            
            avg_volume = float(hist['Volume'].iloc[-20:].mean())
            today_volume = float(hist['Volume'].iloc[-1])
            volume_ratio = today_volume / avg_volume if avg_volume > 0 else 1.0
            
            week_ago = float(hist['Close'].iloc[-6]) if len(hist) >= 6 else float(hist['Close'].iloc[0])
            week_change = ((current - week_ago) / week_ago) * 100
            
            return {
                "ticker": ticker,
                "name": ticker.replace(".NS", ""),
                "price": round(current, 2),
                "change_pct": round(change_pct, 2),
                "volume_ratio": round(volume_ratio, 2),
                "week_change": round(week_change, 2),
                "sector": WATCHLIST.get(ticker, {}).get("sector", "Unknown"),
                "weight": WATCHLIST.get(ticker, {}).get("weight", 5),
                "alert": False,
                "alert_reasons": [],
                "verdict": "HOLD"
            }
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            return None
    
    def get_nifty(self) -> Optional[Dict]:
        try:
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="5d")
            if hist.empty or len(hist) < 2:
                return None
            current = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            return {
                "price": round(current, 2),
                "change_pct": round(((current - prev) / prev) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Failed to fetch Nifty: {e}")
            return None
    
    def get_all(self) -> List[Dict]:
        results = []
        for ticker in WATCHLIST.keys():
            data = self.get_stock(ticker)
            if data:
                results.append(data)
        return results

# ============ AGENT 1: MARKET ANALYST ============

class MarketAnalyst:
    """Analyzes price action and trends."""
    
    def analyze(self, stocks: List[Dict]) -> List[Dict]:
        for stock in stocks:
            alerts = []
            
            # Price move
            if abs(stock['change_pct']) > PRICE_MOVE_THRESHOLD:
                direction = "SURGE" if stock['change_pct'] > 0 else "CRASH"
                alerts.append(f"PRICE ALERT: {direction} {abs(stock['change_pct']):.1f}%")
                stock['verdict'] = "BULLISH" if stock['change_pct'] > 0 else "BEARISH"
            
            # Volume spike
            if stock['volume_ratio'] > VOLUME_SPIKE_THRESHOLD:
                alerts.append(f"VOLUME SPIKE: {stock['volume_ratio']:.1f}x normal")
            
            # Weekly trend
            if abs(stock['week_change']) > 10:
                direction = "surging" if stock['week_change'] > 0 else "declining"
                alerts.append(f"WEEKLY TREND: {direction} {abs(stock['week_change']):.1f}%")
            
            # Sector rotation signal
            if stock['change_pct'] > 5 and stock['volume_ratio'] > 1.5:
                alerts.append(f"MOMENTUM PLAY: Strong buying in {stock['sector']}")
                stock['verdict'] = "STRONG BUY"
            
            if stock['change_pct'] < -5 and stock['volume_ratio'] > 1.5:
                alerts.append(f"CAPITULATION: Heavy selling in {stock['sector']}")
                stock['verdict'] = "STRONG SELL"
            
            stock['alert'] = len(alerts) > 0
            stock['alert_reasons'] = alerts
        
        return stocks

# ============ AGENT 2: FORENSIC AUDITOR ============

class ForensicAuditor:
    """Checks financial health red flags."""
    
    def analyze(self, stocks: List[Dict]) -> List[Dict]:
        for stock in stocks:
            try:
                ticker = yf.Ticker(stock['ticker'])
                info = ticker.info
                
                # Check debt levels
                debt_to_equity = info.get('debtToEquity', 0)
                if debt_to_equity > 100:
                    stock['alert_reasons'].append(f"DEBT RISK: D/E ratio {debt_to_equity:.0f}%")
                    if stock['verdict'] == "HOLD":
                        stock['verdict'] = "BEARISH"
                
                # Check P/E ratio
                pe_ratio = info.get('trailingPE', 0)
                if pe_ratio > 40:
                    stock['alert_reasons'].append(f"VALUATION: P/E {pe_ratio:.0f}x (expensive)")
                elif pe_ratio < 10 and pe_ratio > 0:
                    stock['alert_reasons'].append(f"VALUE: P/E {pe_ratio:.0f}x (cheap)")
                
                # Check dividend
                dividend = info.get('dividendYield', 0)
                if dividend and dividend > 0.03:
                    stock['alert_reasons'].append(f"INCOME: Dividend yield {dividend*100:.1f}%")
                
            except Exception as e:
                pass  # Skip if data unavailable
        
        return stocks

# ============ AGENT 3: SENTIMENT ANALYZER ============

class SentimentAnalyzer:
    """Analyzes market sentiment and momentum."""
    
    def analyze(self, stocks: List[Dict], nifty: Optional[Dict]) -> Dict:
        # Market breadth
        gainers = [s for s in stocks if s['change_pct'] > 0]
        losers = [s for s in stocks if s['change_pct'] < 0]
        
        # Sector performance
        sectors = {}
        for s in stocks:
            sector = s['sector']
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(s['change_pct'])
        
        sector_avg = {k: sum(v)/len(v) for k, v in sectors.items()}
        best_sector = max(sector_avg, key=sector_avg.get)
        worst_sector = min(sector_avg, key=sector_avg.get)
        
        # Overall sentiment
        if nifty:
            if nifty['change_pct'] > 1 and len(gainers) > len(losers):
                sentiment = "BULLISH"
            elif nifty['change_pct'] < -1 and len(losers) > len(gainers):
                sentiment = "BEARISH"
            else:
                sentiment = "MIXED"
        else:
            sentiment = "UNKNOWN"
        
        return {
            "sentiment": sentiment,
            "gainers": len(gainers),
            "losers": len(losers),
            "best_sector": best_sector,
            "worst_sector": worst_sector,
            "sector_avg": sector_avg,
            "alerts": sum(1 for s in stocks if s['alert'])
        }

# ============ CLAUDE AI SUMMARY ============

class ClaudeSummary:
    """Generates AI-powered market intelligence."""
    
    def __init__(self):
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        self.enabled = bool(CLAUDE_API_KEY)
    
    def generate(self, stocks: List[Dict], nifty: Optional[Dict], sentiment: Dict) -> str:
        if not self.enabled:
            return self._fallback(stocks, sentiment)
        
        # Build data for Claude
        stocks_text = ""
        for s in stocks:
            emoji = "🔴" if s['change_pct'] < -3 else "🟢" if s['change_pct'] > 3 else "⚪"
            alert_text = " | ".join(s['alert_reasons']) if s['alert_reasons'] else "Normal"
            stocks_text += f"{emoji} {s['name']}: {s['change_pct']:+.2f}% | {s['verdict']} | {alert_text}\n"
        
        nifty_text = f"Nifty 50: {nifty['price']} ({nifty['change_pct']:+.2f}%)" if nifty else "Nifty data unavailable"
        
        prompt = f"""You are a legendary Indian hedge fund manager. Write a 4-sentence market brief for your portfolio.

MARKET: {nifty_text}
SENTIMENT: {sentiment['sentiment']} | {sentiment['gainers']} up, {sentiment['losers']} down
BEST SECTOR: {sentiment['best_sector']}
WORST SECTOR: {sentiment['worst_sector']}

STOCKS:
{stocks_text}

Write like a pro. One key insight. One actionable trade. No fluff. Use Indian market context (Rs, Nifty, sectors)."""

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['content'][0]['text'].strip()
            return self._fallback(stocks, sentiment)
        except Exception as e:
            logger.error(f"Claude failed: {e}")
            return self._fallback(stocks, sentiment)
    
    def _fallback(self, stocks: List[Dict], sentiment: Dict) -> str:
        alerted = [s for s in stocks if s['alert']]
        if alerted:
            names = ", ".join([s['name'] for s in alerted[:3]])
            return f"Alert: {names} showing unusual activity. Market sentiment: {sentiment['sentiment']}. Monitor closely."
        return f"Market {sentiment['sentiment']}. {sentiment['gainers']} gainers, {sentiment['losers']} losers. Hold positions."

# ============ REPORT GENERATOR ============

class ReportGenerator:
    """Creates professional reports."""
    
    def generate(self, stocks: List[Dict], nifty: Optional[Dict], sentiment: Dict, ai_summary: str) -> str:
        today = datetime.now().strftime("%b %d, %Y %H:%M IST")
        
        report = f"{'='*60}\n"
        report += f"🏛️  AURELIAN FINANCE WAR ROOM - INTELLIGENCE REPORT\n"
        report += f"📅  {today}\n"
        report += f"{'='*60}\n\n"
        
        # Market snapshot
        report += f"📊 MARKET SNAPSHOT\n"
        if nifty:
            emoji = "🟢" if nifty['change_pct'] >= 0 else "🔴"
            report += f"   Nifty 50: {nifty['price']:.0f} {emoji} {nifty['change_pct']:+.2f}%\n"
        report += f"   Sentiment: {sentiment['sentiment']}\n"
        report += f"   Breadth: {sentiment['gainers']} gainers | {sentiment['losers']} losers\n"
        report += f"   Alerts: {sentiment['alerts']}\n\n"
        
        # AI Summary
        report += f"🧠 AI INTELLIGENCE BRIEF\n"
        report += f"   {ai_summary}\n\n"
        
        # Sector Analysis
        report += f"🏭 SECTOR ROTATION\n"
        for sector, avg in sentiment['sector_avg'].items():
            emoji = "🟢" if avg > 1 else "🔴" if avg < -1 else "⚪"
            report += f"   {emoji} {sector}: {avg:+.2f}%\n"
        report += f"\n"
        
        # Stock Table
        report += f"📈 STOCK ANALYSIS\n"
        report += f"{'Stock':<12} {'Price':>10} {'Change':>8} {'Volume':>8} {'Verdict':<12} {'Alerts'}\n"
        report += f"{'-'*70}\n"
        
        for s in stocks:
            emoji = "🔴" if s['change_pct'] < -3 else "🟢" if s['change_pct'] > 3 else "⚪"
            vol = f"{s['volume_ratio']:.1f}x" if s['volume_ratio'] > 1 else "-"
            alert_count = len(s['alert_reasons'])
            alert_str = f"({alert_count})" if alert_count > 0 else ""
            report += f"{emoji} {s['name']:<10} {s['price']:>8.2f} {s['change_pct']:>+7.2f}% {vol:>8} {s['verdict']:<12} {alert_str}\n"
            
            # Show alert details
            for alert in s['alert_reasons']:
                report += f"      ⚠️  {alert}\n"
        
        report += f"\n{'='*60}\n"
        report += f"💡 ACTION ITEMS\n"
        
        # Generate action items
        strong_sells = [s for s in stocks if s['verdict'] == "STRONG SELL"]
        strong_buys = [s for s in stocks if s['verdict'] == "STRONG BUY"]
        bears = [s for s in stocks if s['verdict'] == "BEARISH"]
        bulls = [s for s in stocks if s['verdict'] == "BULLISH"]
        
        if strong_sells:
            report += f"   🚨 EXIT: {', '.join([s['name'] for s in strong_sells])}\n"
        if strong_buys:
            report += f"   🚀 BUY: {', '.join([s['name'] for s in strong_buys])}\n"
        if bears:
            report += f"   ⚠️  REDUCE: {', '.join([s['name'] for s in bears])}\n"
        if bulls:
            report += f"   ✅ HOLD: {', '.join([s['name'] for s in bulls])}\n"
        
        report += f"\n{'='*60}\n"
        report += f"🤖 Agents: MarketAnalyst | ForensicAuditor | SentimentAnalyzer | ClaudeAI\n"
        report += f"⏰ Generated: {datetime.now().strftime('%H:%M:%S IST')}\n"
        report += f"{'='*60}\n"
        
        return report

# ============ FILE SAVER ============

class FileSaver:
    """Saves reports to files."""
    
    def save(self, report: str):
        # Create reports folder
        if not os.path.exists("reports"):
            os.makedirs("reports")
        
        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/market_brief_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Report saved: {filename}")
        return filename
    
    def log_csv(self, stocks: List[Dict], sentiment: Dict):
        """Log to CSV for historical tracking."""
        csv_file = "reports/market_history.csv"
        
        # Create file with headers if doesn't exist
        if not os.path.exists(csv_file):
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Stock", "Price", "Change%", "Volume", "Verdict", "Sentiment", "Alerts"])
        
        # Append data
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for s in stocks:
                writer.writerow([
                    datetime.now().isoformat(),
                    s['name'],
                    s['price'],
                    s['change_pct'],
                    s['volume_ratio'],
                    s['verdict'],
                    sentiment['sentiment'],
                    len(s['alert_reasons'])
                ])
        
        logger.info("Historical data logged")

# ============ EMAIL SENDER ============

class EmailSender:
    """Sends reports via email."""
    
    def __init__(self):
        self.enabled = bool(EMAIL_USER and EMAIL_PASS)
    
    def send(self, report: str, subject: str = "Aurelian Market Brief"):
        if not self.enabled:
            logger.info("Email not configured - skipping")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USER
            msg['To'] = EMAIL_USER
            msg['Subject'] = f"{subject} - {datetime.now().strftime('%b %d, %H:%M')}"
            
            msg.attach(MIMEText(report, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
            server.quit()
            
            logger.info("Email sent successfully")
            return True
        except Exception as e:
            logger.error(f"Email failed: {e}")
            return False

# ============ MAIN ORCHESTRATOR ============

class AurelianWarRoom:
    """Main orchestrator - runs all agents."""
    
    def __init__(self):
        self.data = DataFetcher()
        self.analyst = MarketAnalyst()
        self.auditor = ForensicAuditor()
        self.sentiment = SentimentAnalyzer()
        self.claude = ClaudeSummary()
        self.reporter = ReportGenerator()
        self.saver = FileSaver()
        self.email = EmailSender()
    
    def run(self):
        logger.info("=" * 60)
        logger.info("AURELIAN WAR ROOM - INITIATING ALL AGENTS")
        logger.info("=" * 60)
        
        # Fetch data
        logger.info("📡 Fetching market data...")
        stocks = self.data.get_all()
        nifty = self.data.get_nifty()
        
        if not stocks:
            logger.error("❌ No data fetched")
            return False
        
        logger.info(f"✅ Got {len(stocks)} stocks")
        
        # Run agents
        logger.info("🤖 Deploying Market Analyst...")
        stocks = self.analyst.analyze(stocks)
        
        logger.info("🔎 Deploying Forensic Auditor...")
        stocks = self.auditor.analyze(stocks)
        
        logger.info("📊 Deploying Sentiment Analyzer...")
        sentiment = self.sentiment.analyze(stocks, nifty)
        
        logger.info("🧠 Generating AI Intelligence...")
        ai_summary = self.claude.generate(stocks, nifty, sentiment)
        
        # Generate report
        logger.info("📋 Compiling War Room Report...")
        report = self.reporter.generate(stocks, nifty, sentiment, ai_summary)
        
        # Print to console
        print("\n" + report)
        
        # Save to file
        logger.info("💾 Saving to file...")
        filename = self.saver.save(report)
        self.saver.log_csv(stocks, sentiment)
        
        # Send email
        logger.info("📧 Sending email...")
        self.email.send(report)
        
        logger.info("=" * 60)
        logger.info(f"✅ WAR ROOM COMPLETE - Report: {filename}")
        logger.info("=" * 60)
        
        return True

# ============ RUN ============

if __name__ == "__main__":
    AurelianWarRoom().run()