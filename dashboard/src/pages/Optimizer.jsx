import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { getOptimizerBest, getOptimizerResults } from '../api'

function Card({ title, children }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      {title && <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h2>}
      {children}
    </div>
  )
}

export default function Optimizer() {
  const [best, setBest] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getOptimizerBest(10), getOptimizerResults()])
      .then(([b, r]) => {
        setBest(b.data)
        const gens = r.data?.generations || []
        setHistory(gens.map((g, i) => ({
          generation: i + 1,
          best: g.best_score ?? g.teams?.[0]?.fitness ?? 0,
          avg: g.avg_score ?? (g.teams?.reduce((s, t) => s + (t.fitness || 0), 0) / (g.teams?.length || 1)),
        })))
      })
      .catch(e => setError(e.response?.data?.detail || 'No optimizer results found. Run Phase 5 first.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-500 py-20 text-center">Loading optimizer results...</div>
  if (error) return <div className="text-yellow-400 py-20 text-center">{error}</div>

  return (
    <div className="space-y-6">
      {history.length > 0 && (
        <Card title="Score Progression Over Generations">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="generation" tick={{ fill: '#9ca3af', fontSize: 11 }} label={{ value: 'Generation', position: 'insideBottom', offset: -2, fill: '#6b7280' }} />
              <YAxis domain={[0, 'auto']} tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                formatter={v => [v?.toFixed ? v.toFixed(4) : v]} />
              <Line type="monotone" dataKey="best" stroke="#ef4444" strokeWidth={2} dot={false} name="Best" />
              <Line type="monotone" dataKey="avg" stroke="#3b82f6" strokeWidth={2} dot={false} name="Avg" strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 text-xs text-gray-500 justify-end">
            <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-red-500 inline-block"></span> Best</span>
            <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-blue-500 inline-block"></span> Avg</span>
          </div>
        </Card>
      )}

      <Card title="Top Optimized Teams">
        <div className="space-y-4">
          {best.map((entry, i) => (
            <div key={i} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 text-sm font-mono">#{i + 1}</span>
                  <span className="text-blue-400 font-bold text-lg">{entry.fitness?.toFixed(4)}</span>
                  <span className="text-gray-500 text-xs">fitness score</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 mb-3">
                {(entry.team || []).map(p => (
                  <span key={p} className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1 text-sm font-medium">
                    {p}
                  </span>
                ))}
              </div>
              {entry.scores && (
                <div className="grid grid-cols-3 gap-2 text-xs text-gray-400">
                  {Object.entries(entry.scores).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="capitalize">{k.replace(/_/g, ' ')}</span>
                      <span className="text-gray-300">{typeof v === 'number' ? v.toFixed(3) : v}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {best.length === 0 && <p className="text-gray-500 text-sm">No teams found.</p>}
        </div>
      </Card>
    </div>
  )
}