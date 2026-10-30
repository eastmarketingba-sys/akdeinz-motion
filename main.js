/* ==========================================================================
   Akdeinz Motion — interactions
   Everything moves on the 60° axis with one easing: cubic-bezier(.2,.8,.2,1)
   ========================================================================== */
(() => {
  "use strict";

  const doc = document.documentElement;
  doc.classList.add("js");

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, t) => a + (b - a) * t;

  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = matchMedia("(pointer: fine)").matches;
  const DPR = Math.min(window.devicePixelRatio || 1, 2);
  const TAN60 = Math.sqrt(3);
  const AX = 0.5, AY = Math.sqrt(3) / 2; // unit vector of the 60° axis

  // Brand easing cubic-bezier(0.2, 0.8, 0.2, 1), solved for x → y.
  const ease = (() => {
    const x1 = 0.2, y1 = 0.8, x2 = 0.2, y2 = 1;
    const bez = (t, a, b) => 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3;
    return (x) => {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      let lo = 0, hi = 1, t = x;
      for (let i = 0; i < 18; i++) {
        t = (lo + hi) / 2;
        if (bez(t, x1, x2) < x) lo = t; else hi = t;
      }
      return bez(t, y1, y2);
    };
  })();

  const COLORS = {
    white: "#ffffff", fold: "#e6e6e6", foldDark: "#cccccc",
    carbon: "#191919", blue: "#2e6bff", aegean: "#0b35c9", black: "#000000",
  };

  /* Parallelogram with horizontal top/bottom and 60° sides — the brand band.
     (x, y) = bottom-left corner, w = horizontal width, h = height.
     lean = 1 rises to the right ( / ), lean = -1 rises to the left ( \ ). */
  function band(ctx, x, y, w, h, lean = 1) {
    const k = (h / TAN60) * lean;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + w, y);
    ctx.lineTo(x + w + k, y - h);
    ctx.lineTo(x + k, y - h);
    ctx.closePath();
  }

  function poly(ctx, pts) {
    ctx.beginPath();
    ctx.moveTo(pts[0], pts[1]);
    for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]);
    ctx.closePath();
  }

  // Mark geometry from the master SVG, shifted to start at x = 0.
  const MARK = (() => {
    const o = 107.67;
    const shift = (a) => a.map((v, i) => (i % 2 === 0 ? v - o : v));
    return {
      bands: [
        [[217.87, 0, 307.11, 0, 196.91, 191.32, 107.67, 191.32], [158.38, 132.51, 267.07, 132.51, 300.95, 191.32, 158.38, 191.32]],
        [[313.87, 0, 224.63, 0, 334.83, 191.32, 424.07, 191.32]],
        [[522.06, 161.92, 432.81, 161.92, 339.56, 0, 428.8, 0]],
        [[555.23, 0, 465.99, 0, 576.19, 191.32, 665.43, 191.32]],
      ].map((g) => g.map(shift)),
      folds: [
        [555.23, 0, 521.97, 161.92, 432.81, 161.92, 465.88, 0],
        [428.94, 0, 395.68, 161.92, 324.35, 161.92, 311.36, 138.2, 339.58, 0],
      ].map(shift),
    };
  })();

  /* ---------------- shared canvas loop ---------------- */
  const scenes = new Set();
  const visible = new WeakSet();

  function fit(canvas) {
    const r = canvas.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width * DPR));
    const h = Math.max(1, Math.round(r.height * DPR));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      return true;
    }
    return false;
  }

  const io = new IntersectionObserver((entries) => {
    for (const e of entries) e.isIntersecting ? visible.add(e.target) : visible.delete(e.target);
  }, { rootMargin: "100px" });

  function addScene(canvas, draw, init) {
    const ctx = canvas.getContext("2d");
    const scene = { canvas, ctx, draw, state: null, init, t0: performance.now() };
    fit(canvas);
    scene.state = init ? init(canvas.width, canvas.height) : null;
    scenes.add(scene);
    io.observe(canvas);
    if (reduced) renderScene(scene, 2.2);
    return scene;
  }

  function renderScene(s, t, dt = 0) {
    if (fit(s.canvas) && s.init) s.state = s.init(s.canvas.width, s.canvas.height);
    const { ctx, canvas } = s;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    s.draw(ctx, canvas.width, canvas.height, t, dt, s.state);
  }

  /* ---------------- motion studies ----------------
     Stand-ins for project footage until real clips are added.
     Each is a short piece built only from the brand band. */

  // Drifting field of bands rising on the 60° axis. Used for hero + reel.
  function makeField(palette, density = 1) {
    return {
      init(W, H) {
        const n = Math.round((W * H) / (90000 * DPR * DPR) * density) + 10;
        const spawn = (depth, initial) => {
          const h = (60 + depth * 340) * DPR;
          const w = (6 + Math.pow(Math.random(), 3) * 120) * DPR * (0.4 + depth);
          const color = palette[Math.floor(Math.random() * palette.length)];
          // enter from the bottom/left edge so every band rises across the frame
          const x = Math.random() * (W + H / TAN60) - H / TAN60;
          const y = initial ? Math.random() * (H + h) : H + h + Math.random() * H * 0.3;
          return { x, y, w, h, depth, color, speed: (14 + depth * 46) * DPR };
        };
        const items = Array.from({ length: n }, (_, i) => spawn(i / n, true));
        return { items, spawn, px: 0, py: 0 };
      },
      draw(ctx, W, H, t, dt, st) {
        ctx.clearRect(0, 0, W, H);
        const boost = 1 + Math.min(6, Math.abs(scrollVel) * 0.06);
        st.px = lerp(st.px, pointer.nx, 0.05);
        st.py = lerp(st.py, pointer.ny, 0.05);
        for (let i = 0; i < st.items.length; i++) {
          const b = st.items[i];
          const d = b.speed * boost * dt;
          b.x += AX * d;
          b.y -= AY * d;
          if (b.y < -4 || b.x - b.h > W + 40 * DPR) {
            st.items[i] = st.spawn(b.depth, false);
            continue;
          }
          const ox = st.px * 30 * DPR * b.depth;
          const oy = st.py * 20 * DPR * b.depth;
          ctx.fillStyle = b.color;
          band(ctx, b.x + ox, b.y + oy, b.w, b.h, 1);
          ctx.fill();
        }
      },
    };
  }

  const studies = {
    // The logo sting itself: bands slide in L→R on their axis, fold fades up, hold, exit.
    rise(ctx, W, H, t) {
      ctx.fillStyle = COLORS.carbon; ctx.fillRect(0, 0, W, H);
      const period = 4.6, tt = t % period;
      const MW = 557.76, MH = 191.32;
      const s = Math.min((W * 0.62) / MW, (H * 0.4) / MH);
      ctx.save();
      ctx.translate((W - MW * s) / 2, (H - MH * s) / 2);
      ctx.scale(s, s);
      ctx.beginPath(); ctx.rect(0, 0, MW, MH); ctx.clip();
      const foldIn = ease(clamp((tt - 0.82) / 0.4)) * (1 - ease(clamp((tt - 3.2) / 0.25)));
      ctx.globalAlpha = foldIn;
      ctx.fillStyle = COLORS.fold;
      for (const f of MARK.folds) { poly(ctx, f); ctx.fill(); }
      ctx.globalAlpha = 1;
      MARK.bands.forEach((group, i) => {
        const tin = ease(clamp((tt - i * 0.08) / 0.6));
        const tout = ease(clamp((tt - 3.3 - i * 0.08) / 0.28));
        const up = i === 0;
        const d = (1 - tin) * -260 + tout * 260;
        ctx.save();
        ctx.translate(d * AX, (up ? -1 : 1) * d * AY);
        ctx.fillStyle = COLORS.white;
        for (const pts of group) { poly(ctx, pts); ctx.fill(); }
        ctx.restore();
      });
      ctx.restore();
    },

    // Thin 60° slats breathing in width — a shutter.
    shutter(ctx, W, H, t) {
      ctx.fillStyle = COLORS.carbon; ctx.fillRect(0, 0, W, H);
      const n = 16, step = (W + H / TAN60) / n;
      const drift = (t * 18 * DPR) % step;
      for (let i = -1; i < n + 1; i++) {
        const phase = Math.sin(t * 1.6 - i * 0.45);
        const w = step * (0.08 + 0.42 * (0.5 + 0.5 * phase));
        const x = i * step - H / TAN60 + drift;
        ctx.fillStyle = i % 7 === 3 ? COLORS.blue : COLORS.white;
        band(ctx, x, H, w, H, 1);
        ctx.fill();
      }
    },

    // Mediterranean swell: rows of bands whose height follows a wave.
    wave(ctx, W, H, t) {
      ctx.fillStyle = COLORS.carbon; ctx.fillRect(0, 0, W, H);
      const cols = 14, rows = 9;
      const cw = W / cols, rh = H / rows;
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols + 1; c++) {
          const v = Math.sin(c * 0.55 - t * 1.8 + r * 0.7) * 0.5 + 0.5;
          const h = rh * (0.12 + 0.82 * ease(v));
          const x = c * cw - (r % 2) * cw * 0.5;
          const y = (r + 1) * rh;
          ctx.fillStyle = v > 0.94 ? COLORS.blue : COLORS.white;
          band(ctx, x, y, cw * 0.28, h, 1);
          ctx.fill();
        }
      }
    },

    // A ribbon pulled through a frame; past the edge it bends into the fold.
    fold(ctx, W, H, t) {
      ctx.fillStyle = COLORS.carbon; ctx.fillRect(0, 0, W, H);
      const edge = W * 0.56;
      const bh = H * 1.2, bw = W * 0.16;
      for (let i = 0; i < 4; i++) {
        const p = ((t * 0.16 + i * 0.25) % 1);
        const travel = W + bh / TAN60 + bw;
        const x = -bw - bh / TAN60 + ease(p) * travel * 0.4 + p * travel * 0.6;
        const y = H + H * 0.1;
        ctx.save();
        ctx.beginPath(); ctx.rect(0, 0, edge, H); ctx.clip();
        ctx.fillStyle = COLORS.white; band(ctx, x, y, bw, bh, 1); ctx.fill();
        ctx.restore();
        // folded side: mirrored lean, fold-grey, with the darker crease
        ctx.save();
        ctx.beginPath(); ctx.rect(edge, 0, W - edge, H); ctx.clip();
        const mx = 2 * edge - x - bw;
        ctx.fillStyle = COLORS.fold; band(ctx, mx, y, bw, bh, -1); ctx.fill();
        ctx.fillStyle = COLORS.foldDark; band(ctx, edge, y, bw * 0.18, bh, -1); ctx.fill();
        ctx.restore();
      }
      ctx.fillStyle = COLORS.black;
      ctx.fillRect(edge - DPR, 0, 2 * DPR, H);
    },

    // Bars stack upward, then clear — the mark "climbs".
    stack(ctx, W, H, t) {
      ctx.fillStyle = COLORS.carbon; ctx.fillRect(0, 0, W, H);
      const period = 5, tt = t % period, n = 8;
      const bh = H / (n + 2);
      for (let i = 0; i < n; i++) {
        const tin = ease(clamp((tt - i * 0.12) / 0.55));
        const tout = ease(clamp((tt - 3.6 - (n - i) * 0.05) / 0.3));
        const w = W * (0.18 + 0.5 * ((Math.sin(i * 2.3) + 1) / 2));
        const yb = H - bh * (i + 1);
        const xTarget = W * 0.12 + i * bh / TAN60;
        const D = W;
        const off = (1 - tin) * -D + tout * D;
        ctx.fillStyle = i === n - 1 ? COLORS.blue : COLORS.white;
        band(ctx, xTarget + off * AX, yb - off * AY * 0.02, w, bh * 0.82, 1);
        ctx.fill();
      }
    },

    // Nested bands receding into the frame.
    tunnel(ctx, W, H, t) {
      ctx.fillStyle = COLORS.carbon; ctx.fillRect(0, 0, W, H);
      const cx = W / 2, cy = H / 2;
      const f = (t * 0.35) % 1;
      const n = 14;
      for (let k = n; k >= 0; k--) {
        const s = Math.pow(1.32, k - f) * Math.min(W, H) * 0.035;
        const h = s * 1.6, w = s * 1.1;
        const idx = k - Math.floor(t * 0.35);
        ctx.fillStyle = idx % 2 === 0 ? COLORS.white : COLORS.black;
        if (((idx % 9) + 9) % 9 === 4) ctx.fillStyle = COLORS.blue;
        band(ctx, cx - w / 2 - h / TAN60 / 2, cy + h / 2, w, h, 1);
        ctx.fill();
      }
    },
  };

  /* ---------------- pointer + scroll state ---------------- */
  const pointer = { x: innerWidth / 2, y: innerHeight / 2, nx: 0, ny: 0 };
  addEventListener("pointermove", (e) => {
    pointer.x = e.clientX; pointer.y = e.clientY;
    pointer.nx = e.clientX / innerWidth - 0.5;
    pointer.ny = e.clientY / innerHeight - 0.5;
  }, { passive: true });

  let scrollVel = 0, lastY = scrollY;

  /* ---------------- hero ---------------- */
  const field = $("[data-field]");
  if (field) {
    const f = makeField(["#0d0d0d", "#121212", COLORS.carbon, COLORS.carbon, "#222", "#1c1c1c", COLORS.aegean], 0.8);
    addScene(field, f.draw, f.init);
  }

  const bands = $$("[data-band]");
  const mark = $("[data-mark]");
  const hero = $("[data-hero]");
  const heroText = hero ? $$("[data-reveal]", hero) : [];

  function startSting() {
    requestAnimationFrame(() => {
      document.body.classList.remove("is-loading");
      // after the sting (≈1.2 s) hand the bands to scroll
      setTimeout(() => { mark && mark.classList.add("is-live"); hero && hero.classList.add("is-live"); updateScroll(); }, reduced ? 0 : 1300);
    });
  }
  if (document.fonts && document.fonts.ready) {
    Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 900))]).then(startSting);
  } else startSting();

  /* ---------------- reel ---------------- */
  const reel = $("[data-reel]");
  const reelWin = $("[data-reel-window]");
  const reelVideo = $("[data-reel-video]");
  const reelSound = $("[data-reel-sound]");
  const reelCanvas = reelWin && $("canvas", reelWin);
  if (reelCanvas) {
    const f = makeField([COLORS.white, COLORS.white, COLORS.fold, "#2a2a2a", "#2a2a2a", "#111", "#111", "#111", COLORS.blue], 1.4);
    addScene(reelCanvas, f.draw, f.init);
  }
  if (reelVideo && reelVideo.dataset.src) {
    reelVideo.src = reelVideo.dataset.src;
    reelVideo.preload = "auto";
    reelVideo.addEventListener("canplay", () => {
      reelVideo.classList.add("is-ready");
      if (reelCanvas) reelCanvas.style.visibility = "hidden";
      reelSound.hidden = false;
    }, { once: true });
    new IntersectionObserver(([e]) => {
      e.isIntersecting ? reelVideo.play().catch(() => {}) : reelVideo.pause();
    }, { threshold: 0.2 }).observe(reelWin);
    reelSound.addEventListener("click", () => {
      reelVideo.muted = !reelVideo.muted;
      $("[data-sound-label]", reelSound).textContent = reelVideo.muted ? "Sound on" : "Sound off";
    });
  }

  /* ---------------- scroll-driven ---------------- */
  function updateScroll() {
    const vh = innerHeight, vw = innerWidth, y = scrollY;

    // Hero: bands leave along their own axis, in the same left → right order.
    if (mark && mark.classList.contains("is-live")) {
      const p = clamp(y / (vh * 0.75));
      bands.forEach((b, i) => {
        const pi = reduced ? 0 : ease(clamp((p - i * 0.07) / 0.72));
        const up = b.dataset.axis === "up";
        const d = pi * 420;
        b.style.transform = `translate(${d * AX}px, ${(up ? -1 : 1) * d * AY}px)`;
      });
      const fold = $("[data-fold]");
      if (fold) fold.style.opacity = String(1 - clamp(p * 2.2));
      for (const el of heroText) {
        el.style.opacity = String(1 - clamp(p * 1.6));
        el.style.transform = `translate(${p * 40 * AX}px, ${-p * 40 * AY}px)`;
      }
    }

    // Reel: a single 60° band opens into the full frame.
    if (reel && reelWin) {
      const top = reel.offsetTop;
      const lin = clamp((y - top + vh * 0.5) / (vh * 1.3));
      const p = reduced ? 1 : lin * lin * (3 - 2 * lin); // scrubbed by scroll, so a symmetric curve
      const w0 = vw * 0.16, k = vh / TAN60;
      const cx = vw / 2;
      const s = [
        [cx - w0 / 2 + k / 2, 0], [cx + w0 / 2 + k / 2, 0],
        [cx + w0 / 2 - k / 2, vh], [cx - w0 / 2 - k / 2, vh],
      ];
      const e = [[0, 0], [vw, 0], [vw, vh], [0, vh]];
      const pts = s.map((pt, i) => `${lerp(pt[0], e[i][0], p).toFixed(1)}px ${lerp(pt[1], e[i][1], p).toFixed(1)}px`);
      reelWin.style.clipPath = `polygon(${pts.join(",")})`;
    }
  }
  addEventListener("scroll", updateScroll, { passive: true });
  addEventListener("resize", updateScroll);
  updateScroll();

  /* ---------------- work tiles ---------------- */
  for (const c of $$("canvas[data-study]")) {
    const name = c.dataset.study;
    if (studies[name]) addScene(c, studies[name]);
  }

  const lightbox = $("[data-lightbox]");
  const lbVideo = $("[data-lightbox-video]");
  function openLightbox(src) {
    lbVideo.src = src;
    lightbox.hidden = false;
    document.body.style.overflow = "hidden";
    lbVideo.play().catch(() => {});
    $("[data-lightbox-close]").focus();
  }
  function closeLightbox() {
    lbVideo.pause();
    lbVideo.removeAttribute("src");
    lbVideo.load();
    lightbox.hidden = true;
    document.body.style.overflow = "";
  }
  $("[data-lightbox-close]").addEventListener("click", closeLightbox);
  lightbox.addEventListener("click", (e) => { if (e.target === lightbox) closeLightbox(); });
  addEventListener("keydown", (e) => { if (e.key === "Escape" && !lightbox.hidden) closeLightbox(); });

  const tileIO = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("is-in"); tileIO.unobserve(e.target); }
  }, { threshold: 0.15 });

  for (const tile of $$("[data-tile]")) {
    tileIO.observe(tile);
    const src = tile.dataset.video;
    if (!src) continue;
    tile.tabIndex = 0;
    tile.setAttribute("role", "button");
    tile.setAttribute("aria-label", `Play ${$("h3", tile).textContent}`);
    let v;
    tile.addEventListener("mouseenter", () => {
      if (!v) {
        v = document.createElement("video");
        Object.assign(v, { src, muted: true, loop: true, playsInline: true });
        $(".tile__media", tile).appendChild(v);
      }
      v.play().then(() => tile.classList.add("is-playing")).catch(() => {});
    });
    tile.addEventListener("mouseleave", () => { if (v) { v.pause(); tile.classList.remove("is-playing"); } });
    tile.addEventListener("click", () => openLightbox(src));
    tile.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openLightbox(src); } });
  }

  /* ---------------- contact headline ---------------- */
  const title = $("[data-split]");
  if (title) {
    const words = title.textContent.trim().split(/\s+/);
    title.setAttribute("aria-label", title.textContent.trim());
    title.innerHTML = words
      .map((w, i) => `<span class="w" aria-hidden="true"><span style="--d:${i}">${w}</span></span>`)
      .join(" ");
    new IntersectionObserver(([e], obs) => {
      if (e.isIntersecting) { title.classList.add("is-in"); obs.disconnect(); }
    }, { threshold: 0.4 }).observe(title);
  }

  /* ---------------- copy email ---------------- */
  const copyBtn = $("[data-copy]");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      const label = $("[data-copy-label]", copyBtn);
      try {
        await navigator.clipboard.writeText(copyBtn.dataset.copy);
        label.textContent = "Copied";
      } catch {
        label.textContent = copyBtn.dataset.copy;
      }
      copyBtn.classList.add("is-done");
      setTimeout(() => { label.textContent = "Copy address"; copyBtn.classList.remove("is-done"); }, 2200);
    });
  }

  /* ---------------- Netlify form (AJAX, falls back to /thanks.html) ---------------- */
  const form = $("[data-form]");
  if (form) {
    const status = $("[data-status]");
    const send = $("[data-send]");
    const sendLabel = $("[data-send-label]");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }
      send.disabled = true;
      sendLabel.textContent = "Sending…";
      status.className = "form__status";
      status.textContent = "";
      try {
        const res = await fetch("/", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams(new FormData(form)).toString(),
        });
        if (!res.ok) throw new Error(res.status);
        form.reset();
        sendLabel.textContent = "Sent";
        status.classList.add("is-ok");
        status.textContent = "Thanks — message received. I’ll be in touch.";
      } catch {
        sendLabel.textContent = "Send";
        status.classList.add("is-err");
        status.textContent = "Couldn’t send. Please email me directly.";
      } finally {
        send.disabled = false;
        setTimeout(() => { if (sendLabel.textContent === "Sent") sendLabel.textContent = "Send"; }, 3000);
      }
    });
  }

  /* ---------------- cursor ---------------- */
  const cursor = $("[data-cursor]");
  const cursorLabel = $("[data-cursor-label]");
  const cur = { x: pointer.x, y: pointer.y };
  if (finePointer && !reduced && cursor) {
    document.addEventListener("pointermove", () => document.body.classList.add("has-cursor"), { once: true });
    document.addEventListener("pointerover", (e) => {
      const tile = e.target.closest("[data-tile]");
      const hot = tile && tile.dataset.video;
      cursor.classList.toggle("is-label", !!hot);
      cursorLabel.textContent = hot ? "Play" : "";
      cursor.classList.toggle("is-hidden", !!e.target.closest("input, textarea"));
    });
    document.addEventListener("pointerleave", () => document.body.classList.remove("has-cursor"));
  }

  /* ---------------- main loop ---------------- */
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;

    const y = scrollY;
    scrollVel = lerp(scrollVel, (y - lastY) / Math.max(dt, 0.001) / 60, 0.1);
    lastY = y;

    if (!reduced) {
      for (const s of scenes) {
        if (!visible.has(s.canvas)) continue;
        renderScene(s, (now - s.t0) / 1000, dt);
      }
    }

    if (finePointer && !reduced && cursor) {
      cur.x = lerp(cur.x, pointer.x, 0.22);
      cur.y = lerp(cur.y, pointer.y, 0.22);
      cursor.style.transform = `translate(${cur.x}px, ${cur.y}px)`;
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  const yr = $("[data-year]");
  if (yr) yr.textContent = new Date().getFullYear();
})();
