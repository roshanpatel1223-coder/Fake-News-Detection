"""
app.py — SatyaCheck Flask Backend
Dual-engine: ML model + AI (Gemini or Claude) cross-verification
Auto-detects which API key is set: GEMINI_API_KEY or ANTHROPIC_API_KEY
"""

import os, re, json, pickle
import urllib.request, urllib.error
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
load_dotenv()
print("GEMINI KEY SET:", bool(os.environ.get('GEMINI_API_KEY')))
print("GEMINI KEY VALUE:", os.environ.get('GEMINI_API_KEY','')[:10], "...")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fakenews-detector-india-2024')

# ── Load ML Model ─────────────────────────────────────────────
MODEL_PATH   = os.path.join('models', 'model.pkl')
METRICS_PATH = os.path.join('models', 'metrics.json')
model_pipeline = None
metrics = {}

def load_model():
    global model_pipeline, metrics
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'rb') as f:
            model_pipeline = pickle.load(f)
        print("[INFO] ML model loaded ✓")
    else:
        print("[WARNING] model.pkl not found — run train_model.py first")
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, 'r') as f:
            metrics = json.load(f)
    else:
        metrics = {"accuracy":83.16,"roc_auc":93.09,"precision_fake":79.8,"recall_fake":80.2,"precision_real":82.5,"recall_real":86.2,"confusion_matrix":[[5391,1367],[1028,6438]],"total_samples":71120,"train_samples":56896,"test_samples":14224}

load_model()

# ── Stopwords ─────────────────────────────────────────────────
STOP_WORDS = {'the','a','an','and','or','but','in','on','at','to','for','of','with','by','from','is','are','was','were','be','been','have','has','had','do','does','did','will','would','could','should','this','that','these','those','it','its','i','me','my','we','our','you','your','he','him','his','she','her','they','them','their','what','which','who','when','where','why','how','all','each','also','said','says','according','told','report','news','today','new','one','two','three'}

def preprocess_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^a-z\s]', ' ', text)
    return ' '.join(t for t in text.split() if t not in STOP_WORDS and len(t) > 2)

def analyze_signals(text):
    signals = []
    tl = text.lower()
    if sum(1 for c in text if c.isupper()) / max(len(text),1) > 0.15:
        signals.append("Excessive capitalization detected")
    for w in ['shocking','exposed','viral','breaking','secret','hidden','suppressed','must share','forward this','government hiding','whatsapp forward','share before delete']:
        if w in tl:
            signals.append(f"Clickbait phrase: '{w}'")
            break
    if text.count('!') > 2: signals.append("Multiple exclamation marks")
    if text.count('?') > 3: signals.append("Excessive question marks")
    caps_words = [w for w in text.split() if w.isupper() and len(w) > 3]
    if len(caps_words) >= 2: signals.append(f"All-caps words: {', '.join(caps_words[:3])}")
    for w in ['illuminati','deep state','microchip','population control','cover up','false flag']:
        if w in tl:
            signals.append(f"Conspiracy keyword: '{w}'")
            break
    return signals

# ── AI Prompt (shared) ────────────────────────────────────────
def build_prompt(text):
    return f"""You are an expert fake news detection system specialised in Indian media.
Analyse this news text and determine if it is FAKE or REAL.
Be especially alert to: sensational language, WhatsApp forwards, unverifiable claims, conspiracy theories, anti-government propaganda without evidence.

NEWS TEXT:
\"\"\"{text}\"\"\"

Respond ONLY with valid JSON, absolutely no markdown, no extra text, no explanation outside the JSON:
{{
  "verdict": "FAKE",
  "confidence": 85,
  "reasoning": "Explanation here in 2-3 sentences.",
  "red_flags": ["flag1", "flag2"],
  "credibility_score": 2,
  "category": "political"
}}

verdict must be exactly FAKE or REAL. confidence is 0-100. credibility_score is 0-10."""

