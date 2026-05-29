const { Dex } = require('@pkmn/dex');
const fs = require('fs');
const path = require('path');

// Pokedex — unchanged
const pokedex = {};
for (const species of Dex.species.all()) {
    pokedex[species.name] = {
        types: species.types,
        baseStats: species.baseStats,
        abilities: Object.values(species.abilities),
    };
}
fs.writeFileSync(path.join(__dirname, 'pokedex.json'), JSON.stringify(pokedex, null, 2));
console.log('Wrote pokedex.json');

// Typechart — read damageTaken directly and convert to multipliers
const DAMAGE_TAKEN_MAP = { 0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0 };
const allTypes = Dex.types.all().map(t => t.name);
const typechart = {};

for (const defending of allTypes) {
    const typeData = Dex.types.get(defending);
    typechart[defending] = {};
    for (const attacking of allTypes) {
        const encoded = typeData.damageTaken?.[attacking] ?? 0;
        typechart[defending][attacking] = DAMAGE_TAKEN_MAP[encoded];
    }
}

fs.writeFileSync(path.join(__dirname, 'typechart.json'), JSON.stringify(typechart, null, 2));
console.log('Wrote typechart.json');

// OU Pool — all species legal in Gen 9 OU or below (excluding Ubers/AG)
const EXCLUDED_TIERS = new Set(['Uber', 'AG', 'Illegal', 'CAP', 'CAP NFE', 'CAP LC']);
const ouPool = [];
for (const species of Dex.species.all()) {
    if (EXCLUDED_TIERS.has(species.tier) || species.tier === '') continue;
    // Skip NFEs (not fully evolved)
    if (species.nfe) continue;
    // Skip forme aliases that aren't real battle formes
    if (species.battleOnly) continue;
    ouPool.push(species.name);
}
fs.writeFileSync(path.join(__dirname, 'ou_pool.json'), JSON.stringify(ouPool, null, 2));
console.log(`Wrote ou_pool.json — ${ouPool.length} species`);