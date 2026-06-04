import { useState } from 'react'
import Metagame from './pages/Metagame'
import TeamBuilder from './pages/TeamBuilder'
import Optimizer from './pages/Optimizer'

const TABS = ['Metagame', 'Team Builder', 'Optimizer']

export default function App() {
  const [tab, setTab] = useState('Metagame')

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center gap-8">
        <h1 className="text-xl font-bold text-red-400 tracking-wide">PokéMeta</h1>
        <nav className="flex gap-1">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                tab === t
                  ? 'bg-red-500 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>
      <main className="p-6">
        {tab === 'Metagame' && <Metagame />}
        {tab === 'Team Builder' && <TeamBuilder />}
        {tab === 'Optimizer' && <Optimizer />}
      </main>
    </div>
  )
}