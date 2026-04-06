/**
 * detect.js — Dual-engine prediction UI
 * ML Model + Claude AI cross-verification
 */
'use strict';

const textarea  = document.getElementById('newsInput');
const charCount = document.getElementById('charCount');

// ── Character counter ─────────────────────────────────────────
if (textarea && charCount) {
  textarea.addEventListener('input', () => {
    charCount.textContent = textarea.value.length;
    charCount.style.color = textarea.value.length > 4500 ? 'var(--neon-red)' : '';
  });
}

// ── Load example ──────────────────────────────────────────────
function loadExample(card) {
  const text = card.querySelector('p').textContent.replace(/^"|"$/g, '');
  textarea.value = text;
  charCount.textContent = text.length;
  textarea.focus();
  textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
  textarea.style.borderColor = 'var(--neon-purple)';
  textarea.style.boxShadow = '0 0 0 3px rgba(139,92,246,0.15),0 0 20px rgba(139,92,246,0.35)';
  setTimeout(() => { textarea.style.borderColor = ''; textarea.style.boxShadow = ''; }, 1200);
}

function clearInput() {
  textarea.value = '';
  charCount.textContent = '0';
  textarea.focus();
  hideResult();
}

function hideResult() {
  const p = document.getElementById('resultPanel');
  if (!p) return;
  p.style.opacity = '0'; p.style.transform = 'translateY(20px)';
  setTimeout(() => { p.style.display = 'none'; }, 300);
}

// ── Progress bar ──────────────────────────────────────────────
function showProgress(useAI) {
  const wrap  = document.getElementById('progressWrap');
  const bar   = document.getElementById('progressBar');
  const label = document.getElementById('progressLabel');
  if (!wrap) return;
  wrap.style.display = 'block';
  bar.style.width = '0%';

  const steps = useAI ? [
    { w: '10%', t: 'Tokenising text...',          d: 100  },
    { w: '25%', t: 'Removing stopwords...',        d: 400  },
    { w: '40%', t: 'Computing TF-IDF vectors...',  d: 800  },
    { w: '55%', t: 'Running ML classifier...',     d: 1200 },
    { w: '65%', t: 'Calling Claude AI API...',     d: 1600 },
    { w: '80%', t: 'AI analysing context...',      d: 3000 },
    { w: '92%', t: 'Cross-verifying results...',   d: 5000 },
    { w: '98%', t: 'Finalising verdict...',        d: 6500 },
  ] : [
    { w: '20%', t: 'Tokenising text...',           d: 100  },
    { w: '45%', t: 'Computing TF-IDF vectors...',  d: 400  },
    { w: '70%', t: 'Running ML classifier...',     d: 800  },
    { w: '90%', t: 'Finalising verdict...',        d: 1200 },
  ];

  steps.forEach(({ w, t, d }) => {
    setTimeout(() => {
      bar.style.transition = 'width 0.5s cubic-bezier(0.22,1,0.36,1)';
      bar.style.width = w;
      if (label) label.textContent = t;
    }, d);
  });
}

function hideProgress() {
  const wrap = document.getElementById('progressWrap');
  if (wrap) setTimeout(() => { wrap.style.display = 'none'; }, 300);
}

// ── Main analysis function ────────────────────────────────────
async function analyseNews() {
  const text   = textarea?.value?.trim();
  const useAI  = document.getElementById('aiToggle')?.checked ?? false;

  if (!text) { shakeTextarea(); return; }
  if (text.length < 20) { shakeTextarea('Text too short — add more context.'); return; }

  const btn = document.getElementById('analyseBtn');
  btn.querySelector('.btn-text').style.display = 'none';
  btn.querySelector('.btn-loading').style.display = 'inline-flex';
  btn.disabled = true;

  showProgress(useAI);
  hideResult();

  try {
    const res = await fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, use_ai: useAI }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Server error'); }
    const data = await res.json();
    hideProgress();
    displayResult(data, text);
  } catch (err) {
    hideProgress();
    displayError(err.message || 'Analysis failed. Please try again.');
  } finally {
    btn.querySelector('.btn-text').style.display = 'inline-flex';
    btn.querySelector('.btn-loading').style.display = 'none';
    btn.disabled = false;
  }
}

