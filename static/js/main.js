document.addEventListener('DOMContentLoaded', function () {
  // ===== State =====
  var currentRole = 'student';
  var currentMode = 'login';

  // ===== Navigation Scroll Effect =====
  var nav = document.querySelector('.nav');
  if (nav) {
    window.addEventListener('scroll', function () {
      nav.classList.toggle('scrolled', window.scrollY > 10);
    });
  }

  // ===== Mobile Menu Toggle =====
  var navToggle = document.querySelector('.nav__toggle');
  var navLinks = document.querySelector('.nav__links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function () {
      navLinks.classList.toggle('open');
      var isOpen = navLinks.classList.contains('open');
      navToggle.setAttribute('aria-expanded', isOpen);
    });

    // Close menu when clicking a link
    navLinks.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        navLinks.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // ===== Smooth Scroll =====
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var targetId = this.getAttribute('href');
      if (targetId === '#') return;
      // Skip auth-switch-links
      if (this.classList.contains('auth-switch-link')) return;
      var target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ===== Role Slider Toggle =====
  var roleOptions = document.querySelectorAll('.role-slider__option');
  var roleIndicator = document.getElementById('role-indicator');
  var allAuthForms = document.querySelectorAll('.auth-form');

  function showActiveForm() {
    allAuthForms.forEach(function (form) {
      var matchesRole = form.dataset.role === currentRole;
      var matchesMode = form.dataset.mode === currentMode;
      if (matchesRole && matchesMode) {
        form.classList.add('active');
      } else {
        form.classList.remove('active');
      }
    });
  }

  function updateRoleIndicator() {
    if (roleIndicator) {
      if (currentRole === 'teacher') {
        roleIndicator.classList.add('teacher');
      } else {
        roleIndicator.classList.remove('teacher');
      }
    }
  }

  roleOptions.forEach(function (option) {
    option.addEventListener('click', function () {
      var newRole = this.dataset.role;
      if (newRole === currentRole) return;

      currentRole = newRole;
      // Update active state on slider buttons
      roleOptions.forEach(function (opt) {
        opt.classList.toggle('active', opt.dataset.role === currentRole);
      });

      updateRoleIndicator();

      // Reset to login mode when switching roles
      currentMode = 'login';
      showActiveForm();
    });
  });

  // ===== Auth Mode Switch (Login/Register text links) =====
  document.querySelectorAll('.auth-switch-link').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      var targetMode = this.dataset.targetMode;
      if (targetMode === currentMode) return;
      currentMode = targetMode;
      showActiveForm();
    });
  });

  // ===== Toast Notifications =====
  var activeToastMessages = new Set();

  function dismissToast(toast) {
    var message = toast.querySelector('.toast__message');
    if (message) {
      activeToastMessages.delete(message.textContent.trim());
    }
    toast.classList.add('dismissing');
    toast.addEventListener('animationend', function () {
      toast.remove();
    });
  }

  // Initialize existing toasts (from Django messages)
  document.querySelectorAll('.toast').forEach(function (toast) {
    var message = toast.querySelector('.toast__message');
    if (message) {
      var text = message.textContent.trim();
      if (activeToastMessages.has(text)) {
        toast.remove();
        return;
      }
      activeToastMessages.add(text);
    }

    // Dismiss button
    var dismissBtn = toast.querySelector('.toast__dismiss');
    if (dismissBtn) {
      dismissBtn.addEventListener('click', function () {
        dismissToast(toast);
      });
    }

    // Auto-dismiss after 5 seconds
    setTimeout(function () {
      if (toast.parentNode) {
        dismissToast(toast);
      }
    }, 5000);
  });

  // ===== Scroll to auth panel from nav CTA =====
  var loginCta = document.querySelector('.nav__cta[href="#auth"]');
  if (loginCta) {
    loginCta.addEventListener('click', function (e) {
      e.preventDefault();
      var authPanel = document.querySelector('.auth-panel');
      if (authPanel) {
        authPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Add brief highlight effect
        authPanel.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.2), ' + getComputedStyle(authPanel).boxShadow;
        setTimeout(function () {
          authPanel.style.boxShadow = '';
        }, 1500);
      }
    });
  }

  // ===== Theme Toggle System =====
  function getPreferredTheme() {
    var stored = localStorage.getItem('labsphere_theme');
    if (stored) return stored;
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('labsphere_theme', theme);
    var toggles = document.querySelectorAll('.theme-toggle');
    toggles.forEach(function (btn) {
      btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
      var icon = btn.querySelector('.theme-toggle__icon');
      if (icon) {
        icon.textContent = theme === 'dark' ? '☀️' : '🌙';
      }
      var text = btn.querySelector('.theme-toggle__text');
      if (text) {
        text.textContent = theme === 'dark' ? 'Light' : 'Dark';
      }
    });

    // Synchronize Monaco editor if open
    if (window.monaco && window.monacoEditorInstance) {
      window.monaco.editor.setTheme(theme === 'dark' ? 'vs-dark' : 'vs');
    }
  }

  // Initialize theme icons
  applyTheme(getPreferredTheme());

  // Attach click listeners to all theme toggle buttons
  document.addEventListener('click', function(e) {
    var toggleBtn = e.target.closest('.theme-toggle');
    if (toggleBtn) {
      var current = document.documentElement.getAttribute('data-theme') || 'light';
      var next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
    }
  });

  // Listen for OS system theme changes if not overridden
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
      if (!localStorage.getItem('labsphere_theme')) {
        applyTheme(e.matches ? 'dark' : 'light');
      }
    });
  }
});
