/* ═══════════════════════════════════════════════════════════════
   LeAIrning — Apple-style Scroll Animations
   Techniques: Intersection Observer, Parallax, Word Reveal,
               Counter Animation, Stagger, Spring Physics
═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ── SPRING EASING ──────────────────────────────────────────── */
  // Cubic bezier matching Apple's spring feel
  const SPRING = 'cubic-bezier(0.16, 1, 0.3, 1)';
  const EASE_OUT = 'cubic-bezier(0.22, 1, 0.36, 1)';

  /* ── INTERSECTION OBSERVER FACTORY ─────────────────────────── */
  function makeObserver(callback, options = {}) {
    return new IntersectionObserver(callback, {
      threshold: options.threshold ?? 0.12,
      rootMargin: options.rootMargin ?? '0px 0px -60px 0px',
    });
  }

  /* ══════════════════════════════════════════════════════════════
     1. FADE-IN (base .fade-in already in CSS, enhanced here)
  ══════════════════════════════════════════════════════════════ */
  const fadeObs = makeObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        fadeObs.unobserve(e.target);
      }
    });
  });
  document.querySelectorAll('.fade-in').forEach((el) => fadeObs.observe(el));

  /* ══════════════════════════════════════════════════════════════
     2. STAGGER — children animate in sequence
        Usage: add data-stagger to a parent, children get delays
  ══════════════════════════════════════════════════════════════ */
  function initStagger() {
    document.querySelectorAll('[data-stagger]').forEach((parent) => {
      const delay = parseInt(parent.dataset.stagger || '80', 10);
      const children = Array.from(parent.children);
      children.forEach((child, i) => {
        child.style.opacity = '0';
        child.style.transform = 'translateY(28px)';
        child.style.transition = `opacity 0.65s ${SPRING} ${i * delay}ms, transform 0.65s ${SPRING} ${i * delay}ms`;
      });

      const obs = makeObserver((entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            Array.from(e.target.children).forEach((child) => {
              child.style.opacity = '1';
              child.style.transform = 'translateY(0)';
            });
            obs.unobserve(e.target);
          }
        });
      }, { threshold: 0.05 });

      obs.observe(parent);
    });
  }

  /* ══════════════════════════════════════════════════════════════
     3. WORD REVEAL — text splits into words, each fades in
        Usage: add class="word-reveal" to any heading/paragraph
  ══════════════════════════════════════════════════════════════ */
  function initWordReveal() {
    document.querySelectorAll('.word-reveal').forEach((el) => {
      const text = el.textContent.trim();
      const words = text.split(' ');
      el.innerHTML = words
        .map(
          (w, i) =>
            `<span class="wr-word" style="display:inline-block;opacity:0;transform:translateY(22px) rotateX(12deg);transition:opacity 0.55s ${SPRING} ${i * 55}ms,transform 0.55s ${SPRING} ${i * 55}ms;transform-origin:bottom center;">${w}&nbsp;</span>`
        )
        .join('');

      const obs = makeObserver((entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.querySelectorAll('.wr-word').forEach((span) => {
              span.style.opacity = '1';
              span.style.transform = 'translateY(0) rotateX(0deg)';
            });
            obs.unobserve(e.target);
          }
        });
      }, { threshold: 0.3 });

      obs.observe(el);
    });
  }

  /* ══════════════════════════════════════════════════════════════
     4. COUNTER ANIMATION — numbers count up on scroll
        Usage: add data-target="number" to .stat-num elements
  ══════════════════════════════════════════════════════════════ */
  function animateCount(el, target, duration = 1800) {
    const isFloat = String(target).includes('.');
    const decimals = isFloat ? 1 : 0;
    const start = performance.now();
    const from = 0;

    function step(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out expo
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = from + (target - from) * eased;
      el.textContent = current.toFixed(decimals);
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = target.toFixed(decimals);
    }
    requestAnimationFrame(step);
  }

  function initCounters() {
    const counters = document.querySelectorAll('[data-target]');
    const obs = makeObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          const target = parseFloat(e.target.dataset.target);
          animateCount(e.target, target);
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach((c) => obs.observe(c));
  }

  /* ══════════════════════════════════════════════════════════════
     5. PARALLAX — elements move at different scroll speeds
        Usage: add data-parallax="0.3" (speed 0–1, lower = slower)
  ══════════════════════════════════════════════════════════════ */
  function initParallax() {
    const els = document.querySelectorAll('[data-parallax]');
    if (!els.length) return;

    let ticking = false;
    function onScroll() {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          els.forEach((el) => {
            const speed = parseFloat(el.dataset.parallax || '0.3');
            const rect = el.getBoundingClientRect();
            const centerY = rect.top + rect.height / 2 + scrollY - window.innerHeight / 2;
            const offset = centerY * speed * -1;
            el.style.transform = `translateY(${offset}px)`;
          });
          ticking = false;
        });
        ticking = true;
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════
     6. SCALE-IN — cards scale from 0.94 with blur
        Usage: add class="scale-in" to cards/sections
  ══════════════════════════════════════════════════════════════ */
  function initScaleIn() {
    document.querySelectorAll('.scale-in').forEach((el) => {
      el.style.opacity = '0';
      el.style.transform = 'scale(0.94) translateY(20px)';
      el.style.filter = 'blur(4px)';
      el.style.transition = `opacity 0.7s ${SPRING}, transform 0.7s ${SPRING}, filter 0.7s ${SPRING}`;
    });

    const obs = makeObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.style.opacity = '1';
          e.target.style.transform = 'scale(1) translateY(0)';
          e.target.style.filter = 'blur(0px)';
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.08 });

    document.querySelectorAll('.scale-in').forEach((el) => obs.observe(el));
  }

  /* ══════════════════════════════════════════════════════════════
     7. SLIDE-IN — elements slide from left/right/bottom
        Usage: data-slide="left|right|bottom"
  ══════════════════════════════════════════════════════════════ */
  function initSlideIn() {
    const map = {
      left:   'translateX(-40px)',
      right:  'translateX(40px)',
      bottom: 'translateY(40px)',
      top:    'translateY(-40px)',
    };

    document.querySelectorAll('[data-slide]').forEach((el) => {
      const dir = el.dataset.slide || 'bottom';
      el.style.opacity = '0';
      el.style.transform = map[dir] || map.bottom;
      el.style.transition = `opacity 0.7s ${SPRING}, transform 0.7s ${SPRING}`;
    });

    const obs = makeObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.style.opacity = '1';
          e.target.style.transform = 'translate(0)';
          obs.unobserve(e.target);
        }
      });
    });

    document.querySelectorAll('[data-slide]').forEach((el) => obs.observe(el));
  }

  /* ══════════════════════════════════════════════════════════════
     8. SECTION REVEAL — section title line draws in
        Adds a gradient underline that expands on scroll
  ══════════════════════════════════════════════════════════════ */
  function initSectionReveals() {
    document.querySelectorAll('.section-label').forEach((label) => {
      const title = label.querySelector('.section-title');
      const badge = label.querySelector('.section-badge');
      const sub   = label.querySelector('.section-sub');

      if (badge) {
        badge.style.opacity = '0';
        badge.style.transform = 'translateY(10px)';
        badge.style.transition = `opacity 0.5s ${SPRING}, transform 0.5s ${SPRING}`;
      }
      if (title) {
        title.style.opacity = '0';
        title.style.transform = 'translateY(20px)';
        title.style.transition = `opacity 0.6s ${SPRING} 0.1s, transform 0.6s ${SPRING} 0.1s`;
      }
      if (sub) {
        sub.style.opacity = '0';
        sub.style.transform = 'translateY(16px)';
        sub.style.transition = `opacity 0.6s ${SPRING} 0.2s, transform 0.6s ${SPRING} 0.2s`;
      }

      const obs = makeObserver((entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            if (badge) { badge.style.opacity = '1'; badge.style.transform = 'translateY(0)'; }
            if (title) { title.style.opacity = '1'; title.style.transform = 'translateY(0)'; }
            if (sub)   { sub.style.opacity   = '1'; sub.style.transform   = 'translateY(0)'; }
            obs.unobserve(e.target);
          }
        });
      }, { threshold: 0.3 });

      obs.observe(label);
    });
  }

  /* ══════════════════════════════════════════════════════════════
     9. BENTO GRID STAGGER — feat-cards animate with wave pattern
  ══════════════════════════════════════════════════════════════ */
  function initBentoGrid() {
    const grid = document.querySelector('.bento-grid');
    if (!grid) return;

    const cards = Array.from(grid.querySelectorAll('.feat-card'));
    cards.forEach((card, i) => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(30px) scale(0.96)';
      card.style.transition = `opacity 0.6s ${SPRING} ${i * 70}ms, transform 0.6s ${SPRING} ${i * 70}ms`;
    });

    const obs = makeObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          cards.forEach((card) => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0) scale(1)';
          });
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.05 });

    obs.observe(grid);
  }

  /* ══════════════════════════════════════════════════════════════
     10. HERO ENTRANCE — cinematic sequence on load
  ══════════════════════════════════════════════════════════════ */
  function initHeroEntrance() {
    const hero = document.querySelector('#hero');
    if (!hero) return;

    const badge   = hero.querySelector('.hero-badge');
    const title   = hero.querySelector('.hero-title');
    const sub     = hero.querySelector('.hero-sub');
    const ctas    = hero.querySelector('.hero-ctas');
    const stats   = hero.querySelectorAll('.stat-item');

    const els = [badge, title, sub, ctas].filter(Boolean);
    els.forEach((el, i) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(24px)';
      el.style.transition = `opacity 0.7s ${SPRING} ${200 + i * 120}ms, transform 0.7s ${SPRING} ${200 + i * 120}ms`;
    });

    stats.forEach((stat, i) => {
      stat.style.opacity = '0';
      stat.style.transform = 'translateY(16px)';
      stat.style.transition = `opacity 0.6s ${SPRING} ${700 + i * 100}ms, transform 0.6s ${SPRING} ${700 + i * 100}ms`;
    });

    // Trigger after first paint
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        els.forEach((el) => {
          el.style.opacity = '1';
          el.style.transform = 'translateY(0)';
        });
        stats.forEach((stat) => {
          stat.style.opacity = '1';
          stat.style.transform = 'translateY(0)';
        });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     11. SCROLL PROGRESS BAR — thin line at top of page
  ══════════════════════════════════════════════════════════════ */
  function initProgressBar() {
    const bar = document.createElement('div');
    bar.id = 'scroll-progress';
    bar.style.cssText = `
      position: fixed;
      top: 0; left: 0;
      height: 2px;
      width: 0%;
      background: linear-gradient(90deg, #6366f1, #22d3ee);
      z-index: 9999;
      transition: width 0.1s linear;
      pointer-events: none;
    `;
    document.body.appendChild(bar);

    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      bar.style.width = pct + '%';
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════
     12. CARD HOVER — magnetic push effect on mouse move
  ══════════════════════════════════════════════════════════════ */
  function initMagneticCards() {
    const cards = document.querySelectorAll('.feat-card, .level-card, .comm-card');
    cards.forEach((card) => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = (e.clientX - cx) / (rect.width / 2);
        const dy = (e.clientY - cy) / (rect.height / 2);
        card.style.transform = `translateY(-4px) rotateX(${dy * -3}deg) rotateY(${dx * 3}deg)`;
        card.style.transition = 'transform 0.1s ease';
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
        card.style.transition = `transform 0.5s ${SPRING}`;
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     13. GLOWING CURSOR TRAIL (subtle, Apple Vision-style)
  ══════════════════════════════════════════════════════════════ */
  function initCursorGlow() {
    const glow = document.createElement('div');
    glow.style.cssText = `
      position: fixed;
      width: 400px; height: 400px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 65%);
      pointer-events: none;
      z-index: 0;
      transform: translate(-50%, -50%);
      transition: left 0.8s ease, top 0.8s ease;
      will-change: left, top;
    `;
    document.body.appendChild(glow);

    let lastX = -1000, lastY = -1000;
    window.addEventListener('mousemove', (e) => {
      if (Math.abs(e.clientX - lastX) > 5 || Math.abs(e.clientY - lastY) > 5) {
        glow.style.left = e.clientX + 'px';
        glow.style.top  = e.clientY + 'px';
        lastX = e.clientX;
        lastY = e.clientY;
      }
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════
     14. LEVEL CARDS — stagger on scroll
  ══════════════════════════════════════════════════════════════ */
  function initLevelCards() {
    const grid = document.querySelector('.levels-grid');
    if (!grid) return;
    const cards = Array.from(grid.querySelectorAll('.level-card'));
    cards.forEach((card, i) => {
      card.classList.remove('fade-in'); // handled manually
      card.style.opacity = '0';
      card.style.transform = 'translateY(36px)';
      card.style.transition = `opacity 0.65s ${SPRING} ${i * 100}ms, transform 0.65s ${SPRING} ${i * 100}ms`;
    });

    const obs = makeObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          cards.forEach((c) => {
            c.style.opacity = '1';
            c.style.transform = 'translateY(0)';
          });
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.05 });

    obs.observe(grid);
  }

  /* ══════════════════════════════════════════════════════════════
     15. DEMO CARDS — slide in from sides
  ══════════════════════════════════════════════════════════════ */
  function initDemoCards() {
    const cards = document.querySelectorAll('#demo .demo-card');
    cards.forEach((card, i) => {
      card.classList.remove('fade-in');
      card.style.opacity = '0';
      card.style.transform = i === 0 ? 'translateX(-30px)' : 'translateX(30px)';
      card.style.transition = `opacity 0.7s ${SPRING} ${i * 150}ms, transform 0.7s ${SPRING} ${i * 150}ms`;
    });

    if (!cards.length) return;
    const obs = makeObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          cards.forEach((c) => {
            c.style.opacity = '1';
            c.style.transform = 'translate(0)';
          });
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.1 });

    obs.observe(document.getElementById('demo'));
  }

  /* ══════════════════════════════════════════════════════════════
     16. XP BAR ANIMATION — fills when dashboard section visible
  ══════════════════════════════════════════════════════════════ */
  function initXPBar() {
    const bar = document.querySelector('.xp-bar');
    if (!bar) return;
    const targetWidth = bar.style.width || '0%';
    bar.style.width = '0%';

    const obs = makeObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          setTimeout(() => { bar.style.width = targetWidth; }, 300);
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });

    const wrap = document.querySelector('.xp-bar-wrap');
    if (wrap) obs.observe(wrap);
  }

  /* ══════════════════════════════════════════════════════════════
     17. CTA SECTION — split reveal
  ══════════════════════════════════════════════════════════════ */
  function initCTA() {
    const cta = document.querySelector('#cta');
    if (!cta) return;
    const title    = cta.querySelector('.cta-title');
    const sub      = cta.querySelector('.cta-sub');
    const benefits = cta.querySelector('.cta-benefits');
    const btns     = cta.querySelector('.hero-ctas');

    [[title, 0], [sub, 120], [benefits, 240], [btns, 360]].forEach(([el, delay]) => {
      if (!el) return;
      el.style.opacity = '0';
      el.style.transform = 'translateY(28px)';
      el.style.transition = `opacity 0.7s ${SPRING} ${delay}ms, transform 0.7s ${SPRING} ${delay}ms`;
    });

    const obs = makeObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          [title, sub, benefits, btns].filter(Boolean).forEach((el) => {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
          });
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.2 });

    obs.observe(cta);
  }

  /* ══════════════════════════════════════════════════════════════
     INIT ALL
  ══════════════════════════════════════════════════════════════ */
  function init() {
    // Respect prefers-reduced-motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    initHeroEntrance();
    initProgressBar();
    initCursorGlow();
    initCounters();
    initParallax();
    initWordReveal();
    initStagger();
    initScaleIn();
    initSlideIn();
    initSectionReveals();
    initBentoGrid();
    initLevelCards();
    initDemoCards();
    initXPBar();
    initCTA();

    // Magnetic cards — only on non-touch devices
    if (!('ontouchstart' in window)) {
      initMagneticCards();
    }

    // Re-observe fade-ins that may have been added later
    setTimeout(() => {
      document.querySelectorAll('.fade-in:not(.visible)').forEach((el) => fadeObs.observe(el));
    }, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
