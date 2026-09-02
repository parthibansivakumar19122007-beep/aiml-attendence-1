/* ============================================================
   SPATIAL AI GLASS - face-hud.js
   AI Vision HUD, Facial Landmark Grid, Geofence Radar Canvas,
   and 6-Step Verification Pipeline State Machine.
   ============================================================ */

class FaceVisionHUD {
  constructor(options = {}) {
    this.videoEl = options.videoEl || document.getElementById('webcamVideo');
    this.canvasEl = options.canvasEl || document.getElementById('hudCanvas');
    this.radarCanvasEl = options.radarCanvasEl || document.getElementById('radarCanvas');
    this.pipelineEl = options.pipelineEl || document.getElementById('pipelineTrack');
    this.statusPillEl = options.statusPillEl || document.getElementById('hudStatusPill');
    this.hudWrapEl = options.hudWrapEl || document.getElementById('faceHudWrap');
    
    this.ctx = this.canvasEl ? this.canvasEl.getContext('2d') : null;
    this.radarCtx = this.radarCanvasEl ? this.radarCanvasEl.getContext('2d') : null;
    
    this.stream = null;
    this.animId = null;
    this.radarAnimId = null;
    this.radarAngle = 0;
    
    this.state = 'INITIALIZING'; // INITIALIZING, CAMERA_READY, SCANNING, ANALYZING, VERIFIED, FAILED
    this.distanceMeters = null;
    this.maxRadiusMeters = 50.0;
    
    this.steps = [
      { id: 'step-camera', label: '1. SENSOR STREAM', sub: 'High-Res Optical Capture' },
      { id: 'step-detect', label: '2. SPATIAL GEOMETRY', sub: 'Neural Mesh & Landmark Array' },
      { id: 'step-embed', label: '3. BIOMETRIC VECTOR', sub: '128-Dim Cosine Extraction' },
      { id: 'step-match', label: '4. IDENTITY MATCH', sub: 'Neural Network Verification' },
      { id: 'step-geo', label: '5. GEOFENCE RADAR', sub: '50m Haversine Radius Check' },
      { id: 'step-commit', label: '6. AUDIT COMMIT', sub: 'Cryptographic Attendance Log' }
    ];

    this.initRadar();
    this.initPipeline();
  }

  initPipeline() {
    if (!this.pipelineEl) return;
    this.pipelineEl.innerHTML = '';
    this.steps.forEach((s, idx) => {
      const stepEl = document.createElement('div');
      stepEl.className = 'pipeline-step pending';
      stepEl.id = s.id;
      stepEl.innerHTML = `
        <div class="step-icon">0${idx+1}</div>
        <div class="step-meta">
          <div class="step-label">${s.label}</div>
          <div class="step-sublabel">${s.sub}</div>
        </div>
      `;
      this.pipelineEl.appendChild(stepEl);
    });
  }

  setStepState(stepIndex, state) { // state: 'pending', 'active', 'done', 'failed'
    if (stepIndex < 0 || stepIndex >= this.steps.length) return;
    const stepEl = document.getElementById(this.steps[stepIndex].id);
    if (!stepEl) return;
    stepEl.className = `pipeline-step ${state}`;
    const icon = stepEl.querySelector('.step-icon');
    if (state === 'done' && icon) icon.innerHTML = '✓';
    else if (state === 'failed' && icon) icon.innerHTML = '✕';
    else if (state === 'active' && icon) icon.innerHTML = '●';
    else if (icon) icon.innerHTML = `0${stepIndex + 1}`;
  }

  setStatus(text, type = 'cyan') {
    if (!this.statusPillEl) return;
    this.statusPillEl.textContent = text;
    this.statusPillEl.className = `hud-status-pill text-${type}`;
  }

