const { Dex } = require('@pkmn/dex');
const fs = require('fs');
const path = require('path');

// Pokedex
const pokedex = {};
for (const species of Dex.species.all()) {
    pokedex[species.name] = {
        types: species.types,
        baseStats: species.baseStats,
        abilities: Object.values(species.abilities),
    };
}
fs.writeFileSync(path.join(__dirname, 'pokedex.json'), JSON.stringify(pokedex, null, 2));

// Typechart
const typechart = {};
for (const type of Dex.types.all()) {
    typechart[type.name] = {
        damageTaken: type.damageTaken,
    };
}
fs.writeFileSync(path.join(__dirname, 'typechart.json'), JSON.stringify(typechart, null, 2));

console.log('Done.');