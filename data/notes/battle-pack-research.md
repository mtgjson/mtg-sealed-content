# Booster Battle Pack pack research

The M12 and M13 Battle Packs are not ordinary fixed decklists. Contemporary
opening/review evidence describes each 20-card deck as two ten-card colour
packs: five set cards plus five basic lands for each colour. The product
randomizes which pack combinations are packed, while the cards within a
pack are fixed.

## M12

Ertai's Lament's 2011 review describes two ten-card packs per deck and says
that each pack contains five cards of one colour and five corresponding
basics: <https://ertaislament.com/2011/09/18/booster-battle-pack-review-part-1-of-2/>.
The contemporary MTG Salvation report independently describes four ten-card
packs in a Battle Pack, one for each of four colours, and lists the observed
five-card spell packs: <https://static.mtgsalvation.com/forums/magic-fundamentals/magic-general/326668-two-player-booster-battle-pack>.

The later reconstruction at Quiet Speculation gives two fixed five-spell
variants for every colour (ten spell packs total), with five basics added to
each pack: <https://www.quietspeculation.com/2012/02/presenting-the-innistrad-booster-battle-packs/>.
The recovered M12 spell packs are:

- White A: Armored Warhorse, Divine Favor, Pride Guardian, Siege Mastodon, Serra Angel; White B: Angel's Mercy, Griffin Rider, Griffin Sentinel, Peregrine Griffin, Roc Egg.
- Blue A: Aether Adept, Amphin Cutthroat, Coral Merfolk, Jace's Erasure, Belltower Sphinx; Blue B: Cancel, Chasm Drake, Frost Breath, Skywinder Drake, Azure Mage.
- Black A: Disentomb, Mind Rot, Sorin's Thirst, Zombie Goliath, Sengir Vampire; Black B: Bloodrage Vampire, Duskhunter Bat, Taste of Blood, Tormented Soul, Vampire Outcasts.
- Red A: Chandra's Outrage, Fiery Hellhound, Firebreathing, Goblin Tunneler, Volcanic Dragon; Red B: Blood Ogre, Goblin Fireslinger, Lava Axe, Shock, Stormblood Berserker.
- Green A: Garruk's Companion, Gladecover Scout, Plummet, Stampeding Rhino, Overrun; Green B: Giant Spider, Greater Basilisk, Sacred Wolf, Trollhide, Lure.

The sealed product selects four distinct color groups with `variable_mode`
(`count: 4`, `replacement: false`). Each color group independently chooses
its canonical A or B ten-card pack. This yields eighty equally weighted
modeled outcomes and preserves the documented four-color rule. Two ordinary
fifteen-card M12 boosters bring the product to seventy cards. Exact production
frequencies remain estimates. The twelve-pack display is unchanged.

## M13

The [contemporary owner report and scans](https://mtgadventures.blogspot.com/2012/08/m13-battle-packs.html)
show two twenty-card decks per box, each comprising two ten-card color packs.
Every pack contains five fixed spells and five matching basic lands. The
first two decks are black/red and black/green: colors can repeat between the
two decks in a box. Later openings show black/green, white/red and white/blue.

The additional recovered packs are:

| Pack | Five spells | Scan |
| --- | --- | --- |
| White B | Warclamp Mastiff; Divine Favor; Guardians of Akrasa; Aven Squire; Serra Angel | battle-pack-4-enclosed.jpg |
| Blue B | Unsummon; Downpour; Vedalken Entrancer; Scroll Thief; Jace's Phantasm | battle-pack-4-enclosed.jpg |
| Black B | Tormented Soul; Dark Favor; Crippling Blight; Servant of Nefarox; Duskmantle Prowler | inner-pack-2-2.jpg and inner-pack-2-3-2.jpg |
| Red B | Kindled Fury; Wall of Fire; Canyon Minotaur; Searing Spear; Furnace Whelp | inner-pack-1-2.jpg |
| Green B | Fog; Bond Beetle; Vastwood Gorger; Centaur Courser; Garruk's Packleader | inner-pack-2-2.jpg and inner-pack-2-3-1.jpg |

The original packs use the A suffix, with B distinguishing the newly recovered
variants, matching the M12 naming convention. The scans also corroborate the existing black, red and white packs.
The existing blue and green pack lists are retained, but this source does not
independently corroborate them. The M12 review is not evidence for M13 lists.

The sealed product contains two independent twenty-card deck selections.
Each selects two distinct color groups, and each selected color independently
chooses its canonical A or B ten-card pack. The outer `variable_mode` repeats
this deck component twice with replacement; the inner mode selects two colors
without replacement. The exporter preserves independent choice groups rather
than concatenating their alternatives. No whole-box combinations or YAML
aliases are written into the source.

There are forty modeled outcomes per deck and 1,600 ordered outcomes per box.
Colors and complete packs can repeat between decks, but each deck has two
different colors. Two ordinary M13 boosters bring the total to seventy cards.
Equal choice weights and the completeness of the ten-pack inventory remain
estimates. Basic-land artwork follows the canonical wildcard convention.
No Battle Pack booster definition or importer exclusion is needed.
