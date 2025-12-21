import { useState, useEffect } from 'react'
import { fetchGames, updateGame, getRecommendation, uploadLibrary } from './api'
import './App.css'

function GameCard({ game, onMove, onAttentionChange, actions }) {
  const attentionLevels = [
    { value: 'casual', label: '☕ Casual', className: 'btn-casual' },
    { value: 'focused', label: '🎯 Focused', className: 'btn-focused' },
    { value: 'unset', label: 'None', className: 'btn-unset' }
  ]

  return (
    <div className={`game-card attention-${game.attention_level}`}>
      <div className="game-card-content">
        <h3 className="game-name">{game.name}</h3>
        <div className="game-meta">
          <span className="badge">{game.genre}</span>
          <span className="badge secondary">{game.tags.split(';')[0]}</span>
        </div>
        
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

function ConciergeView({ loading, error, getRec, recommendation }) {
  const [genre, setGenre] = useState('')
  const [tag, setTag] = useState('')
  const [length, setLength] = useState('')
  const [unplayed, setUnplayed] = useState(false)
  const [attention, setAttention] = useState('')

  const handleRecommend = () => {
    getRec({ genre, tag, length, unplayed_only: unplayed, attention_level: attention })
  }

  return (
    <div className="view concierge-view">
      <section className="card filter-section">
        <h2>Preferences</h2>
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
          {loading ? 'Consulting...' : 'Recommend a Game'}
        </button>
      </section>

      {error && <div className="error-card">{error}</div>}

      {recommendation && (
        <section className="result-card">
          <h3>I recommend:</h3>
          <div className="game-title">{recommendation.Name}</div>
          <div className="game-details">
            <span className="badge">{recommendation.Genre}</span>
            <span className="badge secondary">{recommendation.Tags.split(';')[0]}</span>
          </div>
          <p><strong>Playtime:</strong> {recommendation.Playtime_Forever} mins</p>
          <p><strong>Category:</strong> {recommendation.attention_level === 'casual' ? '☕ Casual' : recommendation.attention_level === 'focused' ? '🎯 Focused' : 'Uncategorized'}</p>
        </section>
      )}
    </div>
  )
}

function DashboardView({ games, onMove, onAttentionChange }) {
  const playing = games.filter(g => g.status === 'playing')
  const upNext = games.filter(g => g.status === 'up_next')

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
            {playing.length === 0 && <p className="empty-msg">Nothing active. Pick something from Up Next!</p>}
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
            {upNext.length === 0 && <p className="empty-msg">Queue is empty. Find a game in the Library!</p>}
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

  useEffect(() => {
    loadLibrary()
  }, [attentionFilter])

  const loadLibrary = async () => {
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
  }

  const handleSearch = async (e) => {
    const val = e.target.value
    setSearch(val)
    try {
      const params = { status: 'library' }
      if (attentionFilter) params.attention_level = attentionFilter
      if (val) params.search = val
      const data = await fetchGames(params)
      setGames(data)
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="view library-view">
      <section className="card library-header">
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
        </div>
      </section>
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
        {loading && <p>Loading games...</p>}
        {games.length === 0 && !loading && <p>No games found matching criteria.</p>}
      </div>
    </div>
  )
}

function UploadView() {
  const [uploadMsg, setUploadMsg] = useState('')
  const [loading, setLoading] = useState(false)

  const handleUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    setLoading(true)
    try {
      const res = await uploadLibrary(file)
      setUploadMsg(`Success! Loaded ${res.games_count} games.`)
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
        <h2>Upload Steam Library</h2>
        <p>Export your Steam library as CSV and upload it here.</p>
        <input type="file" accept=".csv" onChange={handleUpload} disabled={loading} />
        {uploadMsg && <p className="success-msg">{uploadMsg}</p>}
        {loading && <p>Processing...</p>}
      </section>
    </div>
  )
}

function App() {
  const [currentView, setCurrentView] = useState('concierge')
  const [dashboardGames, setDashboardGames] = useState([])
  const [recommendation, setRecommendation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (currentView === 'dashboard') {
      loadDashboard()
    }
  }, [currentView])

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
        <div className="logo">🎩 GameButler</div>
        <div className="nav-links">
          <button className={currentView === 'concierge' ? 'active' : ''} onClick={() => setCurrentView('concierge')}>Concierge</button>
          <button className={currentView === 'dashboard' ? 'active' : ''} onClick={() => setCurrentView('dashboard')}>Dashboard</button>
          <button className={currentView === 'library' ? 'active' : ''} onClick={() => setCurrentView('library')}>Library</button>
          <button className={currentView === 'upload' ? 'active' : ''} onClick={() => setCurrentView('upload')}>Upload</button>
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
        {currentView === 'upload' && (
          <UploadView />
        )}
      </main>
    </div>
  )
}

export default App