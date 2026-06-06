import { useEffect, useState, useRef } from 'react'
import { getPool } from '../api'

export default function PokemonSearch({ onAdd, team }) {
  const [pool, setPool] = useState([])
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    getPool().then(r => setPool(r.data))
  }, [])

  useEffect(() => {
    if (query.length < 2) { setSuggestions([]); return }
    const q = query.toLowerCase()
    setSuggestions(
      pool
        .filter(p => p.toLowerCase().includes(q) && !team.includes(p))
        .slice(0, 8)
    )
  }, [query, pool, team])

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const select = (name) => {
    onAdd(name)
    setQuery('')
    setSuggestions([])
    setOpen(false)
  }

  return (
    <div className="relative flex-1" ref={ref}>
      <input
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-red-500"
        placeholder="Search Pokémon (e.g. Great Tusk)"
        value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true) }}
        onKeyDown={e => { if (e.key === 'Enter' && suggestions.length > 0) select(suggestions[0]) }}
      />
      {open && suggestions.length > 0 && (
        <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg overflow-hidden shadow-xl">
          {suggestions.map(p => (
            <button
              key={p}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-700 transition-colors"
              onClick={() => select(p)}
            >
              {p}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}