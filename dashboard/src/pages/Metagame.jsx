import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { getUsage, getPairs, getTriplets, getTera } from '../api'

const TYPE_COLORS = {
  Fire:'#F08030',Water:'#6890F0',Grass:'#78C850',Electric:'#F8D030',
  Ice:'#98D8D8',Fighting:'#C03028',Poison:'#A040A0',Ground:'#E0C068',
  Flying:'#A890F0',Psychic:'#F85888',Bug:'#A8B820',Rock:'#B8A038',
  Ghost:'#705898',Dragon:'#7038F8',Dark:'#705848',Steel:'#B8B8D0',
  Fairy:'#EE99AC',Normal:'#A8A878',
}

function Card({ title, children }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h2>
      {children}
    </div>
  )
}

function TypeBadge({ type }) {
  return (
    <span className="px-2 py-0.5 rounded text-xs font-bold text-white"
      style={{ backgroundColor: TYPE_COLORS[type] || '#666' }}>
      {type}
    </span>
  )
}

export default function Metagame() {
  const [usage, setUsage] = useState([])
  const [pairs, setPairs] = useState([])
  const [triplets, setTriplets] = useState([])
  const [tera, setTera] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getUsage(20), getPairs(15, 10), getTriplets(10), getTera(12)])
      .then(([u, p, t, tr]) => {
        setUsage(u.data)
        setPairs(p.data)
        setTriplets(t.data)
        setTera(tr.data)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-500 py-20 text-center">Loading metagame data...</div>

  return (
    <div className="space-y-6">
      {/* Usage chart */}
      <Card title="Pokémon Usage % — Top 20">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={usage} layout="vertical" margin={{ left: 100, right: 20 }}>
            <XAxis type="number" domain={[0, 'auto']} tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <YAxis type="category" dataKey="name" tick={{ fill: '#e5e7eb', fontSize: 12 }} width={100} />
            <Tooltip
              contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
              formatter={(v, n) => [
                n === 'usage_pct' ? `${v}%` : `${v}%`,
                n === 'usage_pct' ? 'Usage' : 'Win Rate'
              ]}
            />
            <Bar dataKey="usage_pct" fill="#ef4444" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* Usage table with win rates */}
      <Card title="Usage & Win Rates">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2 pr-4">#</th>
                <th className="text-left py-2 pr-4">Pokémon</th>
                <th className="text-right py-2 pr-4">Usage %</th>
                <th className="text-right py-2 pr-4">Win Rate %</th>
                <th className="text-right py-2">Appearances</th>
              </tr>
            </thead>
            <tbody>
              {usage.map((p, i) => (
                <tr key={p.name} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 pr-4 text-gray-500">{i + 1}</td>
                  <td className="py-2 pr-4 font-medium">{p.name}</td>
                  <td className="py-2 pr-4 text-right text-blue-400">{p.usage_pct}%</td>
                  <td className="py-2 pr-4 text-right">
                    <span className={p.win_rate >= 55 ? 'text-green-400' : p.win_rate <= 45 ? 'text-red-400' : 'text-gray-300'}>
                      {p.win_rate}%
                    </span>
                  </td>
                  <td className="py-2 text-right text-gray-500">{p.appearances}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top pairs */}
        <Card title="Top Co-occurring Pairs">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2">Pair</th>
                <th className="text-right py-2 pr-2">Count</th>
                <th className="text-right py-2">Win %</th>
              </tr>
            </thead>
            <tbody>
              {pairs.map((p, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 text-xs">
                    <span className="text-gray-200">{p.pokemon_a}</span>
                    <span className="text-gray-500 mx-1">+</span>
                    <span className="text-gray-200">{p.pokemon_b}</span>
                  </td>
                  <td className="py-2 pr-2 text-right text-gray-400">{p.co_occurrence_count}</td>
                  <td className="py-2 text-right">
                    <span className={p.pair_win_rate >= 60 ? 'text-green-400' : p.pair_win_rate <= 45 ? 'text-red-400' : 'text-gray-300'}>
                      {p.pair_win_rate}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* Tera rates */}
        <Card title="Terastallization Rates — Top 12">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={tera} layout="vertical" margin={{ left: 110, right: 20 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }}
                tickFormatter={v => `${v}%`} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#e5e7eb', fontSize: 12 }} width={110} />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                formatter={v => [`${v}%`, 'Tera Rate']}
              />
              <Bar dataKey="tera_rate" fill="#a855f7" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Triplet cores */}
      {triplets.length > 0 && (
        <Card title="Top Triplet Cores">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2">Core</th>
                <th className="text-right py-2 pr-2">Appearances</th>
                <th className="text-right py-2">Win %</th>
              </tr>
            </thead>
            <tbody>
              {triplets.map((t, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 text-xs">
                    {t.pokemon_a} <span className="text-gray-500">+</span> {t.pokemon_b} <span className="text-gray-500">+</span> {t.pokemon_c}
                  </td>
                  <td className="py-2 pr-2 text-right text-gray-400">{t.co_occurrence_count}</td>
                  <td className="py-2 text-right">
                    <span className={t.pair_win_rate >= 60 ? 'text-green-400' : 'text-gray-300'}>
                      {t.pair_win_rate}%
                    </span>
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