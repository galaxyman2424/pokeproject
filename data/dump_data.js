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

// Sanity checks
console.log('\nSanity checks:');
console.log('Fire -> Steel (expect 0.5):', typechart['Steel']['Fire']);
console.log('Water -> Fire (expect 2.0):', typechart['Fire']['Water']);
console.log('Normal -> Ghost (expect 0.0):', typechart['Ghost']['Normal']);
console.log('Electric -> Ground (expect 0.0):', typechart['Ground']['Electric']);
console.log('Ice -> Dragon (expect 2.0):', typechart['Dragon']['Ice']);
console.log('Fighting -> Bug (expect 0.5):', typechart['Bug']['Fighting']);