// ── Display result ────────────────────────────────────────────
function displayResult(data, originalText) {
  const isFake = data.label === 'FAKE';

  // ── Final Verdict ──────────────────────────────────────────
  const vs = document.getElementById('verdictSection');
  vs.className = 'verdict-section ' + (isFake ? 'is-fake' : 'is-real');
  document.getElementById('verdictIcon').innerHTML = isFake
    ? '<i class="fas fa-circle-xmark" style="color:var(--neon-red)"></i>'
    : '<i class="fas fa-circle-check" style="color:var(--neon-green)"></i>';
  document.getElementById('verdictLabel').innerHTML = isFake
    ? '<span class="fake-label">FAKE NEWS</span>'
    : '<span class="real-label">REAL NEWS</span>';
  document.getElementById('verdictSubtitle').textContent =
    `${data.confidence}% combined confidence`;

  // ── Agreement Banner ───────────────────────────────────────
  const banner = document.getElementById('agreementBanner');
  const agText = document.getElementById('agreementText');
  banner.style.background = data.agreement === 'full_agreement'
    ? 'rgba(52,211,153,0.08)' : data.agreement === 'disagreement'
    ? 'rgba(245,158,11,0.08)' : 'rgba(99,179,237,0.08)';
  banner.style.borderColor = data.agreement_color;
  banner.style.color = data.agreement_color;
  agText.textContent = data.agreement_text;

  // ── Engine Comparison ──────────────────────────────────────
  // ML Card
  const mlIsFake = data.ml_label === 'FAKE';
  document.getElementById('mlTag').textContent = data.ml_label;
  document.getElementById('mlTag').className = 'er-tag ' + (mlIsFake ? 'er-fake' : 'er-real');
  document.getElementById('mlConf').textContent = data.ml_confidence + '%';
  document.getElementById('mlLabel').textContent = mlIsFake ? '🔴 Fake' : '🟢 Real';
  setTimeout(() => {
    const f = document.getElementById('mlFill');
    f.className = 'er-fill ' + (mlIsFake ? 'er-fill-fake' : 'er-fill-real');
    f.style.width = data.ml_confidence + '%';
  }, 300);

  // AI Card
  if (data.ai_available) {
    const aiIsFake = data.ai_label === 'FAKE';
    document.getElementById('aiTag').textContent = data.ai_label;
    document.getElementById('aiTag').className = 'er-tag ' + (aiIsFake ? 'er-fake' : 'er-real');
    document.getElementById('aiConf').textContent = data.ai_confidence + '%';
    document.getElementById('aiLabel').textContent = aiIsFake ? '🔴 Fake' : '🟢 Real';
    document.getElementById('aiCard').style.opacity = '1';
    setTimeout(() => {
      const f = document.getElementById('aiFill');
      f.className = 'er-fill ' + (aiIsFake ? 'er-fill-fake' : 'er-fill-real');
      f.style.width = data.ai_confidence + '%';
    }, 500);
  } else {
    document.getElementById('aiTag').textContent = 'N/A';
    document.getElementById('aiTag').className = 'er-tag er-na';
    document.getElementById('aiConf').textContent = '—';
    document.getElementById('aiLabel').textContent = 'Not available';
    document.getElementById('aiCard').style.opacity = '0.4';
  }

  // ── Confidence Gauge ───────────────────────────────────────
  const gaugeFill = document.getElementById('gaugeFill');
  gaugeFill.className = 'gauge-fill ' + (isFake ? 'fake-fill' : 'real-fill');
  setTimeout(() => { gaugeFill.style.width = data.confidence + '%'; }, 200);

  let cur = 0;
  const gv = document.getElementById('gaugeValue');
  const start = performance.now();
  (function animGauge(now) {
    const p = Math.min((now - start) / 1000, 1);
    cur = (1 - Math.pow(1 - p, 3)) * data.confidence;
    gv.textContent = cur.toFixed(1) + '%';
    gv.style.color = isFake ? 'var(--neon-red)' : 'var(--neon-green)';
    if (p < 1) requestAnimationFrame(animGauge);
  })(start);

  document.getElementById('realProb').textContent = (data.real_prob * 100).toFixed(1) + '%';
  document.getElementById('fakeProb').textContent = (data.fake_prob * 100).toFixed(1) + '%';

  // ── AI Reasoning ───────────────────────────────────────────
  const aiSec = document.getElementById('aiReasoningSection');
  if (data.ai_available && data.ai_reasoning) {
    aiSec.style.display = 'block';
    document.getElementById('aiReasoningBox').textContent = data.ai_reasoning;

    const catEl = document.getElementById('aiCategory');
    if (data.ai_category) {
      catEl.textContent = '📂 ' + data.ai_category.charAt(0).toUpperCase() + data.ai_category.slice(1);
      catEl.style.display = 'inline-flex';
    }
    const credEl = document.getElementById('aiCredibility');
    if (data.ai_credibility !== 'N/A') {
      credEl.textContent = '⭐ Credibility: ' + data.ai_credibility + '/10';
      credEl.style.display = 'inline-flex';
    }

    const rfWrap = document.getElementById('aiRedFlagsWrap');
    const rfList = document.getElementById('aiRedFlagsList');
    if (data.ai_red_flags && data.ai_red_flags.length > 0) {
      rfWrap.style.display = 'block';
      rfList.innerHTML = '';
      data.ai_red_flags.forEach((flag, i) => {
        const li = document.createElement('li');
        li.className = 'signal-item';
        li.style.animationDelay = i * 80 + 'ms';
        li.innerHTML = `<i class="fas fa-flag"></i> ${escapeHtml(flag)}`;
        rfList.appendChild(li);
      });
    }

    // Set category in stats
    document.getElementById('newsCategory').textContent =
      data.ai_category ? data.ai_category.charAt(0).toUpperCase() + data.ai_category.slice(1) : '—';
    document.getElementById('credScore').textContent =
      data.ai_credibility !== 'N/A' ? data.ai_credibility + '/10' : '—';
  } else {
    aiSec.style.display = 'none';
    document.getElementById('newsCategory').textContent = '—';
    document.getElementById('credScore').textContent = '—';
  }

  // ── Heuristic Signals ──────────────────────────────────────
  const sigList = document.getElementById('signalsList');
  sigList.innerHTML = '';
  if (data.signals && data.signals.length > 0) {
    data.signals.forEach((s, i) => {
      const li = document.createElement('li');
      li.className = 'signal-item';
      li.style.animationDelay = i * 80 + 'ms';
      li.innerHTML = `<i class="fas fa-triangle-exclamation"></i> ${escapeHtml(s)}`;
      sigList.appendChild(li);
    });
  } else {
    sigList.innerHTML = '<li class="no-signals"><i class="fas fa-circle-check"></i> No heuristic signals detected</li>';
  }

  // ── Stats ──────────────────────────────────────────────────
  const wc = originalText.split(/\s+/).filter(Boolean).length;
  document.getElementById('wordCount').textContent = wc.toLocaleString();
  document.getElementById('readTime').textContent = Math.ceil(wc / 200) + ' min';

  // ── Show Panel ─────────────────────────────────────────────
  const panel = document.getElementById('resultPanel');
  const card  = document.getElementById('resultCard');
  panel.style.display = 'block';
  panel.style.opacity = '0';
  panel.style.transform = 'translateY(30px)';
  requestAnimationFrame(() => {
    panel.style.transition = 'opacity 0.6s ease,transform 0.6s cubic-bezier(0.22,1,0.36,1)';
    panel.style.opacity = '1';
    panel.style.transform = 'translateY(0)';
  });
  setTimeout(() => { panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, 100);

  card.style.borderColor = isFake ? 'rgba(248,113,113,0.3)' : 'rgba(52,211,153,0.3)';
  card.style.boxShadow   = isFake ? '0 0 30px rgba(248,113,113,0.1)' : '0 0 30px rgba(52,211,153,0.1)';
}

// ── Copy result ───────────────────────────────────────────────
function copyResult() {
  const label = document.getElementById('verdictLabel')?.textContent?.trim();
  const conf  = document.getElementById('gaugeValue')?.textContent?.trim();
  const agree = document.getElementById('agreementText')?.textContent?.trim();
  const reasoning = document.getElementById('aiReasoningBox')?.textContent?.trim();
  let text = `SatyaCheck Analysis\nVerdict: ${label}\nConfidence: ${conf}\n${agree}`;
  if (reasoning) text += `\n\nAI Reasoning: ${reasoning}`;
  text += '\n\nPowered by SatyaCheck — ML + Claude AI';
  navigator.clipboard.writeText(text).then(() => {
    const btn = event.target.closest('button');
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
    btn.style.color = 'var(--neon-green)';
    setTimeout(() => { btn.innerHTML = orig; btn.style.color = ''; }, 2000);
  });
}

// ── Error display ─────────────────────────────────────────────
function displayError(message) {
  const panel = document.getElementById('resultPanel');
  const card  = document.getElementById('resultCard');
  card.innerHTML = `
    <div class="verdict-section" style="background:rgba(248,113,113,0.06);border:1px solid rgba(248,113,113,0.2);text-align:center;padding:2rem;border-radius:12px;">
      <div style="font-size:2.5rem;margin-bottom:1rem"><i class="fas fa-triangle-exclamation" style="color:var(--neon-red)"></i></div>
      <div style="font-size:1.1rem;font-weight:600;margin-bottom:.5rem;color:var(--neon-red)">Analysis Failed</div>
      <div style="color:var(--text-secondary);font-size:.9rem">${escapeHtml(message)}</div>
    </div>
    <div style="display:flex;justify-content:center;margin-top:1.5rem">
      <button class="btn-ghost" onclick="clearInput()"><i class="fas fa-redo"></i> Try Again</button>
    </div>`;
  panel.style.display = 'block';
  panel.style.opacity = '1';
  panel.style.transform = 'none';
}

// ── Shake textarea ────────────────────────────────────────────
function shakeTextarea(msg) {
  if (!textarea) return;
  textarea.style.borderColor = 'var(--neon-red)';
  textarea.style.animation = 'shake 0.4s cubic-bezier(0.36,.07,.19,.97) both';
  const s = document.createElement('style');
  s.textContent = '@keyframes shake{10%,90%{transform:translateX(-3px)}20%,80%{transform:translateX(4px)}30%,50%,70%{transform:translateX(-5px)}40%,60%{transform:translateX(5px)}}';
  document.head.appendChild(s);
  if (msg) { textarea.placeholder = msg; setTimeout(() => { textarea.placeholder = 'Paste news...'; textarea.style.borderColor = ''; }, 2500); }
  textarea.addEventListener('animationend', () => { textarea.style.animation = ''; textarea.style.borderColor = ''; }, { once: true });
}

function escapeHtml(str) {
  const d = document.createElement('div'); d.textContent = str; return d.innerHTML;
}

// ── Ctrl+Enter shortcut ───────────────────────────────────────
textarea?.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') analyseNews();
});
