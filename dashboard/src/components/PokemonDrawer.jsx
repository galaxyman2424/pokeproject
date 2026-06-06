import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { getMoves, getTera, getPokemon } from '../api'

const TYPE_COLORS = {
  Fire:'#F08030',Water:'#6890F0',Grass:'#78C850',Electric:'#F8D030',
  Ice:'#98D8D8',Fighting:'#C03028',Poison:'#A040A0',Ground:'#E0C068',
  Flying:'#A890F0',Psychic:'#F85888',Bug:'#A8B820',Rock:'#B8A038',
  Ghost:'#705898',Dragon:'#7038F8',Dark:'#705848',Steel:'#B8B8D0',
  Fairy:'#EE99AC',Normal:'#A8A878',
}

const spriteUrl = (name) =>
  `https://play.pokemonshowdown.com/sprites/dex/${name.toLowerCase().replace(/ /g, '')}.png`


function StatBar({ label, value, max = 255 }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400 w-8">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
        <div
          className="h-1.5 rounded-full bg-blue-500"
          style={{ width: `${Math.round((value / max) * 100)}%` }}
        />
      </div>
      <span className="text-gray-300 w-6 text-right">{value}</span>
    </div>
  )
}

export default function PokemonDrawer({ name, onClose }) {
  const [moves, setMoves] = useState([])
  const [tera, setTera] = useState([])
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!name) return
    setLoading(true)
    Promise.all([getMoves(name), getTera(name), getPokemon(name)])
      .then(([m, t, p]) => {
        setMoves(m.data.slice(0, 10))
        setTera(t.data)
        setInfo(p.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [name])

  if (!name) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-96 bg-gray-950 border-l border-gray-800 z-50 overflow-y-auto">
        <div className="p-6 space-y-6">

          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src={spriteUrl(name)}
                alt={name}
                className="w-14 h-14 object-contain"
                onError={e => {
                    if (e.target.src.includes('/dex/')) {
                        e.target.src = e.target.src.replace('/dex/', '/gen5/')
                    } else {
                        e.target.style.display = 'none'
                    }
                }}
              />
              <div>
                <h2 className="text-lg font-bold">{name}</h2>
                {info && (
                  <div className="flex gap-1 mt-1">
                    {info.types.map(t => (
                      <span
                        key={t}
                        className="px-2 py-0.5 rounded text-xs font-bold text-white"
                        style={{ backgroundColor: TYPE_COLORS[t] || '#666' }}
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-white text-xl leading-none"
            >
              ✕
            </button>
          </div>

          {loading && <p className="text-gray-500 text-sm">Loading...</p>}

          {/* Base stats */}
          {info && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Base Stats</h3>
              <div className="space-y-2">
                {Object.entries(info.base_stats).map(([stat, val]) => (
                  <StatBar key={stat} label={stat.toUpperCase()} value={val} />
                ))}
              </div>
              <div className="mt-2 text-xs text-gray-500">
                Abilities: {info.abilities.join(', ')}
              </div>
            </div>
          )}

          {/* Move usage */}
          {moves.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Move Usage</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={moves} layout="vertical" margin={{ left: 80, right: 20 }}>
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="move" tick={{ fill: '#e5e7eb', fontSize: 11 }} width={80} />
                  <Tooltip
                    contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                    formatter={v => [`${v}%`, 'Usage']}
                  />
                  <Bar dataKey="move_pct" fill="#ef4444" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Tera distribution */}
          {tera.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Tera Type Distribution</h3>
              <div className="space-y-2">
                {tera.map(t => (
                  <div key={t.tera_type} className="flex items-center gap-2">
                    <span
                      className="px-2 py-0.5 rounded text-xs font-bold text-white w-20 text-center"
                      style={{ backgroundColor: TYPE_COLORS[t.tera_type] || '#666' }}
                    >
                      {t.tera_type}
                    </span>
                    <div className="flex-1 bg-gray-800 rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-purple-500"
                        style={{ width: `${t.type_pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{t.type_pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </>
  )
}