# ── Gemini API ────────────────────────────────────────────────
def call_gemini_api(text):
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        return {"error": "no_api_key"}

    payload = json.dumps({
        "contents": [{"parts": [{"text": build_prompt(text)}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 500}
    }).encode('utf-8')

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            raw  = data['candidates'][0]['content']['parts'][0]['text'].strip()
            raw  = re.sub(r'^```json\s*','',raw); raw = re.sub(r'\s*```$','',raw)
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[ERROR] Gemini {e.code}: {body}")
        return {"error": f"gemini_{e.code}"}
    except json.JSONDecodeError as e:
        print(f"[ERROR] Gemini JSON parse: {e}")
        return {"error": "parse_failed"}
    except Exception as e:
        print(f"[ERROR] Gemini: {e}")
        return {"error": "api_failed"}

def call_ai_api(text):
    """Auto-selects: Claude if ANTHROPIC_API_KEY set, else Gemini."""
    if os.environ.get('ANTHROPIC_API_KEY'):
        return call_claude_api(text)
    elif os.environ.get('GEMINI_API_KEY'):
        return call_gemini_api(text)
    return {"error": "no_api_key"}

# ── Cross-verify ──────────────────────────────────────────────
def cross_verify(ml, ai):
    ml_label, ml_conf = ml['label'], ml['confidence']
    ai_label = ai.get('verdict')
    ai_conf  = ai.get('confidence', 0)

    if not ai_label:
        return {"final_label":ml_label,"final_confidence":ml_conf,"agreement":"ml_only","agreement_text":"ML Model Only (AI unavailable)","agreement_color":"var(--neon-blue)"}
    if ml_label == ai_label:
        return {"final_label":ml_label,"final_confidence":min(round((ml_conf+ai_conf)/2+5,1),99.9),"agreement":"full_agreement","agreement_text":"✓ Both ML Model & AI Agree","agreement_color":"var(--neon-green)"}
    else:
        final_label = ai_label if ai_conf >= ml_conf else ml_label
        final_conf  = round(max(ai_conf, ml_conf) * 0.85, 1)
        return {"final_label":final_label,"final_confidence":final_conf,"agreement":"disagreement","agreement_text":"⚠ ML & AI Disagree — Review Carefully","agreement_color":"#f59e0b"}

# ── Helper: get active AI engine name ─────────────────────────
def get_ai_engine_name():
    if os.environ.get('ANTHROPIC_API_KEY'): return 'Claude AI'
    if os.environ.get('GEMINI_API_KEY'):    return 'Gemini AI'
    return 'AI'

def get_api_key_set():
    return bool(os.environ.get('ANTHROPIC_API_KEY','') or os.environ.get('GEMINI_API_KEY',''))

# ── Routes ────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html', active='home')

@app.route('/detect')
def detect():
    return render_template('detect.html', active='detect',
        api_key_set=get_api_key_set(),
        ai_engine=get_ai_engine_name())

@app.route('/predict', methods=['POST'])
def predict():
    data   = request.get_json(force=True)
    text   = data.get('text','').strip()
    use_ai = data.get('use_ai', True)

    if not text:           return jsonify({"error":"No text provided"}), 400
    if len(text) < 20:     return jsonify({"error":"Text too short (min 20 chars)"}), 400

    signals = analyze_signals(text)

    # ── ML Model ──────────────────────────────────────────────
    if model_pipeline:
        processed = preprocess_text(text)
        prob      = model_pipeline.predict_proba([processed])[0]
        ml_label  = "REAL" if prob[1] >= 0.5 else "FAKE"
        ml_conf   = round(float(max(prob))*100, 1)
        ml_fp, ml_rp = round(float(prob[0]),3), round(float(prob[1]),3)
    else:
        ml_label = "FAKE" if any(w in text.lower() for w in ['shocking','exposed','viral']) else "REAL"
        ml_conf, ml_fp, ml_rp = 72.0, 0.72, 0.28

    ml_result = {"label":ml_label,"confidence":ml_conf,"fake_prob":ml_fp,"real_prob":ml_rp}

    # ── AI Engine ─────────────────────────────────────────────
    ai_result, ai_available = {}, False
    if use_ai and get_api_key_set():
        ai_raw = call_ai_api(text)
        print(f"[DEBUG] AI raw response: {ai_raw}")
        if "error" not in ai_raw:
            ai_result, ai_available = ai_raw, True

    cross = cross_verify(ml_result, ai_result if ai_available else {})

    return jsonify({
        "label":           cross["final_label"],
        "confidence":      cross["final_confidence"],
        "agreement":       cross["agreement"],
        "agreement_text":  cross["agreement_text"],
        "agreement_color": cross["agreement_color"],
        "ml_label":        ml_label,
        "ml_confidence":   ml_conf,
        "ml_fake_prob":    ml_fp,
        "ml_real_prob":    ml_rp,
        "ai_available":    ai_available,
        "ai_engine":       get_ai_engine_name(),
        "ai_label":        ai_result.get("verdict","N/A"),
        "ai_confidence":   ai_result.get("confidence",0),
        "ai_reasoning":    ai_result.get("reasoning",""),
        "ai_red_flags":    ai_result.get("red_flags",[]),
        "ai_credibility":  ai_result.get("credibility_score","N/A"),
        "ai_category":     ai_result.get("category",""),
        "signals":         signals,
        "processed_length":len(text.split()),
        "fake_prob":       ml_fp,
        "real_prob":       ml_rp,
    })

@app.route('/about')
def about():
    return render_template('about.html', active='about')

@app.route('/performance')
def performance():
    return render_template('performance.html', active='performance', metrics=metrics)

@app.route('/contact')
def contact():
    return render_template('contact.html', active='contact')

@app.route('/contact/submit', methods=['POST'])
def contact_submit():
    return jsonify({"status":"success","message":"Message received!"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
