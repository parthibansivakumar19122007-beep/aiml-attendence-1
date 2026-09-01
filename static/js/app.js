/* ============================================================
   SPATIAL AI GLASS - app.js v2.0
   Particle engine, 3D tilt, magnetic buttons, ripple,
   page transitions, skeleton loaders, animated counters,
   circular gauge, toast engine, IST clock
   ============================================================ */

'use strict';

/* ── Feature detection ────────────────────────────────────── */
const REDUCE_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const IS_MOBILE     = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || window.innerWidth < 768;

/* ============================================================
   1. PARTICLE CANVAS ENGINE
   ============================================================ */
(function initParticles() {
  if (REDUCE_MOTION || IS_MOBILE) return;

  const canvas = document.getElementById('particlesCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let W, H, nodes = [], RAF_ID;
  const COUNT = 55;
  const CONNECT_DIST = 140;
  const MOUSE = { x: -9999, y: -9999 };

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function Node() {
    this.x  = Math.random() * W;
    this.y  = Math.random() * H;
    this.vx = (Math.random() - 0.5) * 0.35;
    this.vy = (Math.random() - 0.5) * 0.35;
    this.r  = Math.random() * 1.8 + 0.6;
    this.a  = Math.random() * 0.55 + 0.15;
  }

  function initNodes() {
    nodes = [];
    for (let i = 0; i < COUNT; i++) nodes.push(new Node());
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // Update positions
    nodes.forEach(n => {
      n.x += n.vx; n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
    });

    // Draw connections
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < CONNECT_DIST) {
          const alpha = (1 - dist / CONNECT_DIST) * 0.22;
          ctx.beginPath();
          ctx.strokeStyle = `rgba(34,211,238,${alpha})`;
          ctx.lineWidth = 0.8;
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.stroke();
        }
      }
      // Mouse proximity interaction
      const mdx = nodes[i].x - MOUSE.x;
      const mdy = nodes[i].y - MOUSE.y;
      const mdist = Math.sqrt(mdx*mdx + mdy*mdy);
      if (mdist < 120) {
        const mAlpha = (1 - mdist / 120) * 0.5;
        ctx.beginPath();
        ctx.strokeStyle = `rgba(167,139,250,${mAlpha})`;
        ctx.lineWidth = 1;
        ctx.moveTo(nodes[i].x, nodes[i].y);
        ctx.lineTo(MOUSE.x, MOUSE.y);
        ctx.stroke();
      }
    }

    // Draw nodes
    nodes.forEach(n => {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(34,211,238,${n.a})`;
      ctx.fill();
    });

    RAF_ID = requestAnimationFrame(draw);
  }

  resize(); initNodes(); draw();
  window.addEventListener('resize', () => { resize(); initNodes(); });
  document.addEventListener('mousemove', e => { MOUSE.x = e.clientX; MOUSE.y = e.clientY; });
})();


/* ============================================================
   2. CLEAN FLAT HOVER ENGINE (3D Effects Removed)
   ============================================================ */
(function initCleanHover() {
  // 3D perspective and tilting disabled for ultra-clean flat glass aesthetic
})();


/* ============================================================
   3. MAGNETIC BUTTON ENGINE
   ============================================================ */
(function initMagnetic() {
  if (REDUCE_MOTION || IS_MOBILE) return;
  document.querySelectorAll('.btn-magnetic').forEach(btn => {
    btn.addEventListener('mousemove', e => {
      const rect = btn.getBoundingClientRect();
      const dx = e.clientX - (rect.left + rect.width  / 2);
      const dy = e.clientY - (rect.top  + rect.height / 2);
      btn.style.transform = `translate(${dx * 0.35}px, ${dy * 0.35}px)`;
    });
    btn.addEventListener('mouseleave', () => { btn.style.transform = ''; });
  });
})();


/* ============================================================
   4. RIPPLE EFFECT ENGINE
   ============================================================ */
(function initRipple() {
  document.addEventListener('click', e => {
    const btn = e.target.closest('.btn-glass');
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    const x    = e.clientX - rect.left - size / 2;
    const y    = e.clientY - rect.top  - size / 2;
    const r    = document.createElement('span');
    r.className = 'ripple';
    r.style.cssText = `width:${size}px; height:${size}px; left:${x}px; top:${y}px;`;
    btn.appendChild(r);
    r.addEventListener('animationend', () => r.remove());
  });
})();


/* ============================================================
   5. PAGE TRANSITION MANAGER
   ============================================================ */
(function initPageTransitions() {
  // Create overlay once
  if (!document.getElementById('pageTransitionOverlay')) {
    const el = document.createElement('div');
    el.id = 'pageTransitionOverlay';
    el.className = 'page-transition-overlay';
    document.body.appendChild(el);
  }

  // Intercept navigation links
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    // Skip: external, anchors, javascript:, download, same-page
    if (!href || href.startsWith('#') || href.startsWith('javascript')
        || href.startsWith('http') || a.target === '_blank'
        || a.hasAttribute('data-no-transition') || a.hasAttribute('download')) return;

    e.preventDefault();
    const overlay = document.getElementById('pageTransitionOverlay');
    overlay.classList.add('active');
    setTimeout(() => { window.location.href = href; }, 280);
  });

  // Fade out on page load
  window.addEventListener('pageshow', () => {
    const overlay = document.getElementById('pageTransitionOverlay');
    if (overlay) {
      overlay.classList.add('active');
      requestAnimationFrame(() => {
        overlay.style.transition = 'opacity 0.3s ease';
        overlay.classList.remove('active');
      });
    }
  });
})();


/* ============================================================
   6. ANIMATED COUNTER (count-up)
   ============================================================ */
function animateCounter(el, target, durationMs = 1400) {
  if (REDUCE_MOTION) { el.textContent = target; return; }
  const isFloat  = !Number.isInteger(target);
  const decimals = isFloat ? 1 : 0;
  let start = null;
  function step(ts) {
    if (!start) start = ts;
    const p = Math.min((ts - start) / durationMs, 1);
    // ease-out-cubic
    const eased = 1 - Math.pow(1 - p, 3);
    const val   = eased * target;
    el.textContent = val.toFixed(decimals);
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = target.toFixed(decimals);
  }
  requestAnimationFrame(step);
}

// Auto-init elements with data-count
(function initCounters() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el  = entry.target;
      const val = parseFloat(el.dataset.count);
      if (!isNaN(val)) animateCounter(el, val);
      obs.unobserve(el);
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('[data-count]').forEach(el => obs.observe(el));
})();


/* ============================================================
   7. CIRCULAR GAUGE
   ============================================================ */
function initGauge(wrap, percentage) {
  if (!wrap) return;
  const bar = wrap.querySelector('.gauge-bar');
  if (!bar) return;
  const CIRC     = 471;  // 2π × 75
  const offset   = CIRC - (percentage / 100) * CIRC;
  const clampPct = Math.min(Math.max(percentage, 0), 100);

  // Color transitions based on percentage
  let color;
  if (clampPct >= 75)      color = '#34d399';  // green
  else if (clampPct >= 60) color = '#fbbf24';  // amber
  else                     color = '#f87171';  // red

  bar.style.stroke = color;

  setTimeout(() => {
    bar.style.strokeDashoffset = offset;
  }, 200);

  // Optional glow ring
  const ring = wrap.querySelector('.gauge-glow-ring');
  if (ring) {
    ring.style.setProperty('--pct', `${clampPct}%`);
    ring.style.background = `conic-gradient(${color} ${clampPct}%, transparent 0%)`;
  }
}

// Auto-init gauges
document.querySelectorAll('.gauge-wrap[data-pct]').forEach(el => {
  initGauge(el, parseFloat(el.dataset.pct) || 0);
});


/* ============================================================
   8. ANIMATED BAR CHART (viewport reveal)
   ============================================================ */
(function initBarCharts() {
  const bars = document.querySelectorAll('.bar-fill[data-pct]');
  if (!bars.length) return;
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      el.style.transform = `scaleY(${parseFloat(el.dataset.pct) / 100})`;
      obs.unobserve(el);
    });
  }, { threshold: 0.2 });
  bars.forEach(b => obs.observe(b));
})();


/* ============================================================
   9. DONUT RING
   ============================================================ */
function initDonut(wrap, percentage) {
  if (!wrap) return;
  const bar = wrap.querySelector('.donut-bar');
  if (!bar) return;
  const CIRC  = 251; // 2π × 40
  const offset = CIRC - (percentage / 100) * CIRC;
  let color;
  if (percentage >= 75)      color = '#34d399';
  else if (percentage >= 60) color = '#fbbf24';
  else                       color = '#f87171';
  bar.style.stroke = color;
  setTimeout(() => { bar.style.strokeDashoffset = offset; }, 200);
}
document.querySelectorAll('.donut-wrap[data-pct]').forEach(el => {
  initDonut(el, parseFloat(el.dataset.pct) || 0);
});


/* ============================================================
   10. SUBJECT BAR ROWS (viewport reveal)
   ============================================================ */
(function initSubjectBars() {
  const rows = document.querySelectorAll('.sub-bar-fill[data-pct]');
  if (!rows.length) return;
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      const pct = parseFloat(el.dataset.pct) / 100;
      el.style.transform = `scaleX(${Math.min(pct, 1)})`;
      obs.unobserve(el);
    });
  }, { threshold: 0.15 });
  rows.forEach(r => obs.observe(r));
})();


/* ============================================================
   11. TOAST NOTIFICATION ENGINE
   ============================================================ */
const Toast = (function() {
  function getContainer() {
    let el = document.getElementById('glassToastContainer');
    if (!el) {
      el = document.createElement('div');
      el.id = 'glassToastContainer';
      document.body.appendChild(el);
    }
    return el;
  }

  const ICONS = {
    success: '✅', error: '❌', warning: '⚠️', info: '💡'
  };
  const BORDERS = {
    success: 'rgba(52,211,153,0.5)', error: 'rgba(248,113,113,0.5)',
    warning: 'rgba(251,191,36,0.5)', info:  'rgba(34,211,238,0.5)'
  };

  function show(message, type = 'info', durationMs = 4500) {
    const container = getContainer();
    const t = document.createElement('div');
    t.className = 'glass-toast';
    t.style.borderLeftColor = BORDERS[type] || BORDERS.info;
    t.style.borderLeftWidth = '3px';
    t.innerHTML = `
      <span class="toast-icon">${ICONS[type] || ICONS.info}</span>
      <span class="toast-body">${message}</span>
      <button onclick="this.parentElement.remove()" style="background:none;border:none;color:rgba(255,255,255,0.4);cursor:pointer;padding:0;font-size:1rem;">✕</button>
    `;
    container.appendChild(t);
    setTimeout(() => {
      t.classList.add('removing');
      t.addEventListener('transitionend', () => t.remove(), { once: true });
    }, durationMs);
    return t;
  }

  return { show, success: m => show(m,'success'), error: m => show(m,'error'),
    warning: m => show(m,'warning'), info: m => show(m,'info') };
})();

window.Toast = Toast;


/* ============================================================
   12. TABLE SEARCH FILTER
   ============================================================ */
(function initTableSearch() {
  document.querySelectorAll('[data-table-search]').forEach(input => {
    const tableId = input.dataset.tableSearch;
    const table   = document.getElementById(tableId);
    if (!table) return;
    const rows = () => table.querySelectorAll('tbody tr');

    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase();
      rows().forEach(tr => {
        const text = tr.textContent.toLowerCase();
        tr.classList.toggle('table-row-hidden', q.length > 0 && !text.includes(q));
      });
    });
  });
})();


/* ============================================================
   13. DRAG & DROP UPLOAD ZONE
   ============================================================ */
(function initDropZone() {
  document.querySelectorAll('.drop-zone').forEach(zone => {
    const inputId = zone.dataset.input;
    const input   = inputId ? document.getElementById(inputId) : null;
    const preview = zone.querySelector('.drop-preview');

    zone.addEventListener('click', () => input && input.click());

    zone.addEventListener('dragover', e => {
      e.preventDefault(); zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault(); zone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file && input) { const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; }
      if (file && preview) showPreview(preview, file);
    });

    if (input) {
      input.addEventListener('change', () => {
        if (input.files[0] && preview) showPreview(preview, input.files[0]);
      });
    }
  });

  function showPreview(el, file) {
    const reader = new FileReader();
    reader.onload = e => {
      el.src = e.target.result;
      el.classList.add('visible');
    };
    reader.readAsDataURL(file);
  }
})();


/* ============================================================
   14. LIVE IST CLOCK
   ============================================================ */
(function initClock() {
  function tick() {
    const el = document.getElementById('live-ist-clock');
    if (!el) return;
    const now = new Date();
    el.textContent = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata', hour12: true,
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      day: '2-digit', month: 'short', year: 'numeric'
    }).format(now) + ' IST';
  }
  tick();
  setInterval(tick, 1000);
})();


/* ============================================================
   15. FLASH ALERT AUTO-DISMISS
   ============================================================ */
(function initAlerts() {
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      if (typeof bootstrap !== 'undefined') {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) bsAlert.close();
      } else {
        alert.style.opacity = '0';
        alert.style.transition = 'opacity 0.5s ease';
        setTimeout(() => alert.remove(), 500);
      }
    }, 6000);
  });
})();


/* ============================================================
   16. GLASS MODAL FORM VALIDATION
   ============================================================ */
(function initFormValidation() {
  document.querySelectorAll('form[data-validate]').forEach(form => {
    form.addEventListener('submit', e => {
      let valid = true;
      form.querySelectorAll('[required].glass-input').forEach(input => {
        if (!input.value.trim()) {
          input.classList.add('is-invalid', 'shake');
          valid = false;
          input.addEventListener('animationend', () => input.classList.remove('shake'), { once: true });
        } else {
          input.classList.remove('is-invalid');
          input.classList.add('is-valid');
        }
      });
      if (!valid) e.preventDefault();
    });
  });
})();


/* ============================================================
   17. SESSION TIMER (Faculty active session)
   ============================================================ */
window.startSessionTimer = function(el, openedAtISO) {
  if (!el) return;
  const opened = new Date(openedAtISO);
  function update() {
    const elapsed = Math.floor((Date.now() - opened) / 1000);
    const h = Math.floor(elapsed / 3600).toString().padStart(2, '0');
    const m = Math.floor((elapsed % 3600) / 60).toString().padStart(2, '0');
    const s = (elapsed % 60).toString().padStart(2, '0');
    el.textContent = `${h}:${m}:${s}`;
  }
  update();
  setInterval(update, 1000);
};

/* ============================================================
   EXPOSE UTILITIES
   ============================================================ */
window.SpatialAI = {
  Toast,
  animateCounter,
  initGauge,
  initDonut,
  startSessionTimer
};
