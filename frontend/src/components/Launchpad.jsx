import React, { useState, useEffect } from 'react';
import { Rocket, Globe, Shield, Sparkles, CheckCircle2, AlertTriangle, Sliders, Play, Laptop, Accessibility, Search } from 'lucide-react';
import { validateUrl, startScan } from '../api/client';

export default function Launchpad({ onScanStarted }) {
  const [url, setUrl] = useState('http://localhost:8080');
  const [maxDepth, setMaxDepth] = useState(2);
  const [maxActions, setMaxActions] = useState(25);
  const [browser, setBrowser] = useState('chromium');
  const [headless, setHeadless] = useState(true);
  const [enableA11y, setEnableA11y] = useState(true);
  const [enableExploration, setEnableExploration] = useState(true);
  const [enableVisualDiff, setEnableVisualDiff] = useState(false);

  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Validate URL with debounce
  useEffect(() => {
    if (!url || !url.startsWith('http')) {
      setValidationResult(null);
      return;
    }

    const timer = setTimeout(async () => {
      setValidating(true);
      try {
        const res = await validateUrl(url);
        setValidationResult(res);
      } catch (err) {
        setValidationResult({ valid: false, error: 'Validation endpoint unreachable' });
      } finally {
        setValidating(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [url]);

  const handleLaunch = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const payload = {
        url,
        max_depth: Number(maxDepth),
        max_actions: Number(maxActions),
        browser,
        headless,
        enable_a11y: enableA11y,
        enable_exploration: enableExploration,
        enable_visual_diff: enableVisualDiff,
      };

      const result = await startScan(payload);
      if (onScanStarted) {
        onScanStarted(result.scan_id, url);
      }
    } catch (err) {
      setError(err.message || 'Failed to start scan');
    } finally {
      setIsSubmitting(false);
    }
  };

  const applyPreset = (presetUrl, depth, actions, a11y) => {
    setUrl(presetUrl);
    setMaxDepth(depth);
    setMaxActions(actions);
    setEnableA11y(a11y);
  };

  return (
    <div style={{ maxWidth: '960px', margin: '40px auto', padding: '0 24px' }}>
      {/* Hero Banner */}
      <div style={{ textAlign: 'center', marginBottom: '36px' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 16px',
          borderRadius: '999px',
          background: 'rgba(6, 182, 212, 0.1)',
          border: '1px solid rgba(6, 182, 212, 0.25)',
          color: '#22d3ee',
          fontSize: '0.85rem',
          fontWeight: 600,
          marginBottom: '16px',
        }}>
          <Sparkles size={16} /> Autonomous AI Exploration & Defect Hunting
        </div>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '12px' }}>
          Dispatch a Bug Hunter Scan
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', maxWidth: '640px', margin: '0 auto' }}>
          Provide any web application URL. BugHunter will autonomously navigate, click, fill forms, execute security and accessibility checks, and capture bugs with visual evidence.
        </p>
      </div>

      {/* Preset Buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px', marginBottom: '28px' }}>
        <div
          onClick={() => applyPreset('http://localhost:8080', 2, 25, true)}
          className="glass-panel"
          style={{
            padding: '16px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            border: url === 'http://localhost:8080' ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
            background: url === 'http://localhost:8080' ? 'rgba(6, 182, 212, 0.1)' : 'var(--bg-card)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <span style={{ fontSize: '1.2rem' }}>🎯</span>
            <strong style={{ fontSize: '0.95rem' }}>Local Demo Target</strong>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            http://localhost:8080 (10+ real bugs built-in)
          </p>
        </div>

        <div
          onClick={() => applyPreset('https://example.com', 1, 10, true)}
          className="glass-panel"
          style={{
            padding: '16px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            border: url === 'https://example.com' ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <span style={{ fontSize: '1.2rem' }}>⚡</span>
            <strong style={{ fontSize: '0.95rem' }}>Lightweight Smoke Test</strong>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            Depth 1 · 10 fast actions · Quick sanity check
          </p>
        </div>

        <div
          onClick={() => applyPreset('https://news.ycombinator.com', 2, 40, true)}
          className="glass-panel"
          style={{
            padding: '16px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            border: url === 'https://news.ycombinator.com' ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <span style={{ fontSize: '1.2rem' }}>🌐</span>
            <strong style={{ fontSize: '0.95rem' }}>Public Site Audit</strong>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            Deep crawl · A11y WCAG 2.1 AA audit
          </p>
        </div>
      </div>

      {/* Main Form */}
      <form onSubmit={handleLaunch} className="glass-panel-glow" style={{ padding: '32px' }}>
        {/* Target URL Field */}
        <div style={{ marginBottom: '28px' }}>
          <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 700, marginBottom: '8px', color: 'var(--text-primary)' }}>
            Target Application URL
          </label>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Globe size={18} color="#94a3b8" style={{ position: 'absolute', left: '16px' }} />
            <input
              id="target-url-input"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://your-application.com"
              required
              className="input-control"
              style={{ paddingLeft: '44px', fontSize: '1.05rem', fontFamily: 'var(--font-mono)' }}
            />
          </div>

          {/* Validation Feedback */}
          {url && (
            <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem' }}>
              {validating ? (
                <span style={{ color: 'var(--text-muted)' }}>Validating security constraints...</span>
              ) : validationResult?.valid ? (
                <span style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 600 }}>
                  <CheckCircle2 size={15} /> URL valid & ready to scan
                </span>
              ) : validationResult && !validationResult.valid ? (
                <span style={{ color: '#fb7185', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 600 }}>
                  <AlertTriangle size={15} /> {validationResult.error}
                </span>
              ) : null}
            </div>
          )}
        </div>

        {/* Configuration Sliders & Toggles */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', marginBottom: '28px', padding: '20px', background: 'rgba(15, 23, 42, 0.4)', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
          {/* Depth Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Crawl Depth Limit</span>
              <strong style={{ color: 'var(--accent-cyan)' }}>Level {maxDepth}</strong>
            </div>
            <input
              type="range"
              min="1"
              max="4"
              value={maxDepth}
              onChange={(e) => setMaxDepth(e.target.value)}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
            />
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Number of link tiers to spider from root URL
            </p>
          </div>

          {/* Actions Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Max Agent Actions</span>
              <strong style={{ color: 'var(--accent-purple)' }}>{maxActions} Actions</strong>
            </div>
            <input
              type="range"
              min="5"
              max="60"
              step="5"
              value={maxActions}
              onChange={(e) => setMaxActions(e.target.value)}
              style={{ width: '100%', accentColor: 'var(--accent-purple)' }}
            />
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Maximum clicks, form fills, and steps taken
            </p>
          </div>

          {/* Browser engine */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Browser Engine
            </label>
            <select
              value={browser}
              onChange={(e) => setBrowser(e.target.value)}
              className="input-control"
              style={{ padding: '8px 12px' }}
            >
              <option value="chromium">Chromium (Recommended)</option>
              <option value="firefox">Firefox</option>
              <option value="webkit">WebKit (Safari engine)</option>
            </select>
          </div>

          {/* Feature toggles */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', justifyContent: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={enableA11y}
                onChange={(e) => setEnableA11y(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--accent-cyan)' }}
              />
              <span>Audit Accessibility (axe-core WCAG 2.1 AA)</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={enableExploration}
                onChange={(e) => setEnableExploration(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--accent-cyan)' }}
              />
              <span>Enable AI Autonomous Explorer loop</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={headless}
                onChange={(e) => setHeadless(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--accent-cyan)' }}
              />
              <span>Headless execution (faster background runs)</span>
            </label>
          </div>
        </div>

        {error && (
          <div style={{
            padding: '12px 16px',
            borderRadius: '8px',
            background: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            color: '#fda4af',
            fontSize: '0.85rem',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <AlertTriangle size={16} />
            {error}
          </div>
        )}

        {/* Action Button */}
        <button
          id="launch-scan-btn"
          type="submit"
          disabled={isSubmitting || (validationResult && !validationResult.valid)}
          className="btn btn-primary"
          style={{
            width: '100%',
            padding: '16px',
            fontSize: '1.1rem',
            borderRadius: '12px',
            fontWeight: 700,
          }}
        >
          <Rocket size={20} />
          {isSubmitting ? 'Initializing Agent...' : 'Launch Autonomous Bug Hunt'}
        </button>
      </form>
    </div>
  );
}
