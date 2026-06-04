import { useState } from 'react'
import { analyzeTeam, recommendTeam } from '../api'

const TYPE_COLORS = {
  Fire:'#F08030',Water:'#6890F0',Grass:'#78C850',Electric:'#F8D030',
  Ice:'#98D8D8',Fighting:'#C03028',Poison:'#A040A0',Ground:'#E0C068',
  Flying:'#A890F0',Psychic:'#F85888',Bug:'#A8B820',Rock:'#B8A038',
  Ghost:'#705898',Dragon:'#7038F8',Dark:'#705848',Steel:'#B8B8D0',
  Fairy:'#EE99AC',Normal:'#A8A878',
}

function TypeBadge({ type }) {
  return (
    <span className="px-2 py-0.5 rounded text-xs font-bold text-white"
      style={{ backgroundColor: TYPE_COLORS[type] || '#666' }}>
      {type}
    </span>
  )
}

function Card({ title, children }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      {title && <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h2>}
      {children}
    </div>
  )
}

function ScoreBar({ value, max = 1, color = 'bg-blue-500' }) {
  const pct = Math.round((value / max) * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-800 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-10 text-right">{(value * 100).toFixed(0)}%</span>
    </div>
  )
}

export default function TeamBuilder() {
  const [input, setInput] = useState('')
  const [team, setTeam] = useState([])
  const [report, setReport] = useState(null)
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const addPokemon = () => {
    const name = input.trim()
    if (!name) return
    if (team.length >= 6) { setError('Team is full (max 6)'); return }
    if (team.includes(name)) { setError(`${name} is already on the team`); return }
    setTeam([...team, name])
    setInput('')
    setError('')
    setReport(null)
    setRecs([])
  }

  const removePokemon = (name) => {
    setTeam(team.filter(p => p !== name))
    setReport(null)
    setRecs([])
  }

  const analyze = async () => {
    if (team.length === 0) return
    setLoading(true)
    setError('')
    try {
      const [r, rec] = await Promise.all([
        analyzeTeam(team),
        team.length < 6 ? recommendTeam(team, 10) : Promise.resolve({ data: [] })
      ])
      setReport(r.data)
      setRecs(rec.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setTeam([])
    setReport(null)
    setRecs([])
    setError('')
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Input */}
      <Card title="Build Your Team">
        <div className="flex gap-2 mb-4">
          <input
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-red-500"
            placeholder="Enter Pokémon name (e.g. Great Tusk)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addPokemon()}
          />
          <button onClick={addPokemon}
            className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded-lg text-sm font-medium transition-colors">
            Add
          </button>
          <button onClick={reset}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition-colors">
            Reset
          </button>
        </div>

        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

        <div className="flex flex-wrap gap-2 mb-4 min-h-8">
          {team.map(p => (
            <span key={p} className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm">
              {p}
              <button onClick={() => removePokemon(p)} className="text-gray-500 hover:text-red-400 text-xs">✕</button>
            </span>
          ))}
          {team.length === 0 && <span className="text-gray-600 text-sm">No Pokémon added yet</span>}
        </div>

        <div className="flex items-center gap-3">
          <button onClick={analyze} disabled={team.length === 0 || loading}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors">
            {loading ? 'Analyzing...' : 'Analyze Team'}
          </button>
          <span className="text-gray-500 text-sm">{team.length}/6 Pokémon</span>
        </div>
      </Card>

      {report && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Threat score */}
          <Card title="Threat Score">
            <div className="flex items-center gap-4 mb-4">
              <div className={`text-4xl font-bold ${
                report.threat_score < 0.3 ? 'text-green-400' :
                report.threat_score < 0.5 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {(report.threat_score * 100).toFixed(0)}
              </div>
              <div className="text-sm text-gray-400">
                <div>{report.threat_score < 0.3 ? '✓ Strong team' : report.threat_score < 0.5 ? '⚠ Some weaknesses' : '✗ Significant gaps'}</div>
                <div className="text-xs text-gray-500">Lower is better (0–100)</div>
              </div>
            </div>
          </Card>

          {/* Speed */}
          <Card title="Speed Tier">
            <div className="grid grid-cols-3 gap-3 mb-3">
              {[['Max', report.speed_gaps?.max_speed], ['Avg', report.speed_gaps?.avg_speed?.toFixed(0)], ['Min', report.speed_gaps?.min_speed]].map(([label, val]) => (
                <div key={label} className="bg-gray-800 rounded-lg p-3 text-center">
                  <div className="text-xs text-gray-500 mb-1">{label}</div>
                  <div className="text-xl font-bold text-blue-400">{val ?? '—'}</div>
                </div>
              ))}
            </div>
            {report.speed_gaps?.outsped_by?.length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-1">Outsped by:</div>
                <div className="text-xs text-red-400">{report.speed_gaps.outsped_by.join(', ')}</div>
              </div>
            )}
          </Card>

          {/* Type holes */}
          <Card title="Type Holes">
            {report.type_holes?.length === 0
              ? <p className="text-green-400 text-sm">No significant type holes detected</p>
              : (
                <div className="space-y-2">
                  {report.type_holes.map(h => (
                    <div key={h.type} className="flex items-center gap-3">
                      <TypeBadge type={h.type} />
                      <div className="flex-1 bg-gray-800 rounded-full h-2">
                        <div className="bg-red-500 h-2 rounded-full" style={{ width: `${Math.min(100, (h.exposure / 12) * 100)}%` }} />
                      </div>
                      <span className="text-xs text-gray-400">exp: {h.exposure}</span>
                    </div>
                  ))}
                </div>
              )
            }
          </Card>

          {/* Role gaps */}
          <Card title="Role Coverage">
            {report.role_gaps?.length === 0
              ? <p className="text-green-400 text-sm">All key roles covered</p>
              : (
                <ul className="space-y-1">
                  {report.role_gaps.map((g, i) => (
                    <li key={i} className="text-sm text-yellow-400 flex items-start gap-2">
                      <span>⚠</span><span>{g}</span>
                    </li>
                  ))}
                </ul>
              )
            }
          </Card>

          {/* Archetype flags */}
          <Card title="Archetype Weaknesses">
            <div className="space-y-2">
              {Object.entries(report.archetype_flags || {}).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-sm text-gray-300 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${val ? 'bg-red-900 text-red-300' : 'bg-green-900 text-green-300'}`}>
                    {val ? 'WEAK' : 'OK'}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Meta coverage */}
          <Card title="Meta Coverage">
            <div className="mb-2">
              <span className="text-2xl font-bold text-blue-400">{report.meta_coverage?.score}</span>
              <span className="text-gray-500 text-sm"> / {report.meta_coverage?.total} top threats covered</span>
            </div>
            {report.meta_coverage?.uncovered?.length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-1">Uncovered:</div>
                <div className="text-xs text-red-400">{report.meta_coverage.uncovered.join(', ')}</div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Recommendations */}
      {recs.length > 0 && (
        <Card title={`Recommendations — ${6 - team.length} slot${6 - team.length !== 1 ? 's' : ''} remaining`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2">#</th>
                <th className="text-left py-2">Pokémon</th>
                <th className="text-right py-2">Score</th>
                <th className="text-right py-2">Synergy</th>
                <th className="text-right py-2">Threat</th>
                <th className="text-right py-2">Usage</th>
                <th className="text-right py-2">Diversity</th>
                <th className="py-2"></th>
              </tr>
            </thead>
            <tbody>
              {recs.map((r, i) => (
                <tr key={r.pokemon} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 text-gray-500">{i + 1}</td>
                  <td className="py-2 font-medium">{r.pokemon}</td>
                  <td className="py-2 text-right text-blue-400 font-bold">{r.composite}</td>
                  <td className="py-2 text-right text-gray-300">{r.synergy}</td>
                  <td className="py-2 text-right text-gray-300">{r.threat_improvement}</td>
                  <td className="py-2 text-right text-gray-300">{r.usage}</td>
                  <td className="py-2 text-right text-gray-300">{r.diversity}</td>
                  <td className="py-2 text-right">
                    <button
                      onClick={() => { setTeam([...team, r.pokemon]); setReport(null); setRecs([]) }}
                      disabled={team.length >= 6}
                      className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-30 rounded transition-colors"
                    >
                      Add
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}