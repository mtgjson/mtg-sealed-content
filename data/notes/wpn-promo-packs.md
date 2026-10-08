# Seasonal WPN Promo Packs

## 2019 implementation

Sources:
- [Core Set 2020 contents](https://media.wizards.com/2019/downloads/promo_packs/M20_Promo_Pack_08162019.pdf)
- [M20 finish and Japanese planeswalker rules](https://wpn.wizards.com/en/news/everything-there-know-about-new-promo-packs)
- [Throne of Eldraine contents](https://media.wizards.com/2019/downloads/promo_packs/ELD_Promo_Pack_10022019.pdf)

Both releases have separate regular and foil products, referencing `promo` and
`promo-foil` boosters in magic-search-engine. The foil variants use the same card
membership, entirely in traditional foil. These references require publication of
the corresponding booster definitions before downstream compilation can resolve them.

M20 has four gameplay cards: a stamped M20 rare/mythic, a curated stamped card
(replaced by a Japanese alternate-art WAR planeswalker in 25% of packs), a stamped
basic land from PPP1, and one of five dark-frame promos from PM20. The curated list
contains 121 cards. All 36 Japanese planeswalkers are eligible in either finish.
The compiled union contains 235 physical cards; do not use the launch article's
236-card marketing total as a reason to invent another printing.

Eldraine has three gameplay cards: a stamped ELD rare/mythic, one of 121 curated
stamped cards, and one of five dark-frame promos (ELD 393–397). The fourth physical
card is an Arena code where available; it is described as an accessory and excluded
from `card_count`. The compiled union contains 194 physical cards. Split and
Adventure cards count once, despite their separate faces in the search index.

The first rare/mythic slot uses the existing 2:1 per-card rarity convention.
Curated lists, dark-frame promos, M20 lands and the Japanese planeswalker sheet use
equal per-card weights as estimates. Only M20's 25% replacement rate is documented;
these estimates are not claims about the actual print sheets.

Validation: all four boosters compile; every possible card resolves through the
production card UUID exporter; sampled packs have the expected card counts and
finishes. No provider identifiers have been invented for these newly defined packs.

## Remaining source inventory

The [official archive](https://magic.wizards.com/en/products/card-set-archive)
exposes older PDF links through its year selector. Located sources still awaiting
full pool extraction and mapping:

- 2020: THB, IKO, M21, ZNR.
- 2021: KHM, STX, AFR, MID.
- 2022: NEO, SNC, DMU, BRO.
- 2023: ONE, MOM, WOE, LCI.
- 2024: MKM, OTJ, BLB, DSK.
- 2025: DFT, TDM, EOE.
- 2026: ECL (PDF), SOS and FRA (inline lists).

Do not assume one pool across finishes or all rares/mythics from each set. SNC has
separate shared, regular-only and foil-only lists. BRO and ONE claim different
foil pools but show only one curated list; that discrepancy needs investigation.

VOW and DBL reused MID packs ([WPN](https://wpn.wizards.com/en/news/look-inside-your-innistrad-crimson-vow-and-innistrad-double-feature-marketing-kit)).
FDN reused DSK packs until DFT ([WPN](https://wpn.wizards.com/en/news/magic-the-gathering-foundations-events-and-promos-overview)).
These are not additional seasonal pack definitions. Standard Showdown packs are a
separate earlier product family.
