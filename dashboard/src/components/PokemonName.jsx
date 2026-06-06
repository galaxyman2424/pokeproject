const spriteUrl = (name) =>
  `https://play.pokemonshowdown.com/sprites/dex/${name.toLowerCase().replace(/ /g, '')}.png`

export default function PokemonName({ name, onClick }) {
  return (
    <span
      className={`inline-flex items-center gap-2 ${onClick ? 'cursor-pointer hover:text-blue-400 transition-colors' : ''}`}
      onClick={() => onClick?.(name)}
    >
      <img
        src={spriteUrl(name)}
        alt={name}
        className="w-8 h-8 object-contain"
        onError={e => {
            if (e.target.src.includes('/dex/')) {
                e.target.src = e.target.src.replace('/dex/', '/gen5/')
            } else {
                e.target.style.display = 'none'
            }
        }}
      />
      <span>{name}</span>
    </span>
  )
}