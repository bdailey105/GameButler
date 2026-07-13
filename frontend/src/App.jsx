import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchGames, updateGame, deleteGame, reorderQueue, getRecommendation, fetchContinuation, fetchResume, uploadLibrary, previewLibraryUpload, previewExternalImport, importExternalLibrary, autoTagLibrary, enrichLibrary, fetchEnrichmentJob, fetchCurrentEnrichmentJob, syncSteamLibrary, fetchActivity, fetchAutomationStatus, addGame, fetchGameDetail, addJournalEntry, deleteJournalEntry, postRecommendationDecision, bulkUpdateGames, fetchProfiles, createProfile, deleteProfile, fetchPendingOutcome, postSessionOutcome, fetchArchaeology, dismissArchaeology } from './api'
import './App.css'

const PLATFORM_LABELS = { switch: '🕹 Switch', playstation: '🎮 PlayStation', xbox: '🟢 Xbox', pc: '💻 PC', retro: '👾 Retro' }

function GameCard({ game, onMove, onAttentionChange, actions, queueActions = [], onDelete, onEditGenre, onOpenDetail, selectable, selectedState, onToggleSelect }) {
  const platformLabels = PLATFORM_LABELS
  const primaryTag = game.tags?.split(';')[0]
  const status = game.status || 'library'
  const attentionLevels = [
    { value: 'casual', label: '☕ Casual', className: 'btn-casual' },
    { value: 'focused', label: '🎯 Focused', className: 'btn-focused' },
    { value: 'unset', label: 'None', className: 'btn-unset' }
  ]

  return (
    <div className={`game-card status-${status} attention-${game.attention_level} ${selectedState ? 'selected' : ''}`}>
      {selectable && (
        <input
          type="checkbox"
          className="card-select"
          checked={!!selectedState}
          onChange={() => onToggleSelect(game.id)}
          aria-label={`Select ${game.name}`}
        />
      )}
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
          {game.platform && game.platform !== 'steam' && <span className="badge secondary">{platformLabels[game.platform] || game.platform}</span>}
          {game.platform && game.platform !== 'steam' && onEditGenre && (
            <button className="action-btn" title="Edit genre" onClick={() => onEditGenre(game)}>✎</button>
          )}
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
          {(game.platform === 'steam' || game.playtime_forever > 0) && (
            <p><strong>Playtime:</strong> {game.playtime_forever} mins</p>
          )}
          {game.average_playtime > 0 && (
            <p><strong>To beat:</strong> ~{Math.round(game.average_playtime / 60)}h</p>
          )}
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
        {onOpenDetail && (
          <button className="action-btn" title="Details" onClick={() => onOpenDetail(game.id)}>ⓘ</button>
        )}
        {onDelete && (
          <button className="action-btn danger" title="Remove from library" onClick={() => onDelete(game)}>✕</button>
        )}
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

function StarRating({ value, onChange }) {
  return (
    <div className="star-rating" role="group" aria-label="Personal rating">
      {[1, 2, 3, 4, 5].map(n => (
        <button
          key={n}
          type="button"
          className={`star-btn ${n <= (value || 0) ? 'filled' : ''}`}
          onClick={() => onChange(value === n ? null : n)}
          title={`${n} star${n > 1 ? 's' : ''}`}
          aria-label={`Set rating to ${n} star${n > 1 ? 's' : ''}`}
          aria-pressed={n <= (value || 0)}
        >
          ★
        </button>
      ))}
    </div>
  )
}

function GameDetailDrawer({ appId, onClose, onGameChanged }) {
  const [game, setGame] = useState(null)
  const [journal, setJournal] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)

  const [rating, setRating] = useState(null)
  const [startedOn, setStartedOn] = useState('')
  const [completedOn, setCompletedOn] = useState('')
  const [note, setNote] = useState('')
  const [sessionTags, setSessionTags] = useState([])
  const [returnWhen, setReturnWhen] = useState('')
  const [pauseJustClicked, setPauseJustClicked] = useState(false)
  const [saveState, setSaveState] = useState('idle') // idle | saving | saved | error
  const [saveError, setSaveError] = useState('')
  const sessionTagOptions = [
    { value: 'burst_friendly', label: 'Burst-friendly' },
    { value: 'controller_only', label: 'Controller only' },
    { value: 'podcast_friendly', label: 'Podcast-friendly' }
  ]

  const [newEntry, setNewEntry] = useState('')
  const [addingEntry, setAddingEntry] = useState(false)

  const drawerRef = useRef(null)
  const previouslyFocused = useRef(null)

  useEffect(() => {
    if (!appId) return
    previouslyFocused.current = document.activeElement
    setLoading(true)
    setLoadError(null)
    fetchGameDetail(appId)
      .then(data => {
        setGame(data)
        setJournal(data.journal || [])
        setRating(data.personal_rating ?? null)
        setStartedOn(data.started_on || '')
        setCompletedOn(data.completed_on || '')
        setNote(data.current_note || '')
        setSessionTags(data.session_tags ? data.session_tags.split(';').filter(Boolean) : [])
        setReturnWhen(data.return_when || '')
        setPauseJustClicked(false)
        setSaveState('idle')
      })
      .catch(err => {
        console.error(err)
        setLoadError('Failed to load game details.')
      })
      .finally(() => setLoading(false))
  }, [appId])

  useEffect(() => {
    if (appId && !loading && drawerRef.current) {
      drawerRef.current.focus()
    }
  }, [appId, loading])

  const handleClose = useCallback(() => {
    onClose()
    if (previouslyFocused.current && typeof previouslyFocused.current.focus === 'function') {
      previouslyFocused.current.focus()
    }
  }, [onClose])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        handleClose()
        return
      }
      if (e.key === 'Tab' && drawerRef.current) {
        const focusable = drawerRef.current.querySelectorAll(
          'button:not(:disabled), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleClose])

  const handleMove = async (status) => {
    if (status === 'paused') setPauseJustClicked(true)
    try {
      const updated = await updateGame(appId, { status })
      setGame(updated)
      onGameChanged?.()
    } catch (err) {
      console.error('Failed to update game status:', err)
    }
  }

  const toggleSessionTag = (value) => {
    setSessionTags(prev => prev.includes(value) ? prev.filter(t => t !== value) : [...prev, value])
  }

  const handleSaveContext = async () => {
    setSaveState('saving')
    setSaveError('')
    try {
      const updated = await updateGame(appId, {
        personal_rating: rating,
        started_on: startedOn || null,
        completed_on: completedOn || null,
        current_note: note || null,
        session_tags: sessionTags.length > 0 ? sessionTags.join(';') : null,
        return_when: returnWhen || null,
      })
      setGame(updated)
      setSaveState('saved')
      onGameChanged?.()
      setTimeout(() => setSaveState('idle'), 2500)
    } catch (err) {
      console.error(err)
      setSaveState('error')
      setSaveError(err.response?.data?.detail || 'Failed to save changes.')
    }
  }

  const handleAddEntry = async () => {
    if (!newEntry.trim() || addingEntry) return
    setAddingEntry(true)
    try {
      const entry = await addJournalEntry(appId, newEntry.trim())
      setJournal(prev => [...prev, entry])
      setNewEntry('')
    } catch (err) {
      console.error('Failed to add journal entry:', err)
    } finally {
      setAddingEntry(false)
    }
  }

  const handleDeleteEntry = async (entryId) => {
    if (!window.confirm('Delete this journal entry?')) return
    try {
      await deleteJournalEntry(appId, entryId)
      setJournal(prev => prev.filter(entry => entry.id !== entryId))
    } catch (err) {
      console.error('Failed to delete journal entry:', err)
    }
  }

  const status = game?.status || 'library'
  const statusActions = [
    { label: status === 'paused' ? '▶ Resume' : '▶ Play now', status: 'playing', className: 'primary' },
    { label: '+ Up Next', status: 'up_next', className: 'secondary' },
    { label: '↩ Back to Library', status: 'library', className: 'secondary' },
    { label: '⏸ Pause', status: 'paused', className: 'secondary' }
  ].filter(action => action.status !== status)
  const showReturnWhen = status === 'paused' || pauseJustClicked

  return (
    <>
      <div className="drawer-overlay" onClick={handleClose} />
      <div
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={game?.name ? `${game.name} details` : 'Game details'}
        tabIndex={-1}
        ref={drawerRef}
      >
        <button className="action-btn drawer-close" title="Close" onClick={handleClose}>✕</button>

        {loading && <LoadingState label="Loading game..." />}
        {!loading && loadError && <div className="error-card">{loadError}</div>}

        {!loading && !loadError && game && (
          <>
            <div className="drawer-header">
              {game.header_image ? (
                <img className="drawer-art" src={game.header_image} alt="" />
              ) : (
                <div className="drawer-art drawer-art-placeholder">{game.name?.slice(0, 1) || '?'}</div>
              )}
              <h2 className="drawer-title">{game.name}</h2>
              <div className="game-meta">
                {game.genre && <span className="badge">{game.genre}</span>}
                {game.platform && <span className="badge secondary">{PLATFORM_LABELS[game.platform] || game.platform}</span>}
              </div>
              {game.source && (
                <p className="drawer-source-meta">Source: {game.source}{game.external_id ? ` · ${game.external_id}` : ''}</p>
              )}
              {game.short_description && <p className="drawer-description">{game.short_description}</p>}
            </div>

            {statusActions.length > 0 && (
              <div className="drawer-status-actions">
                {statusActions.map(action => (
                  <button
                    key={action.status}
                    className={`action-btn ${action.className}`}
                    onClick={() => handleMove(action.status)}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}

            {showReturnWhen && (
              <div className="drawer-field">
                <label>Return when…</label>
                <input
                  type="text"
                  value={returnWhen}
                  onChange={(e) => setReturnWhen(e.target.value)}
                  placeholder="e.g. after finishing the current chapter"
                />
              </div>
            )}

            <section className="drawer-section">
              <h3>Personal Context</h3>
              <div className="drawer-field">
                <label>Rating</label>
                <StarRating value={rating} onChange={setRating} />
              </div>
              <div className="drawer-date-row">
                <div className="drawer-field">
                  <label>Started</label>
                  <input type="date" value={startedOn} onChange={(e) => setStartedOn(e.target.value)} />
                </div>
                <div className="drawer-field">
                  <label>Completed</label>
                  <input type="date" value={completedOn} onChange={(e) => setCompletedOn(e.target.value)} />
                </div>
              </div>
              <div className="drawer-field">
                <label>Notes</label>
                <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="What do you think so far?" />
              </div>
              <div className="drawer-field">
                <label>Session suitability</label>
                <div className="planner-chip-row">
                  {sessionTagOptions.map(option => (
                    <button
                      key={option.value}
                      type="button"
                      className={`planner-chip ${sessionTags.includes(option.value) ? 'active' : ''}`}
                      onClick={() => toggleSessionTag(option.value)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="drawer-save-row">
                <button className="primary-btn" onClick={handleSaveContext} disabled={saveState === 'saving'}>
                  {saveState === 'saving' ? 'Saving...' : 'Save'}
                </button>
                {saveState === 'saved' && <span className="success-msg">Saved</span>}
                {saveState === 'error' && <span className="drawer-error-text">{saveError}</span>}
              </div>
            </section>

            <section className="drawer-section">
              <h3>Journal</h3>
              <div className="journal-list">
                {journal.length === 0 && <p className="empty-hint">No journal entries yet.</p>}
                {journal.map(entry => (
                  <div className="journal-entry" key={entry.id}>
                    <div className="journal-entry-header">
                      <span className="journal-date">{new Date(entry.created_at).toLocaleDateString()}</span>
                      <button className="action-btn danger journal-delete" title="Delete entry" onClick={() => handleDeleteEntry(entry.id)}>✕</button>
                    </div>
                    <p className="journal-text">{entry.text}</p>
                  </div>
                ))}
              </div>
              <div className="journal-add">
                <textarea
                  rows={2}
                  value={newEntry}
                  onChange={(e) => setNewEntry(e.target.value)}
                  placeholder="Add a journal entry..."
                />
                <button className="secondary-btn" onClick={handleAddEntry} disabled={!newEntry.trim() || addingEntry}>
                  {addingEntry ? 'Adding...' : 'Add entry'}
                </button>
              </div>
            </section>
          </>
        )}
      </div>
    </>
  )
}

function ConciergeView({ loading, error, getRec, recommendation }) {
  const [butlerMode, setButlerMode] = useState('fresh')
  const [genre, setGenre] = useState('')
  const [tag, setTag] = useState('')
  const [length, setLength] = useState('')
  const [unplayed, setUnplayed] = useState(false)
  const [attention, setAttention] = useState('')
  const [mood, setMood] = useState('')
  const [sessionMinutes, setSessionMinutes] = useState(null)
  const [sessionEnergy, setSessionEnergy] = useState(null)
  const [sessionContext, setSessionContext] = useState(null)
  const [appliedSession, setAppliedSession] = useState(null)
  const [actedOn, setActedOn] = useState({})
  const [feedback, setFeedback] = useState({})
  const [reasonPickerFor, setReasonPickerFor] = useState(null)
  const [lastRecommendation, setLastRecommendation] = useState(recommendation)
  const [profiles, setProfiles] = useState([])
  const [activeProfileId, setActiveProfileId] = useState(null)
  const [profileError, setProfileError] = useState('')
  const [pendingOutcome, setPendingOutcome] = useState(null)
  const [outcomeConfirmed, setOutcomeConfirmed] = useState(false)
  const timeOptions = [
    { value: 15, label: '15 min' },
    { value: 30, label: '30 min' },
    { value: 60, label: '1 hour' },
    { value: 120, label: '90+ min' }
  ]
  const energyOptions = [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' }
  ]
  const contextOptions = [
    { value: 'desk', label: 'Desk' },
    { value: 'couch', label: 'Couch' },
    { value: 'handheld', label: 'Handheld' },
    { value: 'podcast', label: 'Podcast' }
  ]
  const moods = [
    { value: 'zone_out', label: 'Zone out', hint: 'Low friction' },
    { value: 'story_night', label: 'Story night', hint: 'Focused' },
    { value: 'short_session', label: 'Short session', hint: 'Quick run' },
    { value: 'finish_something', label: 'Finish something', hint: 'Progress' },
    { value: 'surprise_me', label: 'Surprise me', hint: 'Wildcard' }
  ]
  const deferReasons = [
    { value: 'not_in_the_mood', label: 'Not in the mood' },
    { value: 'too_long', label: 'Too long' },
    { value: 'too_demanding', label: 'Too demanding' },
    { value: 'bounced_off', label: 'Bounced off it' },
    { value: 'defer_for_now', label: 'Just not tonight' }
  ]
  const feedbackConfirmations = {
    more_like_this: 'Noted — more like this coming',
    less_like_this: 'Noted — fewer like this',
    deferred: "Noted — won't suggest this for a while"
  }

  if (recommendation !== lastRecommendation) {
    setLastRecommendation(recommendation)
    setActedOn({})
    setFeedback({})
    setReasonPickerFor(null)
  }

  useEffect(() => {
    fetchProfiles()
      .then(setProfiles)
      .catch(() => setProfiles([]))
  }, [])

  useEffect(() => {
    fetchPendingOutcome()
      .then(data => setPendingOutcome(data?.pending || null))
      .catch(() => setPendingOutcome(null))
  }, [])

  const withClear = (setter) => (value) => {
    setter(value)
    setActiveProfileId(null)
  }
  const setSessionMinutesClear = withClear(setSessionMinutes)
  const setSessionEnergyClear = withClear(setSessionEnergy)
  const setSessionContextClear = withClear(setSessionContext)
  const setMoodClear = withClear(setMood)
  const setGenreClear = withClear(setGenre)
  const setTagClear = withClear(setTag)
  const setLengthClear = withClear(setLength)
  const setAttentionClear = withClear(setAttention)
  const setUnplayedClear = withClear(setUnplayed)

  const PROFILE_FIELD_SETTERS = {
    available_minutes: setSessionMinutes,
    energy: setSessionEnergy,
    context: setSessionContext,
    mood: setMood,
    genre: setGenre,
    tag: setTag,
    length: setLength,
    attention_level: setAttention,
    unplayed_only: setUnplayed
  }

  const applyProfile = (profile) => {
    if (activeProfileId === profile.id) {
      setActiveProfileId(null)
      return
    }
    Object.entries(PROFILE_FIELD_SETTERS).forEach(([field, setter]) => {
      const value = profile[field]
      if (value !== null && value !== undefined) setter(value)
    })
    setActiveProfileId(profile.id)
    setProfileError('')
  }

  const handleSaveProfile = async () => {
    const name = window.prompt('Name this setup')
    if (!name) return
    const payload = {
      name,
      ...(mood && { mood }),
      ...(sessionMinutes && { available_minutes: sessionMinutes }),
      ...(sessionEnergy && { energy: sessionEnergy }),
      ...(sessionContext && { context: sessionContext }),
      ...(attention && { attention_level: attention }),
      ...(length && { length }),
      ...(genre && { genre }),
      ...(tag && { tag }),
      unplayed_only: unplayed
    }
    try {
      const created = await createProfile(payload)
      setProfiles(prev => [...prev, created])
      setProfileError('')
    } catch (err) {
      if (err.response?.status === 409) {
        setProfileError(`A profile named "${name}" already exists.`)
      } else {
        setProfileError('Could not save this setup.')
      }
    }
  }

  const handleDeleteProfile = async (id) => {
    if (!window.confirm('Delete this saved setup?')) return
    try {
      await deleteProfile(id)
      setProfiles(prev => prev.filter(p => p.id !== id))
      if (activeProfileId === id) setActiveProfileId(null)
      setProfileError('')
    } catch {
      setProfileError('Could not delete this setup.')
    }
  }

  const handleAct = async (appId, status) => {
    try {
      await updateGame(appId, { status })
      setActedOn(prev => ({ ...prev, [appId]: status }))
      postRecommendationDecision({
        game_id: appId,
        decision: status === 'playing' ? 'accepted_play' : 'accepted_queue',
        mood: mood || undefined
      }).catch(() => {})
    } catch (err) {
      console.error('Failed to update game:', err)
    }
  }

  const handleFeedback = (appId, decision, reason) => {
    postRecommendationDecision({ game_id: appId, decision, reason, mood: mood || undefined }).catch(() => {})
    setFeedback(prev => ({ ...prev, [appId]: { decision, confirmed: feedbackConfirmations[decision] } }))
    setReasonPickerFor(null)
  }

  const handleResetSession = () => {
    setSessionMinutes(null)
    setSessionEnergy(null)
    setSessionContext(null)
    setActiveProfileId(null)
  }

  const handleOutcome = (fit) => {
    if (!pendingOutcome) return
    postSessionOutcome({ decision_id: pendingOutcome.decision_id, fit })
      .then(() => {
        if (fit === 'skipped') {
          setPendingOutcome(null)
        } else {
          setOutcomeConfirmed(true)
        }
      })
      .catch(() => setPendingOutcome(null))
  }

  const sessionSummaryText = (snapshot) => {
    if (!snapshot) return ''
    const parts = []
    const timeOpt = timeOptions.find(o => o.value === snapshot.minutes)
    if (timeOpt) parts.push(timeOpt.label)
    const energyOpt = energyOptions.find(o => o.value === snapshot.energy)
    if (energyOpt) parts.push(`${energyOpt.label.toLowerCase()} energy`)
    const contextOpt = contextOptions.find(o => o.value === snapshot.context)
    if (contextOpt) parts.push(contextOpt.label.toLowerCase())
    return parts.join(' · ')
  }

  const handleRecommend = () => {
    setAppliedSession(
      (sessionMinutes || sessionEnergy || sessionContext)
        ? { minutes: sessionMinutes, energy: sessionEnergy, context: sessionContext }
        : null
    )
    getRec({
      ...(genre && { genre }),
      ...(tag && { tag }),
      ...(length && { length }),
      unplayed_only: unplayed,
      ...(attention && { attention_level: attention }),
      ...(mood && { mood }),
      ...(sessionMinutes && { available_minutes: sessionMinutes }),
      ...(sessionEnergy && { energy: sessionEnergy }),
      ...(sessionContext && { context: sessionContext })
    })
  }

  return (
    <div className="view concierge-view">
      {pendingOutcome && (
        <div className="outcome-card">
          {outcomeConfirmed ? (
            <span className="outcome-confirm">Noted — thanks</span>
          ) : (
            <>
              <span className="outcome-text">
                Last time you picked {pendingOutcome.game_name} — did it fit what you wanted?
              </span>
              <div className="outcome-actions">
                <button className="planner-chip" onClick={() => handleOutcome('great_fit')}>Great fit</button>
                <button className="planner-chip" onClick={() => handleOutcome('partly')}>Partly</button>
                <button className="planner-chip" onClick={() => handleOutcome('not_a_fit')}>Not really</button>
                <button className="outcome-skip" onClick={() => handleOutcome('skipped')}>Skip</button>
              </div>
            </>
          )}
        </div>
      )}
      <div className="butler-mode-toggle" role="group" aria-label="Butler mode">
        <button
          type="button"
          className={butlerMode === 'fresh' ? 'active' : ''}
          aria-pressed={butlerMode === 'fresh'}
          onClick={() => setButlerMode('fresh')}
        >
          Fresh pick
        </button>
        <button
          type="button"
          className={butlerMode === 'continue' ? 'active' : ''}
          aria-pressed={butlerMode === 'continue'}
          onClick={() => setButlerMode('continue')}
        >
          Continue something
        </button>
      </div>

      {butlerMode === 'fresh' && (
      <>
      <section className="card filter-section">
        <p className="eyebrow">Butler</p>
        <h2>What kind of session are you after?</h2>
        <div className="planner-section">
          <div className="filter-group profile-group">
            <label>Profiles:</label>
            <div className="planner-chip-row">
              {profiles.map(profile => (
                <button
                  key={profile.id}
                  type="button"
                  className={`planner-chip profile-chip ${activeProfileId === profile.id ? 'active' : ''}`}
                  onClick={() => applyProfile(profile)}
                >
                  {profile.name}
                  <span
                    className="profile-chip-delete"
                    role="button"
                    aria-label={`Delete profile ${profile.name}`}
                    title="Delete profile"
                    onClick={(e) => { e.stopPropagation(); handleDeleteProfile(profile.id) }}
                  >
                    ×
                  </span>
                </button>
              ))}
              <button type="button" className="planner-chip profile-save-chip" onClick={handleSaveProfile}>
                + Save setup…
              </button>
            </div>
            {profileError && <span className="profile-error-text">{profileError}</span>}
          </div>
          <div className="filter-group">
            <label>Time:</label>
            <div className="planner-chip-row">
              {timeOptions.map(option => (
                <button
                  key={option.value}
                  type="button"
                  className={`planner-chip ${sessionMinutes === option.value ? 'active' : ''}`}
                  onClick={() => setSessionMinutesClear(sessionMinutes === option.value ? null : option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
          <div className="filter-group">
            <label>Energy:</label>
            <div className="planner-chip-row">
              {energyOptions.map(option => (
                <button
                  key={option.value}
                  type="button"
                  className={`planner-chip ${sessionEnergy === option.value ? 'active' : ''}`}
                  onClick={() => setSessionEnergyClear(sessionEnergy === option.value ? null : option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
          <div className="filter-group">
            <label>Setting:</label>
            <div className="planner-chip-row">
              {contextOptions.map(option => (
                <button
                  key={option.value}
                  type="button"
                  className={`planner-chip ${sessionContext === option.value ? 'active' : ''}`}
                  onClick={() => setSessionContextClear(sessionContext === option.value ? null : option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
          {(sessionMinutes || sessionEnergy || sessionContext) && (
            <button type="button" className="planner-reset" onClick={handleResetSession}>
              Reset session
            </button>
          )}
        </div>
        <div className="mood-grid">
          {moods.map(option => (
            <button
              key={option.value}
              type="button"
              className={`mood-btn ${mood === option.value ? 'active' : ''}`}
              onClick={() => setMoodClear(mood === option.value ? '' : option.value)}
            >
              <strong>{option.label}</strong>
              <span>{option.hint}</span>
            </button>
          ))}
        </div>
        <details className="advanced-filters">
          <summary>Advanced filters</summary>
          <div className="filter-grid">
            <div className="filter-group">
              <label>Genre:</label>
              <input type="text" value={genre} onChange={(e) => setGenreClear(e.target.value)} placeholder="e.g. Action" />
            </div>
            <div className="filter-group">
              <label>Tag:</label>
              <input type="text" value={tag} onChange={(e) => setTagClear(e.target.value)} placeholder="e.g. Indie" />
            </div>
            <div className="filter-group">
              <label>Length:</label>
              <select value={length} onChange={(e) => setLengthClear(e.target.value)}>
                <option value="">Any Length</option>
                <option value="short">Short (&lt; 5h)</option>
                <option value="medium">Medium (5h - 20h)</option>
                <option value="long">Long (&gt; 20h)</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Attention:</label>
              <select value={attention} onChange={(e) => setAttentionClear(e.target.value)}>
                <option value="">Any</option>
                <option value="casual">☕ Casual</option>
                <option value="focused">🎯 Focused</option>
              </select>
            </div>
          </div>
          <div className="filter-group checkbox">
            <label>
              <input type="checkbox" checked={unplayed} onChange={(e) => setUnplayedClear(e.target.checked)} />
              Unplayed Only
            </label>
          </div>
        </details>
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
          {recommendation.header_image && (
            <img className="result-hero" src={recommendation.header_image} alt="" loading="lazy" />
          )}
          <div className="game-title">{recommendation.Name}</div>
          <div className="game-details">
            <span className="badge">{recommendation.Genre}</span>
            <span className="badge secondary">{recommendation.Tags.split(';')[0]}</span>
          </div>
          {recommendation.short_description && <p className="game-description">{recommendation.short_description}</p>}
          {appliedSession && (
            <p className="session-summary">Planned for: {sessionSummaryText(appliedSession)}</p>
          )}
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
          <div className="rec-actions">
            {actedOn[recommendation.AppID] ? (
              <span className="rec-acted">{actedOn[recommendation.AppID] === 'playing' ? '▶ Playing now' : '✓ Moved to Up Next'}</span>
            ) : (
              <>
                <button className="primary-btn" onClick={() => handleAct(recommendation.AppID, 'playing')} disabled={recommendation.status === 'playing'}>▶ Play now</button>
                <button className="secondary-btn" onClick={() => handleAct(recommendation.AppID, 'up_next')} disabled={recommendation.status === 'up_next'}>+ Up Next</button>
              </>
            )}
            <span className="rec-feedback" aria-live="polite">
              {feedback[recommendation.AppID] ? (
                <span className="rec-feedback-note">{feedback[recommendation.AppID].confirmed}</span>
              ) : (
                <>
                  <button className="secondary-btn" onClick={() => setReasonPickerFor(recommendation.AppID)}>Not tonight</button>
                  <button className="action-btn" onClick={() => handleFeedback(recommendation.AppID, 'more_like_this')}>👍 More like this</button>
                  <button className="action-btn" onClick={() => handleFeedback(recommendation.AppID, 'less_like_this')}>👎 Less like this</button>
                </>
              )}
            </span>
          </div>
          {reasonPickerFor === recommendation.AppID && (
            <div className="reason-picker">
              {deferReasons.map(reason => (
                <button
                  key={reason.value}
                  className="reason-chip"
                  aria-label={`Not tonight — ${reason.label}`}
                  onClick={() => handleFeedback(recommendation.AppID, 'deferred', reason.value)}
                >
                  {reason.label}
                </button>
              ))}
              <button
                className="reason-chip"
                aria-label="Not tonight — skip giving a reason"
                onClick={() => handleFeedback(recommendation.AppID, 'deferred')}
              >
                Skip
              </button>
            </div>
          )}
          {recommendation.alternates?.length > 0 && (
            <div className="alternates">
              <p className="alternates-label">Or try:</p>
              <div className="alternates-row">
                {recommendation.alternates.map(alt => (
                  <div className="alternate-card" key={alt.AppID}>
                    {alt.header_image ? (
                      <img src={alt.header_image} alt="" loading="lazy" />
                    ) : (
                      <div className="alternate-placeholder">{alt.Name?.slice(0, 1)}</div>
                    )}
                    <div className="alternate-info">
                      <span className="alternate-name">{alt.Name}</span>
                      {alt.reasons?.length > 0 && <span className="alternate-reason">{alt.reasons[0]}</span>}
                    </div>
                    <div className="alternate-actions">
                      {actedOn[alt.AppID] ? (
                        <span className="rec-acted">{actedOn[alt.AppID] === 'playing' ? '▶' : '✓'}</span>
                      ) : (
                        <>
                          <button className="action-btn" title="Play now" onClick={() => handleAct(alt.AppID, 'playing')} disabled={alt.status === 'playing'}>▶</button>
                          <button className="action-btn" title="Add to Up Next" onClick={() => handleAct(alt.AppID, 'up_next')} disabled={alt.status === 'up_next'}>+</button>
                        </>
                      )}
                      <span className="rec-feedback" aria-live="polite">
                        {feedback[alt.AppID] ? (
                          <span className="rec-acted" title={feedback[alt.AppID].confirmed}>✓</span>
                        ) : (
                          <>
                            <button className="action-btn" title="More like this" onClick={() => handleFeedback(alt.AppID, 'more_like_this')}>👍</button>
                            <button className="action-btn" title="Less like this" onClick={() => handleFeedback(alt.AppID, 'less_like_this')}>👎</button>
                          </>
                        )}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
      </>
      )}

      {butlerMode === 'continue' && <ContinuationLadder />}
    </div>
  )
}

function formatStatusLabel(status) {
  return (status || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function LadderCard({ item, played, onPlay }) {
  const estimate = item.remaining_estimate
  const estimateLabel = estimate?.label
    ? (estimate.label.startsWith('~') ? estimate.label : `~${estimate.label}`)
    : null

  return (
    <div className="ladder-card">
      {item.header_image ? (
        <img className="ladder-card-art" src={item.header_image} alt="" loading="lazy" />
      ) : (
        <div className="ladder-card-placeholder">{item.name?.slice(0, 1) || '?'}</div>
      )}
      <div className="ladder-card-info">
        <span className="ladder-card-name">{item.name}</span>
        <span className="badge secondary">{formatStatusLabel(item.status)}</span>
        {item.reasons?.length > 0 && (
          <ul className="ladder-reasons">
            {/* the estimate label renders on its own line below — don't repeat it */}
            {item.reasons.filter(reason => reason !== estimate?.label).map(reason => <li key={reason}>{reason}</li>)}
          </ul>
        )}
        {estimateLabel && <span className="ladder-estimate">{estimateLabel}</span>}
      </div>
      <div className="ladder-card-actions">
        {played ? (
          <span className="rec-acted">▶ Playing now</span>
        ) : (
          <button className="action-btn" title="Play now" onClick={() => onPlay(item.id)}>▶ Play now</button>
        )}
      </div>
    </div>
  )
}

function ContinuationLadder() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actedOn, setActedOn] = useState({})

  useEffect(() => {
    let cancelled = false
    fetchContinuation()
      .then(res => { if (!cancelled) setData(res) })
      .catch(err => {
        console.error('Failed to load continuation options:', err)
        if (!cancelled) setError('Failed to load continuation options.')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const handlePlay = async (gameId) => {
    try {
      await updateGame(gameId, { status: 'playing' })
      setActedOn(prev => ({ ...prev, [gameId]: true }))
    } catch (err) {
      console.error('Failed to update game:', err)
    }
  }

  const groups = [
    { key: 'short', title: 'Quick dip (15–30 min)', items: data?.short || [] },
    { key: 'session', title: 'One session', items: data?.session || [] },
    { key: 'finish', title: 'Finish this week', items: data?.finish || [] }
  ]
  const totalItems = groups.reduce((sum, group) => sum + group.items.length, 0)

  return (
    <div className="continuation-ladder">
      {error && <div className="error-card">{error}</div>}
      {loading && <LoadingState label="Butler is checking what's in progress..." />}
      {!loading && !error && totalItems === 0 && (
        <EmptyState
          title="Nothing to continue yet"
          message="No started or queued games with trustworthy estimates yet."
        />
      )}
      {!loading && !error && totalItems > 0 && groups.map(group => (
        <section className="ladder-group" key={group.key}>
          <h3>{group.title}</h3>
          {group.items.length === 0 ? (
            <p className="empty-hint">Nothing safe to suggest here yet.</p>
          ) : (
            <div className="game-list">
              {group.items.map(item => (
                <LadderCard
                  key={item.id}
                  item={item}
                  played={!!actedOn[item.id]}
                  onPlay={handlePlay}
                />
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  )
}

function ResumeCard({ candidate, onOpenDetail }) {
  if (!candidate) return null

  return (
    <section className="card resume-card">
      <div className="resume-card-media">
        {candidate.header_image ? (
          <img className="resume-card-art" src={candidate.header_image} alt="" loading="lazy" />
        ) : (
          <div className="resume-card-placeholder">{candidate.name?.slice(0, 1) || '?'}</div>
        )}
      </div>
      <div className="resume-card-body">
        <span className="eyebrow">Resume</span>
        <button className="resume-card-name" onClick={() => onOpenDetail(candidate.id)}>{candidate.name}</button>
        {candidate.return_when && (
          <p className="resume-card-line">Return when: {candidate.return_when}</p>
        )}
        {candidate.current_note && (
          <p className="resume-card-line">Where you left off: {candidate.current_note}</p>
        )}
        {candidate.remaining_estimate?.label && (
          <p className="resume-card-estimate">{candidate.remaining_estimate.label}</p>
        )}
        {candidate.reasons?.length > 0 && (
          <div className="resume-card-reasons">
            {candidate.reasons.map(reason => (
              <span className="badge secondary" key={reason}>{reason}</span>
            ))}
          </div>
        )}
      </div>
      <div className="resume-card-actions">
        {candidate.launch_url ? (
          <a className="primary-btn resume-card-launch" href={candidate.launch_url}>Launch</a>
        ) : (
          <span className="resume-card-launch-disabled">No launcher link</span>
        )}
      </div>
    </section>
  )
}

function ArchaeologyCard({ game, onOpenDetail, onUpNext, onDefer, onDismiss }) {
  return (
    <div className="archaeology-card">
      {game.header_image ? (
        <img className="archaeology-card-art" src={game.header_image} alt="" loading="lazy" />
      ) : (
        <div className="archaeology-card-placeholder">{game.name?.slice(0, 1) || '?'}</div>
      )}
      <div className="archaeology-card-body">
        <button className="archaeology-card-name" onClick={() => onOpenDetail(game.id)}>{game.name}</button>
        {game.reasons?.length > 0 && (
          <div className="archaeology-card-reasons">
            {game.reasons.map(reason => (
              <span className="badge secondary" key={reason}>{reason}</span>
            ))}
          </div>
        )}
      </div>
      <div className="archaeology-card-actions">
        <button className="action-btn primary" title="Add to Up Next" onClick={() => onUpNext(game.id)}>Up Next</button>
        <button className="action-btn" title="Remind me later" onClick={() => onDefer(game.id)}>Later</button>
        <button className="action-btn" title="Not interested" onClick={() => onDismiss(game.id)}>Not interested</button>
      </div>
    </div>
  )
}

function DashboardView({ games, onMove, onAttentionChange, onOpenDetail }) {
  const [activity, setActivity] = useState(null)
  const [resumeCandidate, setResumeCandidate] = useState(null)
  const [digs, setDigs] = useState([])

  useEffect(() => {
    fetchActivity().then(setActivity).catch(() => {})
    fetchResume().then(res => setResumeCandidate(res?.candidate ?? null)).catch(() => {})
    fetchArchaeology().then(res => setDigs(res?.digs ?? [])).catch(() => {})
  }, [])

  const handleArchaeologyUpNext = async (gameId) => {
    await onMove(gameId, 'up_next')
    setDigs(prev => prev.filter(dig => dig.id !== gameId))
  }

  const handleArchaeologyDismiss = async (gameId, action) => {
    try {
      await dismissArchaeology(gameId, action)
    } catch (err) {
      console.error('Failed to update archaeology dig:', err)
    } finally {
      setDigs(prev => prev.filter(dig => dig.id !== gameId))
    }
  }

  const playing = games.filter(g => g.status === 'playing')
  const upNext = games
    .filter(g => g.status === 'up_next')
    .sort((a, b) => (a.queue_position ?? 9999) - (b.queue_position ?? 9999) || a.name.localeCompare(b.name))

  return (
    <div className="view dashboard-view">
      <ResumeCard candidate={resumeCandidate} onOpenDetail={onOpenDetail} />
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
                onOpenDetail={onOpenDetail}
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
                onOpenDetail={onOpenDetail}
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

        <section className="dashboard-column">
          <h2>Recent Activity</h2>
          {activity ? (
            <>
              <div className="game-meta">
                <span className="badge">🕐 {(activity.minutes_this_week / 60).toFixed(1)}h this week</span>
                <span className="badge secondary">▶ {activity.started_this_month} started</span>
                <span className="badge secondary">✔ {activity.finished_this_month} finished</span>
              </div>
              {activity.events.length === 0 ? (
                <EmptyState title="No activity yet" message="Play, finish, or sync games to build your history." />
              ) : (
                <ul className="activity-list">
                  {activity.events.map(ev => (
                    <li key={ev.id ?? `${ev.game_id}-${ev.created_at}`} className="activity-item">
                      {ev.header_image && <img className="activity-thumb" src={ev.header_image} alt="" loading="lazy" />}
                      <strong>{ev.game_name}</strong>{' '}
                      {ev.event_type === 'playtime'
                        ? `+${((ev.new_value - ev.old_value) / 60).toFixed(1)}h played`
                        : ev.new_value === 'playing' ? 'started'
                        : ev.new_value === 'completed' ? 'finished'
                        : ev.new_value === 'abandoned' ? 'abandoned'
                        : `moved to ${ev.new_value.replace('_', ' ')}`}
                      <span className="activity-date"> · {new Date(ev.created_at).toLocaleDateString()}</span>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <EmptyState title="No activity yet" message="Play, finish, or sync games to build your history." />
          )}
        </section>
      </div>

      {digs.length > 0 && (
        <section className="archaeology-section">
          <h2>From the archives</h2>
          <p className="archaeology-subtitle">Games you own that might deserve another look — no obligation.</p>
          <div className="archaeology-row">
            {digs.map(game => (
              <ArchaeologyCard
                key={game.id}
                game={game}
                onOpenDetail={onOpenDetail}
                onUpNext={handleArchaeologyUpNext}
                onDefer={(id) => handleArchaeologyDismiss(id, 'deferred')}
                onDismiss={(id) => handleArchaeologyDismiss(id, 'dismissed')}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

const SAVED_FILTERS_KEY = 'gamebutler.savedFilters'

function loadSavedFiltersFromStorage() {
  try {
    const raw = localStorage.getItem(SAVED_FILTERS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch (err) {
    console.error('Failed to read saved filters:', err)
    return []
  }
}

function persistSavedFilters(filters) {
  try {
    localStorage.setItem(SAVED_FILTERS_KEY, JSON.stringify(filters))
  } catch (err) {
    console.error('Failed to persist saved filters:', err)
  }
}

const LIBRARY_PRESETS = [
  { key: 'uncategorized', label: 'Uncategorized' },
  { key: 'never_played', label: 'Never played' },
  { key: 'started_not_active', label: 'Started, not active' },
  { key: 'deferred', label: 'Deferred' }
]

function timeAgo(iso) {
  const d = new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`)
  const mins = Math.max(0, Math.floor((Date.now() - d.getTime()) / 60000))
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  if (mins < 1440) return `${Math.floor(mins / 60)}h ago`
  return `${Math.floor(mins / 1440)}d ago`
}

function LibraryView({ onMove, onAttentionChange, onOpenDetail }) {
  const [games, setGames] = useState([])
  const [search, setSearch] = useState('')
  const [attentionFilter, setAttentionFilter] = useState('')
  const [platformFilter, setPlatformFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [preset, setPreset] = useState('')
  const [savedFilters, setSavedFilters] = useState(() => loadSavedFiltersFromStorage())
  const [loading, setLoading] = useState(false)
  const [enriching, setEnriching] = useState(false)
  const [enrichmentJob, setEnrichmentJob] = useState(null)
  const [autoTagMsg, setAutoTagMsg] = useState('')
  const [automation, setAutomation] = useState(null)
  const [selectMode, setSelectMode] = useState(false)
  const [selected, setSelected] = useState(new Set())
  const [bulkStatus, setBulkStatus] = useState('')
  const [bulkAttention, setBulkAttention] = useState('')
  const [bulkSessionTags, setBulkSessionTags] = useState('')
  const [bulkApplying, setBulkApplying] = useState(false)

  const loadLibrary = useCallback(async () => {
    setLoading(true)
    try {
      const params = { status: 'library' }
      if (attentionFilter) params.attention_level = attentionFilter
      if (platformFilter) params.platform = platformFilter
      if (search) params.search = search
      if (preset === 'uncategorized') params.attention_level = 'unset'
      else if (preset === 'never_played') params.played = false
      else if (preset === 'started_not_active') params.played = true
      else if (preset === 'deferred') params.status = 'paused'
      const data = await fetchGames(params)
      setGames(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [attentionFilter, platformFilter, search, preset])

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
    fetchAutomationStatus().then(setAutomation).catch(() => {})
  }, [])

  useEffect(() => {
    if (!enrichmentJob || enrichmentJob.status !== 'running') return

    let cancelled = false
    let consecutiveErrors = 0
    const timer = setInterval(async () => {
      try {
        const job = await fetchEnrichmentJob(enrichmentJob.id)
        if (cancelled) return
        consecutiveErrors = 0
        setEnrichmentJob(job)
        setEnriching(job.status === 'running')
        if (job.status !== 'running') {
          clearInterval(timer)
          loadLibrary()
        }
      } catch (err) {
        console.error(err)
        if (cancelled) return
        consecutiveErrors += 1
        if (consecutiveErrors >= 5) {
          setEnriching(false)
          setAutoTagMsg('Lost contact with server — enrichment may still be running.')
          clearInterval(timer)
        }
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
    setSelected(new Set())
  }

  const handleAttentionFilterChange = (e) => {
    setAttentionFilter(e.target.value)
    setSelected(new Set())
  }

  const handlePlatformFilterChange = (e) => {
    setPlatformFilter(e.target.value)
    setSelected(new Set())
  }

  const handleSourceFilterChange = (e) => {
    setSourceFilter(e.target.value)
    setSelected(new Set())
  }

  const handleTogglePreset = (key) => {
    setPreset(prev => prev === key ? '' : key)
    setSelected(new Set())
  }

  const handleDelete = async (game) => {
    if (!window.confirm(`Remove ${game.name} from your library? This also deletes its activity history.`)) return
    try {
      await deleteGame(game.id)
      loadLibrary()
    } catch (err) {
      console.error(err)
      setAutoTagMsg(err.response?.data?.detail || 'Failed to remove game.')
      setTimeout(() => setAutoTagMsg(''), 5000)
    }
  }

  const handleToggleSelectMode = () => {
    setSelectMode(prev => !prev)
    setSelected(new Set())
  }

  const handleToggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleBulkApply = async () => {
    if (selected.size === 0) return
    const payload = { app_ids: Array.from(selected) }
    if (bulkStatus) payload.status = bulkStatus
    if (bulkAttention) payload.attention_level = bulkAttention
    if (bulkSessionTags === 'clear') payload.session_tags = null
    else if (bulkSessionTags) payload.session_tags = bulkSessionTags

    if (!window.confirm(`Apply changes to ${selected.size} games?`)) return

    setBulkApplying(true)
    try {
      const res = await bulkUpdateGames(payload)
      setAutoTagMsg(`Updated ${res.updated} games`)
      setSelected(new Set())
      setBulkStatus('')
      setBulkAttention('')
      setBulkSessionTags('')
      loadLibrary()
      setTimeout(() => setAutoTagMsg(''), 3000)
    } catch (err) {
      console.error(err)
      setAutoTagMsg(err.response?.data?.detail || 'Failed to update games.')
      setTimeout(() => setAutoTagMsg(''), 5000)
    } finally {
      setBulkApplying(false)
    }
  }

  const handleSaveFilter = () => {
    const name = window.prompt('Name this filter:')
    if (name === null) return
    const trimmed = name.trim()
    if (!trimmed) {
      setAutoTagMsg('Filter name cannot be empty.')
      setTimeout(() => setAutoTagMsg(''), 3000)
      return
    }
    if (savedFilters.some(f => f.name.toLowerCase() === trimmed.toLowerCase())) {
      setAutoTagMsg(`A filter named "${trimmed}" already exists.`)
      setTimeout(() => setAutoTagMsg(''), 3000)
      return
    }
    const next = [...savedFilters, { name: trimmed, search, attention: attentionFilter, platform: platformFilter, preset }]
    setSavedFilters(next)
    persistSavedFilters(next)
  }

  const handleApplySavedFilter = (filter) => {
    setSearch(filter.search || '')
    setAttentionFilter(filter.attention || '')
    setPlatformFilter(filter.platform || '')
    setPreset(filter.preset || '')
    setSelected(new Set())
  }

  const handleDeleteSavedFilter = (name) => {
    const next = savedFilters.filter(f => f.name !== name)
    setSavedFilters(next)
    persistSavedFilters(next)
  }

  const handleEditGenre = async (game) => {
    const genre = window.prompt(`Genre for ${game.name}:`, game.genre === 'Unknown' ? '' : game.genre)
    if (genre === null) return
    try {
      await updateGame(game.id, { genre: genre.trim() || 'Unknown' })
      loadLibrary()
    } catch (err) {
      console.error(err)
    }
  }

  const truncate = (s, n) => (s && s.length > n ? `${s.slice(0, n)}…` : s)
  const automationParts = []
  if (automation?.last_sync) {
    const { finished_at, success, message } = automation.last_sync
    if (success === false) {
      automationParts.push({ text: `Sync failed: ${truncate(message, 60)}`, isError: true })
    } else {
      automationParts.push({ text: `Synced ${timeAgo(finished_at)}` })
    }
  }
  if (automation?.last_enrichment) {
    const { status, processed, total, succeeded, failed, error_summary } = automation.last_enrichment
    if (status === 'completed') {
      automationParts.push({ text: `enriched ${succeeded}${failed > 0 ? `, ${failed} failed` : ''}` })
    } else if (status === 'failed') {
      automationParts.push({ text: `enrichment failed: ${truncate(error_summary, 60)}`, isError: true })
    } else if (status === 'running') {
      automationParts.push({ text: `enriching ${processed}/${total}…` })
    }
  }

  const sourceOptions = Array.from(new Set(games.map(g => g.source).filter(Boolean))).sort()
  const visibleGames = sourceFilter ? games.filter(g => g.source === sourceFilter) : games

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
          <select value={attentionFilter} onChange={handleAttentionFilterChange} className="att-filter">
            <option value="">All Attention</option>
            <option value="unset">Uncategorized</option>
            <option value="casual">☕ Casual</option>
            <option value="focused">🎯 Focused</option>
          </select>
          <select value={platformFilter} onChange={handlePlatformFilterChange} className="att-filter">
            <option value="">All Platforms</option>
            <option value="steam">Steam</option>
            <option value="switch">Switch</option>
            <option value="playstation">PlayStation</option>
            <option value="xbox">Xbox</option>
            <option value="pc">PC</option>
            <option value="retro">Retro</option>
          </select>
          <select value={sourceFilter} onChange={handleSourceFilterChange} className="att-filter">
            <option value="">All Sources</option>
            {sourceOptions.map(source => (
              <option key={source} value={source}>{source}</option>
            ))}
          </select>
          <button className="secondary-btn" onClick={handleSync} disabled={loading || enriching}>🔄 Sync Steam</button>
          <button className="secondary-btn" onClick={handleAutoTag} disabled={loading} title="Auto-tag uncategorized games">
            🪄 Auto-Tag
          </button>
          <button className="secondary-btn" onClick={handleEnrich} disabled={loading || enriching} title="Fetch metadata from Steam">
            {enriching ? 'Enriching...' : '☁️ Enrich'}
          </button>
          <button className={`secondary-btn ${selectMode ? 'active' : ''}`} onClick={handleToggleSelectMode}>
            {selectMode ? '✓ Selecting' : 'Select'}
          </button>
          {selectMode && <span className="selected-count">{selected.size} selected</span>}
        </div>
        <div className="preset-row">
          {LIBRARY_PRESETS.map(opt => (
            <button
              key={opt.key}
              type="button"
              className={`planner-chip ${preset === opt.key ? 'active' : ''}`}
              onClick={() => handleTogglePreset(opt.key)}
            >
              {opt.label}
            </button>
          ))}
          {savedFilters.map(filter => (
            <span key={filter.name} className="saved-filter-chip">
              <button type="button" className="planner-chip" onClick={() => handleApplySavedFilter(filter)}>
                {filter.name}
              </button>
              <button
                type="button"
                className="chip-remove"
                aria-label={`Delete saved filter ${filter.name}`}
                onClick={() => handleDeleteSavedFilter(filter.name)}
              >
                ✕
              </button>
            </span>
          ))}
          {(search || attentionFilter || platformFilter || preset) && (
            <button type="button" className="secondary-btn" onClick={handleSaveFilter}>Save filter</button>
          )}
        </div>
        <p className="library-count">{visibleGames.length} games</p>
        {autoTagMsg && <p className="success-msg">{autoTagMsg}</p>}
        {automationParts.length > 0 && (
          <p className="automation-status">
            {automationParts.map((part, i) => (
              <span key={i}>
                {i > 0 && ' · '}
                {part.isError ? <span className="status-error">{part.text}</span> : part.text}
              </span>
            ))}
          </p>
        )}
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
          {visibleGames.map(game => (
            <GameCard
              key={game.id}
              game={game}
              onMove={(id, status) => {
                onMove(id, status)
                setGames(games.filter(g => g.id !== id))
              }}
              onAttentionChange={async (id, level) => {
                const updated = await onAttentionChange(id, level)
                if (updated) setGames(prev => prev.map(g => g.id === id ? updated : g))
              }}
              actions={[{ label: 'Add to Up Next', status: 'up_next', className: 'primary' }]}
              onDelete={handleDelete}
              onEditGenre={handleEditGenre}
              onOpenDetail={onOpenDetail}
              selectable={selectMode}
              selectedState={selected.has(game.id)}
              onToggleSelect={handleToggleSelect}
            />
          ))}
          {visibleGames.length === 0 && (
            <EmptyState title="No games found" message="Try a different search or attention filter." />
          )}
        </div>
      )}
      {selectMode && selected.size > 0 && (
        <div className="bulk-bar">
          <span className="bulk-count">{selected.size} selected</span>
          <select value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value)}>
            <option value="">— Status —</option>
            <option value="library">Library</option>
            <option value="up_next">Up Next</option>
            <option value="playing">Playing</option>
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
            <option value="abandoned">Abandoned</option>
          </select>
          <div className="attention-btns">
            {[
              { value: 'casual', label: '☕', className: 'btn-casual' },
              { value: 'focused', label: '🎯', className: 'btn-focused' },
              { value: 'unset', label: 'None', className: 'btn-unset' }
            ].map(opt => (
              <button
                key={opt.value}
                type="button"
                className={`att-btn ${opt.className} ${bulkAttention === opt.value ? 'active' : ''}`}
                onClick={() => setBulkAttention(bulkAttention === opt.value ? '' : opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <select value={bulkSessionTags} onChange={(e) => setBulkSessionTags(e.target.value)}>
            <option value="">— Session tags —</option>
            <option value="burst_friendly">Burst-friendly</option>
            <option value="controller_only">Controller only</option>
            <option value="podcast_friendly">Podcast-friendly</option>
            <option value="clear">Clear tags</option>
          </select>
          <button
            className="primary-btn"
            onClick={handleBulkApply}
            disabled={bulkApplying || !(bulkStatus || bulkAttention || bulkSessionTags)}
          >
            {bulkApplying ? 'Applying...' : 'Apply'}
          </button>
          <button className="secondary-btn" onClick={() => setSelected(new Set())}>Clear selection</button>
        </div>
      )}
    </div>
  )
}

function BacklogView({ onMove, onAttentionChange, onOpenDetail }) {
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(false)
  const statuses = [
    { key: 'library', title: 'Backlog' },
    { key: 'up_next', title: 'Up Next' },
    { key: 'playing', title: 'Playing' },
    { key: 'paused', title: 'Paused' },
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
                      onAttentionChange={async (id, level) => {
                        const updated = await onAttentionChange(id, level)
                        if (updated) setGames(prev => prev.map(g => g.id === id ? updated : g))
                      }}
                      onOpenDetail={onOpenDetail}
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
  const [manualName, setManualName] = useState('')
  const [manualPlatform, setManualPlatform] = useState('switch')
  const [manualMsg, setManualMsg] = useState('')
  const [addingGame, setAddingGame] = useState(false)

  const [extFile, setExtFile] = useState(null)
  const [extPreview, setExtPreview] = useState(null)
  const [extReplaceMetadata, setExtReplaceMetadata] = useState(false)
  const [extResultMsg, setExtResultMsg] = useState('')
  const [extErrorMsg, setExtErrorMsg] = useState('')
  const [extPreviewing, setExtPreviewing] = useState(false)
  const [extImporting, setExtImporting] = useState(false)

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

  const handleAddGame = async (e) => {
    e.preventDefault()
    if (!manualName.trim() || addingGame) return
    setAddingGame(true)
    try {
      const game = await addGame({ name: manualName.trim(), platform: manualPlatform })
      setManualMsg(`Added ${game.name}${game.header_image ? ' (art found)' : ''}`)
      setManualName('')
      setTimeout(() => setManualMsg(''), 5000)
    } catch (err) {
      console.error(err)
      setManualMsg(err.response?.data?.detail || 'Failed to add game.')
      setTimeout(() => setManualMsg(''), 8000)
    } finally {
      setAddingGame(false)
    }
  }

  const handleExtFileChange = (event) => {
    const file = event.target.files[0]
    setExtFile(file || null)
    setExtPreview(null)
    setExtResultMsg('')
    setExtErrorMsg('')
    setExtReplaceMetadata(false)
  }

  const handleExtPreview = async () => {
    if (!extFile) return
    setExtPreviewing(true)
    setExtErrorMsg('')
    setExtResultMsg('')
    try {
      const res = await previewExternalImport(extFile)
      setExtPreview(res)
    } catch (err) {
      console.error(err)
      setExtErrorMsg(err.response?.data?.detail || 'Preview failed.')
      setExtPreview(null)
    } finally {
      setExtPreviewing(false)
    }
  }

  const handleExtImport = async () => {
    if (!extFile || !extPreview) return
    setExtImporting(true)
    setExtErrorMsg('')
    try {
      const res = await importExternalLibrary(extFile, extReplaceMetadata)
      setExtResultMsg(`Imported ${res.imported} new, updated ${res.updated}, skipped ${res.skipped}.`)
      setExtPreview(null)
      setExtFile(null)
      onUploaded()
    } catch (err) {
      console.error(err)
      setExtErrorMsg(err.response?.data?.detail || 'Import failed.')
    } finally {
      setExtImporting(false)
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

      <section className="card">
        <p className="eyebrow">Unified Library</p>
        <h2>External library import</h2>
        <p>Bring in games from Switch, PlayStation, Xbox, PC, or Retro. The CSV needs <code>title</code>, <code>platform</code>, and <code>source</code> columns; <code>external_id</code>, <code>genre</code>, <code>tags</code>, and <code>playtime_minutes</code> are optional.</p>
        <p className="import-note">Imports are local to your GameButler. No platform account credentials are requested or stored.</p>
        <input type="file" accept=".csv" onChange={handleExtFileChange} disabled={extPreviewing || extImporting} />
        <button className="secondary-btn" onClick={handleExtPreview} disabled={!extFile || extPreviewing || extImporting}>
          {extPreviewing ? 'Previewing...' : 'Preview import'}
        </button>
        {extPreview && (
          <div className="import-preview-panel">
            <p>{extPreview.total_rows} rows in {extPreview.filename}</p>
            <div className="import-preview-stats">
              <span className="badge secondary">New {extPreview.new}</span>
              <span className="badge secondary">Updated {extPreview.updated}</span>
              <span className="badge secondary">Skipped {extPreview.skipped}</span>
              <span className="badge secondary">Duplicates {extPreview.duplicates}</span>
              <span className="badge secondary">Invalid {extPreview.invalid.length}</span>
            </div>
            {extPreview.invalid.length > 0 && (
              <ul className="import-invalid-list">
                {extPreview.invalid.map((issue, i) => (
                  // backend error strings already carry the "Row N:" prefix
                  <li key={i}>{issue.error}</li>
                ))}
              </ul>
            )}
            <div className="filter-group checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={extReplaceMetadata}
                  onChange={(e) => setExtReplaceMetadata(e.target.checked)}
                />
                Replace genre/tags/playtime from file for existing games
              </label>
              <p className="empty-hint">Personal notes, ratings, and status are never touched.</p>
            </div>
            <button className="primary-btn" onClick={handleExtImport} disabled={extImporting}>
              {extImporting ? 'Importing...' : 'Confirm import'}
            </button>
          </div>
        )}
        {extErrorMsg && <div className="error-card">{extErrorMsg}</div>}
        {extResultMsg && <p className="success-msg">{extResultMsg}</p>}
      </section>

      <section className="card">
        <p className="eyebrow">Manual</p>
        <h2>Add a game manually</h2>
        <p>For Switch, PlayStation, Xbox, or anything else outside Steam.</p>
        <form onSubmit={handleAddGame}>
          <div className="filter-grid">
            <div className="filter-group">
              <label>Name:</label>
              <input type="text" value={manualName} onChange={(e) => setManualName(e.target.value)} placeholder="e.g. Tears of the Kingdom" />
            </div>
            <div className="filter-group">
              <label>Platform:</label>
              <select value={manualPlatform} onChange={(e) => setManualPlatform(e.target.value)}>
                <option value="switch">Switch</option>
                <option value="playstation">PlayStation</option>
                <option value="xbox">Xbox</option>
                <option value="pc">PC (non-Steam)</option>
                <option value="retro">Retro</option>
              </select>
            </div>
          </div>
          <button className="primary-btn" type="submit" disabled={!manualName.trim() || addingGame}>{addingGame ? 'Adding...' : 'Add Game'}</button>
        </form>
        {manualMsg && <p className="success-msg">{manualMsg}</p>}
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
  const [detailAppId, setDetailAppId] = useState(null)

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
      setDashboardGames(prev => prev.map(g => g.id === appId ? updated : g))
      // If we are in concierge, and the recommendation matches, update it
      if (recommendation && recommendation.AppID === appId) {
        setRecommendation({ ...recommendation, attention_level })
      }
      return updated
    } catch (err) {
      console.error('Failed to update attention:', err)
      return null
    }
  }

  const handleGameChanged = () => {
    loadLibraryCount()
    if (currentView === 'dashboard') {
      loadDashboard()
    }
  }

  const handleGetRec = async (params) => {
    setLoading(true)
    setError(null)
    setRecommendation(null)
    try {
      const data = await getRecommendation({ ...params, count: 3 })
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
            onOpenDetail={setDetailAppId}
          />
        )}
        {currentView === 'library' && (
          <LibraryView
            onMove={handleMove}
            onAttentionChange={handleAttentionChange}
            onOpenDetail={setDetailAppId}
          />
        )}
        {currentView === 'backlog' && (
          <BacklogView
            onMove={handleMove}
            onAttentionChange={handleAttentionChange}
            onOpenDetail={setDetailAppId}
          />
        )}
        {currentView === 'upload' && (
          <UploadView onUploaded={loadLibraryCount} />
        )}
      </main>

      {detailAppId && (
        <GameDetailDrawer
          appId={detailAppId}
          onClose={() => setDetailAppId(null)}
          onGameChanged={handleGameChanged}
        />
      )}
    </div>
  )
}

export default App