  async startCamera() {
    try {
      this.setStatus('INITIALIZING OPTICAL STREAM...', 'cyan');
      this.setStepState(0, 'active');

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (!window.isSecureContext && window.location.protocol === 'http:') {
          const httpsUrl = 'https://' + window.location.host + window.location.pathname;
          if (window.Toast) {
            window.Toast.error('Mobile browsers require HTTPS to open the camera. Please switch to HTTPS.');
          }
          this.setStatus('HTTPS REQUIRED FOR MOBILE CAMERA', 'red');
          this.setStepState(0, 'failed');
          this.state = 'FAILED';
          return false;
        }
        throw new Error('Camera API not supported or blocked by browser.');
      }
      
      let stream = null;
      try {
        // Try optimal front/user camera first
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }
        });
      } catch (e1) {
        console.warn('Optimal camera constraint failed, trying basic resolution...', e1);
        try {
          // Fallback without facingMode (essential for Windows laptop webcams)
          stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 } }
          });
        } catch (e2) {
          console.warn('Resolution constraint failed, trying simple video:true...', e2);
          try {
            // Absolute minimal fallback
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
          } catch (e3) {
            throw e3;
          }
        }
      }
      
      this.stream = stream;
      if (this.videoEl) {
        this.videoEl.srcObject = this.stream;
        await this.videoEl.play();
      }
      
      // Hide placeholder if any
      const placeholder = document.getElementById('hudPlaceholder');
      if (placeholder) placeholder.style.display = 'none';

      this.setStepState(0, 'done');
      this.setStepState(1, 'active');
      this.setStatus('AI VISION ACTIVE • ALIGN FACE', 'cyan');
      this.state = 'CAMERA_READY';
      this.startHudLoop();
      return true;
    } catch (err) {
      console.error('Camera Init Error:', err);
      this.setStepState(0, 'failed');
      this.setStatus('OPTICAL STREAM DENIED', 'red');
      this.state = 'FAILED';
      if (window.Toast) {
        if (!window.isSecureContext && window.location.protocol === 'http:') {
          window.Toast.error('Mobile camera requires HTTPS. Please access via https://' + window.location.host);
        } else if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          window.Toast.error('Camera permission blocked. Click the lock/camera icon in your address bar and select "Allow".');
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
          window.Toast.error('Camera is being used by another app. Please close other camera programs.');
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          window.Toast.error('No camera detected. Please plug in or enable a webcam.');
        } else {
          window.Toast.error('Camera access failed: ' + (err.message || 'Please check browser permissions.'));
        }
      }
      return false;
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }
  }

  captureFrameB64() {
    if (!this.videoEl || !this.videoEl.videoWidth) return null;
    const offscreen = document.createElement('canvas');
    offscreen.width = this.videoEl.videoWidth;
    offscreen.height = this.videoEl.videoHeight;
    const ctx = offscreen.getContext('2d');
    ctx.drawImage(this.videoEl, 0, 0, offscreen.width, offscreen.height);
    return offscreen.toDataURL('image/jpeg', 0.9);
  }

  startHudLoop() {
    const loop = () => {
      this.drawHudOverlay();
      this.animId = requestAnimationFrame(loop);
    };
    this.animId = requestAnimationFrame(loop);
  }

  drawHudOverlay() {
    if (!this.ctx || !this.canvasEl) return;
    const w = this.canvasEl.width = this.canvasEl.offsetWidth;
    const h = this.canvasEl.height = this.canvasEl.offsetHeight;
    this.ctx.clearRect(0, 0, w, h);

    if (this.state === 'CAMERA_READY' || this.state === 'SCANNING' || this.state === 'ANALYZING') {
      const cx = w / 2;
      const cy = h / 2;
      const rx = w * 0.22;
      const ry = h * 0.32;

      // Draw subtle spatial crosshairs
      this.ctx.strokeStyle = 'rgba(34, 211, 238, 0.2)';
      this.ctx.lineWidth = 1;
      this.ctx.beginPath();
      this.ctx.moveTo(cx - 30, cy); this.ctx.lineTo(cx + 30, cy);
      this.ctx.moveTo(cx, cy - 30); this.ctx.lineTo(cx, cy + 30);
      this.ctx.stroke();

      // Dynamic landmark points simulation
      const time = Date.now() * 0.003;
      const points = [
        { x: cx - rx * 0.45, y: cy - ry * 0.25 }, // Left eye
        { x: cx + rx * 0.45, y: cy - ry * 0.25 }, // Right eye
        { x: cx, y: cy },                         // Nose tip
        { x: cx - rx * 0.3, y: cy + ry * 0.4 },   // Left mouth
        { x: cx + rx * 0.3, y: cy + ry * 0.4 },   // Right mouth
        { x: cx, y: cy + ry * 0.65 }              // Chin
      ];

      points.forEach((pt, i) => {
        const jitterX = Math.sin(time + i) * 1.5;
        const jitterY = Math.cos(time + i) * 1.5;
        this.ctx.fillStyle = 'rgba(34, 211, 238, 0.8)';
        this.ctx.beginPath();
        this.ctx.arc(pt.x + jitterX, pt.y + jitterY, 2.5, 0, Math.PI * 2);
        this.ctx.fill();
      });

      // Connect landmarks with faint geometric polygon
      this.ctx.strokeStyle = 'rgba(34, 211, 238, 0.15)';
      this.ctx.beginPath();
      this.ctx.moveTo(points[0].x, points[0].y);
      this.ctx.lineTo(points[1].x, points[1].y);
      this.ctx.lineTo(points[4].x, points[4].y);
      this.ctx.lineTo(points[5].x, points[5].y);
      this.ctx.lineTo(points[3].x, points[3].y);
      this.ctx.closePath();
      this.ctx.stroke();
    }
  }

  initRadar() {
    if (!this.radarCanvasEl || !this.radarCtx) return;
    const rLoop = () => {
      this.drawRadar();
      this.radarAnimId = requestAnimationFrame(rLoop);
    };
    this.radarAnimId = requestAnimationFrame(rLoop);
  }

  updateDistance(meters) {
    this.distanceMeters = meters;
    const badge = document.getElementById('radarDistanceBadge');
    if (badge) {
      if (meters !== null && meters !== undefined) {
        badge.innerHTML = `🛰️ DISTANCE: <strong>${meters.toFixed(1)}m</strong> / ${this.maxRadiusMeters}m`;
        if (meters <= this.maxRadiusMeters) {
          badge.style.borderColor = 'rgba(52, 211, 153, 0.5)';
          badge.style.color = 'var(--green)';
        } else {
          badge.style.borderColor = 'rgba(248, 113, 113, 0.5)';
          badge.style.color = 'var(--red)';
        }
      }
    }
  }

  drawRadar() {
    const canvas = this.radarCanvasEl;
    const ctx = this.radarCtx;
    if (!canvas || !ctx) return;
    
    const w = canvas.width = canvas.offsetWidth;
    const h = canvas.height = canvas.offsetHeight;
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.42;

    ctx.clearRect(0, 0, w, h);

    // Concentric grid rings
    [0.33, 0.66, 1.0].forEach(factor => {
      ctx.beginPath();
      ctx.arc(cx, cy, radius * factor, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(34, 211, 238, 0.16)';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    // Crosshairs
    ctx.beginPath();
    ctx.moveTo(cx - radius, cy); ctx.lineTo(cx + radius, cy);
    ctx.moveTo(cx, cy - radius); ctx.lineTo(cx, cy + radius);
    ctx.strokeStyle = 'rgba(34, 211, 238, 0.12)';
    ctx.stroke();

    // Rotating sweep line
    this.radarAngle += 0.035;
    const sweepEndAngle = this.radarAngle;
    const sweepStartAngle = sweepEndAngle - 0.55;

    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    grad.addColorStop(0, 'rgba(34, 211, 238, 0)');
    grad.addColorStop(1, 'rgba(34, 211, 238, 0.3)');

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, sweepStartAngle, sweepEndAngle);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.restore();

    // Sweep leading edge
    const edgeX = cx + Math.cos(sweepEndAngle) * radius;
    const edgeY = cy + Math.sin(sweepEndAngle) * radius;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(edgeX, edgeY);
    ctx.strokeStyle = 'rgba(34, 211, 238, 0.8)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Center classroom beacon
    ctx.beginPath();
    ctx.arc(cx, cy, 4, 0, Math.PI * 2);
    ctx.fillStyle = 'var(--cyan)';
    ctx.fill();

    // Student location blip if distance is known
    if (this.distanceMeters !== null && this.distanceMeters !== undefined) {
      const normalizedDist = Math.min(this.distanceMeters / (this.maxRadiusMeters * 1.5), 1.0) * radius;
      const blipAngle = Math.PI * 0.35; // stationary simulated angle
      const blipX = cx + Math.cos(blipAngle) * normalizedDist;
      const blipY = cy + Math.sin(blipAngle) * normalizedDist;

      const isInside = this.distanceMeters <= this.maxRadiusMeters;
      ctx.beginPath();
      ctx.arc(blipX, blipY, 5, 0, Math.PI * 2);
      ctx.fillStyle = isInside ? 'var(--green)' : 'var(--red)';
      ctx.shadowColor = isInside ? 'rgba(52, 211, 153, 0.8)' : 'rgba(248, 113, 113, 0.8)';
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  setSuccess(confidence, message) {
    this.state = 'VERIFIED';
    if (this.hudWrapEl) {
      this.hudWrapEl.classList.remove('hud-failed');
      this.hudWrapEl.classList.add('hud-verified');
    }
    this.setStatus(`IDENTITY VERIFIED • ${(confidence * 100).toFixed(0)}% MATCH`, 'green');
    this.setStepState(1, 'done');
    this.setStepState(2, 'done');
    this.setStepState(3, 'done');
    this.setStepState(4, 'done');
    this.setStepState(5, 'done');
  }

  setFailure(reason) {
    this.state = 'FAILED';
    if (this.hudWrapEl) {
      this.hudWrapEl.classList.remove('hud-verified');
      this.hudWrapEl.classList.add('hud-failed');
    }
    this.setStatus(`FAILED: ${reason}`, 'red');
    this.setStepState(3, 'failed');
  }
}

window.FaceVisionHUD = FaceVisionHUD;
