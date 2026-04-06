/**
 * home.js — Home page typing animation
 */
'use strict';

(function initTypingEffect() {
  const el = document.getElementById('heroTyping');
  if (!el) return;

  const phrases = [
    'Detect Fake News',
    'Verify WhatsApp Forwards',
    'Fight Misinformation',
    'Trust Verified Facts',
  ];

  let phraseIdx = 0;
  let charIdx = 0;
  let isDeleting = false;
  let delay = 100;

  function type() {
    const current = phrases[phraseIdx];

    if (!isDeleting) {
      el.textContent = current.slice(0, charIdx + 1);
      charIdx++;
      delay = 90;
      if (charIdx === current.length) {
        isDeleting = true;
        delay = 2000;        // pause before deleting
      }
    } else {
      el.textContent = current.slice(0, charIdx - 1);
      charIdx--;
      delay = 50;
      if (charIdx === 0) {
        isDeleting = false;
        phraseIdx = (phraseIdx + 1) % phrases.length;
        delay = 400;
      }
    }

    setTimeout(type, delay);
  }

  setTimeout(type, 800);   // initial delay before starting
})();
