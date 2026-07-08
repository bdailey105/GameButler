import { useState, useEffect, useCallback } from 'react'
import { fetchGames, updateGame, reorderQueue, getRecommendation, uploadLibrary, previewLibraryUpload, autoTagLibrary, enrichLibrary, fetchEnrichmentJob, fetchCurrentEnrichmentJob, syncSteamLibrary } from './api'
import './App.css'

function GameCard({ game, onMove, onAttentionChange, actions, queueActions = [] }) {
  const primaryTag = game.tags?.split(';')[0]
  const status = game.status || 'library'
  const attentionLevels = [
    { value: 'casual', label: '☕ Casual', className: 'btn-casual' },
    { value: 'focused', label: '🎯 Focused', className: 'btn-focused' },
    { value: 'unset', label: 'None', className: 'btn-unset' }
  ]

  return (
    <div className={`game-card status-${status} attention-${game.attention_level}`}>
      {game.header_image ? (
        <img className="game-card-image" src={game.header_image} alt="" loading="lazy" />
      ) : (
        <div className="game-card-image game-card-image-placeholder">{game.name?.slice(0, 1) || '?'}</div>
      )}
      <div className="game-card-content">
        <h3 className="game-name">{game.name}</h3>
        <div className="game-meta">
          {game.genre && <span className="badge">{game.genre}</span>}
          {primaryTag && <span className="badge secondary">{primaryTag}</span>}
        </div>
        {game.short_description && <p className="game-description">{game.short_description}</p>}
        
        <div className="attention-toggle">
          <label>Attention:</label>
          <div className="attention-btns">
            {attentionLevels.map(level => (
              <button
                key={level.value}
                className={`att-btn ${level.className} ${game.attention_level === level.value ? 'active' : ''}`}
                onClick={() => onAttentionChange(game.id, level.value)}
                title={level.label}
              >
                {level.label.split(' ')[0]} {/* Show icon or text */}
              </button>
            ))}
          </div>
        </div>

        <div className="game-stats">
          <p><strong>Playtime:</strong> {game.playtime_forever} mins</p>
        </div>
      </div>
      <div className="game-card-actions">
        {queueActions.map(action => (
          <button
            key={action.label}
            className={`action-btn ${action.className || ''}`}
            onClick={action.onClick}
            disabled={action.disabled}
            title={action.title || action.label}
          >
            {action.label}
          </button>
        ))}
        {actions.map(action => (
          <button 
            key={action.status} 
            className={`action-btn ${action.className || ''}`}
            onClick={() => onMove(game.id, action.status)}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  )
}

function EmptyState({ title, message, action }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">◇</div>
      <h3>{title}</h3>
      <p>{message}</p>
      {action}
    </div>
  )
}

function LoadingState({ label = 'Loading library...' }) {
  return (
    <div className="skeleton-stack" aria-live="polite" aria-label={label}>
      <p className="loading-label">{label}</p>
      <div className="skeleton-card" />
      <div className="skeleton-card" />
      <div className="skeleton-card" />
    </div>
  )
}

function ConciergeView({ loading, error, getRec, recommendation }) {
  const [genre, setGenre] = useState('')
  const [tag, setTag] = useState('')
  const [length, setLength] = useState('')
  const [unplayed, setUnplayed] = useState(false)
  const [attention, setAttention] = useState('')
  const [mood, setMood] = useState('')
  const moods = [
    { value: 'zone_out', label: 'Zone out', hint: 'Low friction' },
    { value: 'story_night', label: 'Story night', hint: 'Focused' },
    { value: 'short_session', label: 'Short session', hint: 'Quick run' },
    { value: 'finish_something', label: 'Finish something', hint: 'Progress' },
    { value: 'surprise_me', label: 'Surprise me', hint: 'Wildcard' }
  ]

  const handleRecommend = () => {
    getRec({
      ...(genre && { genre }),
      ...(tag && { tag }),
      ...(length && { length }),
      unplayed_only: unplayed,
      ...(attention && { attention_level: attention }),
      ...(mood && { mood })
    })
  }

  return (
    <div className="view concierge-view">
      <section className="card filter-section">
        <p className="eyebrow">Butler</p>
        <h2>What kind of session are you after?</h2>
        <div className="mood-grid">
          {moods.map(option => (
            <button
              key={option.value}
              type="button"
              className={`mood-btn ${mood === option.value ? 'active' : ''}`}
              onClick={() => setMood(mood === option.value ? '' : option.value)}
            >
              <strong>{option.label}</strong>
              <span>{option.hint}</span>
            </button>
          ))}
        </div>
        <div className="filter-grid">
          <div className="filter-group">
            <label>Genre:</label>
            <input type="text" value={genre} onChange={(e) => setGenre(e.target.value)} placeholder="e.g. Action" />
          </div>
          <div className="filter-group">
            <label>Tag:</label>
            <input type="text" value={tag} onChange={(e) => setTag(e.target.value)} placeholder="e.g. Indie" />
          </div>
          <div className="filter-group">
            <label>Length:</label>
            <select value={length} onChange={(e) => setLength(e.target.value)}>
              <option value="">Any Length</option>
              <option value="short">Short (&lt; 5h)</option>
              <option value="medium">Medium (5h - 20h)</option>
              <option value="long">Long (&gt; 20h)</option>
            </select>
          </div>
          <div className="filter-group">
            <label>Attention:</label>
            <select value={attention} onChange={(e) => setAttention(e.target.value)}>
              <option value="">Any</option>
              <option value="casual">☕ Casual</option>
              <option value="focused">🎯 Focused</option>
            </select>
          </div>
        </div>
        <div className="filter-group checkbox">
          <label>
            <input type="checkbox" checked={unplayed} onChange={(e) => setUnplayed(e.target.checked)} />
            Unplayed Only
          </label>
        </div>
        <button className="primary-btn" onClick={handleRecommend} disabled={loading}>
          {loading ? 'Scanning library...' : 'Find My Game'}
        </button>
      </section>

      {error && <div className="error-card">{error}</div>}
      {loading && <LoadingState label="Butler is thinking..." />}

      {recommendation && (
        <section className="result-card">
          <p className="eyebrow">Recommendation</p>
          {recommendation.score !== undefined && <span className="score-pill">{recommendation.score}% match</span>}
          <div className="game-title">{recommendation.Name}</div>
          <div className="game-details">
            <span className="badge">{recommendation.Genre}</span>
            <span className="badge secondary">{recommendation.Tags.split(';')[0]}</span>
          </div>
          {recommendation.reasons?.length > 0 && (
            <div className="why-panel">
              <strong>Why this game</strong>
              <ul>
                {recommendation.reasons.map(reason => <li key={reason}>{reason}</li>)}
              </ul>
            </div>
          )}
          <p><strong>Playtime:</strong> {recommendation.Playtime_Forever} mins</p>
          <p><strong>Category:</strong> {recommendation.attention_level === 'casual' ? '☕ Casual' : recommendation.attention_level === 'focused' ? '🎯 Focused' : 'Uncategorized'}</p>
        </section>
      )}
    </div>
  )
}

function DashboardView({ games, onMove, onAttentionChange }) {
  const playing = games.filter(g => g.status === 'playing')
  const upNext = games
    .filter(g => g.status === 'up_next')
    .sort((a, b) => (a.queue_position ?? 9999) - (b.queue_position ?? 9999) || a.name.localeCompare(b.name))

  return (
    <div className="view dashboard-view">
      <div className="dashboard-grid">
        <section className="dashboard-column">
          <h2>Currently Playing</h2>
          <div className="game-list">
            {playing.map(game => (
              <GameCard 
                key={game.id} 
                game={game} 
                onMove={onMove} 
                onAttentionChange={onAttentionChange}
                actions={[
                  { label: 'Completed', status: 'completed', className: 'success' },
                  { label: 'Drop', status: 'library', className: 'warning' }
                ]} 
              />
            ))}
            {playing.length === 0 && (
              <EmptyState title="Nothing playing right now" message="Pick something from your queue, or ask Butler for a fresh recommendation." />
            )}
          </div>
        </section>

        <section className="dashboard-column">
          <h2>Up Next</h2>
          <div className="game-list">
            {upNext.map(game => (
              <GameCard 
                key={game.id} 
                game={game} 
                onMove={onMove} 
                onAttentionChange={onAttentionChange}
                actions={[
                  { label: 'Start Playing', status: 'playing', className: 'primary' },
                  { label: 'Remove', status: 'library', className: 'secondary' }
                ]} 
              />
            ))}
            {upNext.length === 0 && (
              <EmptyState title="Queue is empty" message="Add games from the Library to build your next few sessions." />
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function LibraryView({ onMove, onAttentionChange }) {
  const [games, setGames] = useState([])
  const [search, setSearch] = useState('')
  const [attentionFilter, setAttentionFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [enriching, setEnriching] = useState(false)
  const [enrichmentJob, setEnrichmentJob] = useState(null)
  const [autoTagMsg, setAutoTagMsg] = useState('')

  const loadLibrary = useCallback(async () => {
    setLoading(true)
    try {
      const params = { status: 'library' }
      if (attentionFilter) params.attention_level = attentionFilter
      if (search) params.search = search
      const data = await fetchGames(params)
      setGames(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [attentionFilter, search])

  useEffect(() => {
    loadLibrary()
  }, [loadLibrary])

  useEffect(() => {
    fetchCurrentEnrichmentJob()
      .then(job => {
        setEnrichmentJob(job)
        setEnriching(job.status === 'running')
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!enrichmentJob || enrichmentJob.status !== 'running') return

    let cancelled = false
    const timer = setInterval(async () => {
      try {
        const job = await fetchEnrichmentJob(enrichmentJob.id)
        if (cancelled) return
        setEnrichmentJob(job)
        setEnriching(job.status === 'running')
        if (job.status !== 'running') {
          clearInterval(timer)
          loadLibrary()
        }
      } catch (err) {
        console.error(err)
        if (cancelled) return
        setEnriching(false)
        clearInterval(timer)
      }
    }, 1500)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [enrichmentJob, loadLibrary])

  const handleAutoTag = async () => {
    setLoading(true)
    try {
      const res = await autoTagLibrary()
      setAutoTagMsg(res.message)
      loadLibrary()
      setTimeout(() => setAutoTagMsg(''), 3000)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    setLoading(true)
    try {
      const res = await syncSteamLibrary()
      setAutoTagMsg(res.message)
      loadLibrary()
      setTimeout(() => setAutoTagMsg(''), 5000)
    } catch (err) {
      console.error(err)
      setAutoTagMsg(err.response?.data?.detail || 'Steam sync failed.')
      setTimeout(() => setAutoTagMsg(''), 8000)
    } finally {
      setLoading(false)
    }
  }

  const handleEnrich = async () => {
    setEnriching(true)
    try {
      const res = await enrichLibrary()
      setEnrichmentJob({ id: res.job_id, status: 'running' })
      setAutoTagMsg(res.message) // Reusing msg state for simplicity
      setTimeout(() => setAutoTagMsg(''), 5000)
    } catch (err) {
      console.error(err)
      setAutoTagMsg('Enrichment failed to start.')
      setEnriching(false)
    }
  }

  const handleSearch = async (e) => {
    setSearch(e.target.value)
  }

  return (
    <div className="view library-view">
      <section className="card library-header">
        <p className="eyebrow">Library</p>
        <h2>Library</h2>
        <div className="library-controls">
          <input 
            type="text" 
            placeholder="Search games..." 
            value={search} 
            onChange={handleSearch}
            className="search-input"
          />
          <select value={attentionFilter} onChange={(e) => setAttentionFilter(e.target.value)} className="att-filter">
            <option value="">All Attention</option>
            <option value="unset">Uncategorized</option>
            <option value="casual">☕ Casual</option>
            <option value="focused">🎯 Focused</option>
          </select>
          <button className="secondary-btn" onClick={handleSync} disabled={loading || enriching}>🔄 Sync Steam</button>
          <button className="secondary-btn" onClick={handleAutoTag} disabled={loading} title="Auto-tag uncategorized games">
            🪄 Auto-Tag
          </button>
          <button className="secondary-btn" onClick={handleEnrich} disabled={loading || enriching} title="Fetch metadata from Steam">
            {enriching ? 'Enriching...' : '☁️ Enrich'}
          </button>
        </div>
        {autoTagMsg && <p className="success-msg">{autoTagMsg}</p>}
        {enrichmentJob && (
          <div className={`job-progress job-${enrichmentJob.status}`}>
            <div className="progress-row">
              <strong>Enrichment {enrichmentJob.status}</strong>
              <span>{enrichmentJob.processed}/{enrichmentJob.total} processed</span>
            </div>
            <progress value={enrichmentJob.processed} max={Math.max(enrichmentJob.total, 1)} />
            <p>{enrichmentJob.succeeded} saved · {enrichmentJob.failed} failed</p>
            {enrichmentJob.error_summary && <p className="job-error">{enrichmentJob.error_summary}</p>}
          </div>
        )}
      </section>
      {loading ? (
        <LoadingState />
      ) : (
        <div className="library-grid">
          {games.map(game => (
            <GameCard 
              key={game.id} 
              game={game} 
              onMove={(id, status) => {
                onMove(id, status)
                setGames(games.filter(g => g.id !== id))
              }} 
              onAttentionChange={onAttentionChange}
              actions={[{ label: 'Add to Up Next', status: 'up_next', className: 'primary' }]} 
            />
          ))}
          {games.length === 0 && (
            <EmptyState title="No games found" message="Try a different search or attention filter." />
          )}
        </div>
      )}
    </div>
  )
}

function BacklogView({ onMove, onAttentionChange }) {
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(false)
  const statuses = [
    { key: 'library', title: 'Backlog' },
    { key: 'up_next', title: 'Up Next' },
    { key: 'playing', title: 'Playing' },
    { key: 'completed', title: 'Completed' }
  ]

  const loadBacklog = useCallback(async () => {
    setLoading(true)
    try {
      setGames(await fetchGames())
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadBacklog()
  }, [loadBacklog])

  const moveAndRefresh = async (id, status) => {
    await onMove(id, status)
    loadBacklog()
  }

  const moveQueuedGame = async (id, direction) => {
    const queue = games
      .filter(game => game.status === 'up_next')
      .sort((a, b) => (a.queue_position ?? 9999) - (b.queue_position ?? 9999) || a.name.localeCompare(b.name))
    const index = queue.findIndex(game => game.id === id)
    const targetIndex = index + direction
    if (index < 0 || targetIndex < 0 || targetIndex >= queue.length) return

    const nextQueue = [...queue]
    const [moved] = nextQueue.splice(index, 1)
    nextQueue.splice(targetIndex, 0, moved)
    const updatedQueue = await reorderQueue(nextQueue.map(game => game.id))
    const updatedById = new Map(updatedQueue.map(game => [game.id, game]))
    setGames(games.map(game => updatedById.get(game.id) || game))
  }

  return (
    <div className="view backlog-view">
      <section className="page-header">
        <p className="eyebrow">Backlog</p>
        <h2>Queue board</h2>
      </section>
      {loading ? (
        <LoadingState />
      ) : (
        <div className="backlog-board">
          {statuses.map(column => {
            const columnGames = games
              .filter(game => game.status === column.key)
              .sort((a, b) => (
                column.key === 'up_next'
                  ? (a.queue_position ?? 9999) - (b.queue_position ?? 9999) || a.name.localeCompare(b.name)
                  : a.name.localeCompare(b.name)
              ))
            return (
              <section className="backlog-column" key={column.key}>
                <div className="column-header">
                  <span>{column.title}</span>
                  <strong>{columnGames.length}</strong>
                </div>
                <div className="game-list">
                  {columnGames.slice(0, 12).map(game => (
                    <GameCard
                      key={game.id}
                      game={game}
                      onMove={moveAndRefresh}
                      onAttentionChange={onAttentionChange}
                      queueActions={column.key === 'up_next' ? [
                        {
                          label: '↑',
                          title: 'Move earlier',
                          disabled: columnGames.indexOf(game) === 0,
                          onClick: () => moveQueuedGame(game.id, -1)
                        },
                        {
                          label: '↓',
                          title: 'Move later',
                          disabled: columnGames.indexOf(game) === columnGames.length - 1,
                          onClick: () => moveQueuedGame(game.id, 1)
                        }
                      ] : []}
                      actions={[
                        column.key !== 'up_next' && { label: 'Queue', status: 'up_next', className: 'primary' },
                        column.key !== 'playing' && { label: 'Play', status: 'playing', className: 'success' },
                        column.key !== 'completed' && { label: 'Done', status: 'completed', className: 'secondary' }
                      ].filter(Boolean)}
                    />
                  ))}
                  {columnGames.length === 0 && (
                    <EmptyState title="Empty" message={`No games in ${column.title.toLowerCase()} yet.`} />
                  )}
                </div>
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}

function UploadView({ onUploaded }) {
  const [uploadMsg, setUploadMsg] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)

  const handlePreview = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    setSelectedFile(file)
    setPreview(null)
    setUploadMsg('')
    setLoading(true)
    try {
      const res = await previewLibraryUpload(file)
      setPreview(res)
    } catch (err) {
      setUploadMsg('Preview failed.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    setLoading(true)
    try {
      const res = await uploadLibrary(selectedFile)
      setUploadMsg(`Success! Added ${res.new_games}, updated ${res.updated_games}, skipped ${res.duplicate_rows} duplicate rows.`)
      setPreview(null)
      setSelectedFile(null)
      onUploaded()
    } catch (err) {
      setUploadMsg('Upload failed.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="view upload-view">
      <section className="card">
        <p className="eyebrow">Onboarding</p>
        <h2>Upload Steam Library</h2>
        <p>Export your Steam library as CSV and upload it here.</p>
        <input type="file" accept=".csv" onChange={handlePreview} disabled={loading} />
        {preview && (
          <div className="import-preview">
            <div>
              <span>Total rows</span>
              <strong>{preview.total_rows}</strong>
            </div>
            <div>
              <span>New</span>
              <strong>{preview.new_games}</strong>
            </div>
            <div>
              <span>Existing</span>
              <strong>{preview.updated_games}</strong>
            </div>
            <div>
              <span>Duplicates</span>
              <strong>{preview.duplicate_rows}</strong>
            </div>
            {preview.duplicate_app_ids.length > 0 && (
              <p>Duplicate AppIDs skipped after first row: {preview.duplicate_app_ids.join(', ')}</p>
            )}
            <button className="primary-btn" onClick={handleUpload} disabled={loading}>Import library</button>
          </div>
        )}
        {uploadMsg && <p className="success-msg">{uploadMsg}</p>}
        {loading && <p>Processing...</p>}
      </section>
    </div>
  )
}

function App() {
  const [currentView, setCurrentView] = useState('dashboard')
  const [dashboardGames, setDashboardGames] = useState([])
  const [libraryCount, setLibraryCount] = useState(null)
  const [recommendation, setRecommendation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadLibraryCount()
    if (currentView === 'dashboard') {
      loadDashboard()
    }
  }, [currentView])

  const loadLibraryCount = async () => {
    try {
      const games = await fetchGames()
      setLibraryCount(games.length)
    } catch (err) {
      console.error(err)
    }
  }

  const loadDashboard = async () => {
    setLoading(true)
    try {
      const playing = await fetchGames({ status: 'playing' })
      const upNext = await fetchGames({ status: 'up_next' })
      setDashboardGames([...playing, ...upNext])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleMove = async (appId, status) => {
    try {
      await updateGame(appId, { status })
      loadLibraryCount()
      if (currentView === 'dashboard') {
        loadDashboard()
      }
    } catch (err) {
      console.error('Failed to move game:', err)
    }
  }

  const handleAttentionChange = async (appId, attention_level) => {
    try {
      const updated = await updateGame(appId, { attention_level })
      // Update local state to reflect change
      if (currentView === 'dashboard') {
        setDashboardGames(dashboardGames.map(g => g.id === appId ? updated : g))
      }
      // If we are in concierge, and the recommendation matches, update it
      if (recommendation && recommendation.AppID === appId) {
        setRecommendation({ ...recommendation, attention_level })
      }
    } catch (err) {
      console.error('Failed to update attention:', err)
    }
  }

  const handleGetRec = async (params) => {
    setLoading(true)
    setError(null)
    setRecommendation(null)
    try {
      const data = await getRecommendation(params)
      setRecommendation(data)
    } catch (err) {
      if (err.response && err.response.status === 404) {
        setError('No game found matching your criteria.')
      } else {
        setError('Failed to get recommendation.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <nav className="navbar">
        <div className="logo">GameButler</div>
        <div className="nav-links">
          <button className={currentView === 'dashboard' ? 'active' : ''} onClick={() => setCurrentView('dashboard')}>Dashboard</button>
          <button className={currentView === 'library' ? 'active' : ''} onClick={() => setCurrentView('library')}>Library</button>
          <button className={currentView === 'backlog' ? 'active' : ''} onClick={() => setCurrentView('backlog')}>Backlog</button>
          <button className={currentView === 'concierge' ? 'active' : ''} onClick={() => setCurrentView('concierge')}>Butler</button>
          <button className={`add-nav ${currentView === 'upload' ? 'active' : ''}`} aria-label="Upload library" title="Upload library" onClick={() => setCurrentView('upload')}>Add</button>
        </div>
        <div className="library-chip">
          <span />
          {libraryCount === null ? 'Library' : `${libraryCount} in library`}
        </div>
      </nav>

      <main className="content">
        {currentView === 'concierge' && (
          <ConciergeView 
            loading={loading} 
            error={error} 
            getRec={handleGetRec} 
            recommendation={recommendation} 
          />
        )}
        {currentView === 'dashboard' && (
          <DashboardView 
            games={dashboardGames} 
            onMove={handleMove} 
            onAttentionChange={handleAttentionChange}
          />
        )}
        {currentView === 'library' && (
          <LibraryView 
            onMove={handleMove} 
            onAttentionChange={handleAttentionChange}
          />
        )}
        {currentView === 'backlog' && (
          <BacklogView
            onMove={handleMove}
            onAttentionChange={handleAttentionChange}
          />
        )}
        {currentView === 'upload' && (
          <UploadView onUploaded={loadLibraryCount} />
        )}
      </main>
    </div>
  )
}

export default App
