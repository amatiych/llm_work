import { useState, useEffect } from 'react'

const PROMPT_EXAMPLES = [
  'Create a comprehensive risk-focused report highlighting drawdowns and volatility',
  'Build a concise executive summary with performance highlights and outlook',
  'Generate an income analysis report focusing on yield trends and duration',
  'Create a detailed portfolio analysis with sector exposure and top holdings',
]

const TOOL_COLORS = {
  analyze_fund: '#2E5090',
  list_available_charts: '#7B68EE',
  generate_chart: '#4CAF50',
  add_section: '#E8833A',
  list_themes: '#9C27B0',
  set_theme: '#9C27B0',
  finalize_report: '#F44336',
}

export default function App() {
  const [funds, setFunds] = useState([])
  const [themes, setThemes] = useState([])
  const [fundId, setFundId] = useState('')
  const [prompt, setPrompt] = useState('')
  const [themeId, setThemeId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  // Template state
  const [templates, setTemplates] = useState([])
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [templateName, setTemplateName] = useState('')
  const [showSaveTemplate, setShowSaveTemplate] = useState(false)
  const [templateMsg, setTemplateMsg] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/funds').then(r => r.json()),
      fetch('/api/themes').then(r => r.json()),
      fetch('/api/templates').then(r => r.json()),
    ]).then(([f, t, tpl]) => {
      setFunds(f)
      setThemes(t)
      setTemplates(tpl)
      if (f.length > 0) setFundId(f[0].id)
    })
  }, [])

  function refreshTemplates() {
    fetch('/api/templates').then(r => r.json()).then(setTemplates)
  }

  async function handleGenerate() {
    if (!fundId) return
    // If using a template, replay it; otherwise require a prompt
    if (selectedTemplate) {
      return handleReplayTemplate()
    }
    if (!prompt.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fund_id: fundId,
          prompt: prompt.trim(),
          theme_id: themeId || null,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Generation failed')
      }
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleReplayTemplate() {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch(`/api/templates/${selectedTemplate}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fund_id: fundId,
          theme_id: themeId || null,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Template replay failed')
      }
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveTemplate() {
    const name = templateName.trim()
    if (!name || !result?.plan) return

    try {
      const res = await fetch('/api/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, plan: result.plan }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Save failed')
      }
      setTemplateMsg(`Saved as "${name}"`)
      setTemplateName('')
      setShowSaveTemplate(false)
      refreshTemplates()
      setTimeout(() => setTemplateMsg(null), 3000)
    } catch (e) {
      setTemplateMsg(`Error: ${e.message}`)
      setTimeout(() => setTemplateMsg(null), 4000)
    }
  }

  async function handleDeleteTemplate(name) {
    try {
      const res = await fetch(`/api/templates/${name}`, { method: 'DELETE' })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Delete failed')
      }
      if (selectedTemplate === name) setSelectedTemplate('')
      refreshTemplates()
    } catch (e) {
      setError(e.message)
    }
  }

  const canGenerate = selectedTemplate
    ? !loading
    : !loading && prompt.trim()

  return (
    <div className="app">
      <header className="header">
        <h1>Report Builder</h1>
        <span className="subtitle">AI-Powered Investment Reports</span>
      </header>

      <main className="main">
        {/* Config Panel */}
        <section className="config-panel">
          <div className="field">
            <label htmlFor="fund">Fund</label>
            <select
              id="fund"
              value={fundId}
              onChange={e => setFundId(e.target.value)}
              disabled={loading}
            >
              {funds.map(f => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>

          {/* Template selector */}
          <div className="field">
            <label htmlFor="template">Or use a saved template</label>
            <div className="template-selector">
              <select
                id="template"
                value={selectedTemplate}
                onChange={e => setSelectedTemplate(e.target.value)}
                disabled={loading}
              >
                <option value="">None (use prompt)</option>
                {templates.map(t => (
                  <option key={t.name} value={t.name}>
                    {t.title} ({t.sections} sections)
                  </option>
                ))}
              </select>
              {selectedTemplate && (
                <button
                  className="btn-delete-template"
                  onClick={() => handleDeleteTemplate(selectedTemplate)}
                  disabled={loading}
                  title="Delete this template"
                >
                  Delete
                </button>
              )}
            </div>
          </div>

          {/* Prompt — hidden when template is selected */}
          {!selectedTemplate && (
            <div className="field">
              <label htmlFor="prompt">Prompt</label>
              <textarea
                id="prompt"
                rows={4}
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                disabled={loading}
                placeholder="e.g. Create a risk-focused report highlighting drawdowns and volatility..."
              />
              <div className="examples">
                {PROMPT_EXAMPLES.map((ex, i) => (
                  <button
                    key={i}
                    className="example-chip"
                    onClick={() => setPrompt(ex)}
                    disabled={loading}
                  >
                    {ex.length > 60 ? ex.slice(0, 57) + '...' : ex}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="field">
            <label htmlFor="theme">Theme (optional)</label>
            <select
              id="theme"
              value={themeId}
              onChange={e => setThemeId(e.target.value)}
              disabled={loading}
            >
              <option value="">Default</option>
              {themes.filter(t => t.theme_id !== 'default').map(t => (
                <option key={t.theme_id} value={t.theme_id}>
                  {t.client_name || t.theme_id}
                </option>
              ))}
            </select>
          </div>

          <button
            className="btn-generate"
            onClick={handleGenerate}
            disabled={!canGenerate}
          >
            {loading
              ? 'Generating...'
              : selectedTemplate
                ? 'Replay Template'
                : 'Generate Report'}
          </button>
        </section>

        {/* Loading State */}
        {loading && (
          <section className="loading-panel">
            <div className="spinner" />
            <p>{selectedTemplate ? 'Replaying template...' : 'Claude is building your report...'}</p>
            <p className="loading-hint">
              {selectedTemplate ? 'This should be instant' : 'This typically takes ~30-60 seconds'}
            </p>
          </section>
        )}

        {/* Error */}
        {error && (
          <section className="error-panel">
            <strong>Error:</strong> {error}
          </section>
        )}

        {/* Results */}
        {result && (
          <section className="results-panel">
            {/* Summary Bar */}
            <div className="summary-bar">
              <div className="stat">
                <span className="stat-value">{result.sections}</span>
                <span className="stat-label">Sections</span>
              </div>
              <div className="stat">
                <span className="stat-value">{result.chart_files?.length || 0}</span>
                <span className="stat-label">Charts</span>
              </div>
              <div className="stat">
                <span className="stat-value">{result.tool_calls}</span>
                <span className="stat-label">Tool Calls</span>
              </div>

              {/* Save as Template */}
              {result.plan && !showSaveTemplate && (
                <button
                  className="btn-save-template"
                  onClick={() => setShowSaveTemplate(true)}
                >
                  Save as Template
                </button>
              )}
              {showSaveTemplate && (
                <div className="save-template-inline">
                  <input
                    type="text"
                    placeholder="template_name"
                    value={templateName}
                    onChange={e => setTemplateName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSaveTemplate()}
                  />
                  <button className="btn-confirm-save" onClick={handleSaveTemplate}>
                    Save
                  </button>
                  <button className="btn-cancel-save" onClick={() => {
                    setShowSaveTemplate(false)
                    setTemplateName('')
                  }}>
                    Cancel
                  </button>
                </div>
              )}
              {templateMsg && <span className="template-msg">{templateMsg}</span>}

              <a
                className="btn-download"
                href={`/api/report/${result.fund_id}/pdf`}
                download
              >
                Download PDF
              </a>
            </div>

            {/* Chart Grid */}
            {result.chart_files?.length > 0 && (
              <div className="section-block">
                <h2>Generated Charts</h2>
                <div className="chart-grid">
                  {result.chart_files.map(chartId => (
                    <div key={chartId} className="chart-card">
                      <img
                        src={`/api/report/${result.fund_id}/charts/${chartId}`}
                        alt={chartId}
                        loading="lazy"
                      />
                      <span className="chart-label">{chartId.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tool Log Timeline */}
            {result.tool_log?.length > 0 && (
              <div className="section-block">
                <h2>Tool Log</h2>
                <ol className="tool-log">
                  {result.tool_log.map((entry, i) => (
                    <li key={i} className="log-entry">
                      <span
                        className="tool-badge"
                        style={{ backgroundColor: TOOL_COLORS[entry.tool] || '#666' }}
                      >
                        {entry.tool}
                      </span>
                      <span className="log-summary">
                        {summarizeTool(entry)}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

function summarizeTool(entry) {
  const { tool, input } = entry
  if (tool === 'analyze_fund') return 'Analyzed fund data profile'
  if (tool === 'list_available_charts') return 'Listed available chart types'
  if (tool === 'generate_chart') return `Generated chart: ${input.chart_id}`
  if (tool === 'add_section') return `Added section: ${input.title}`
  if (tool === 'list_themes') return 'Listed available themes'
  if (tool === 'set_theme') return `Applied theme: ${input.theme_id}`
  if (tool === 'finalize_report') return `Finalized: ${input.report_title}`
  return JSON.stringify(input).slice(0, 80)
}
