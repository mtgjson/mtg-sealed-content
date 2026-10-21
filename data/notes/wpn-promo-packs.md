# Seasonal WPN Promo Packs

For new seasons or repeat coverage audits, follow the [Promo Pack creation skill](../../.agents/skills/mtg-promo-pack-audit/SKILL.md).

## Coverage and scope

All 28 documented seasons from Core Set 2020 through Reality Fracture have separate
regular and traditional-foil products, referencing `promo` and `promo-foil` in
magic-search-engine. Against the current card index, these 56 boosters cover all
2,742 physical `promo:promopack` printings and all 5,409 supported printing/finish
pairs. No exceptions or catch-all orphan sheet are used. This is a membership
coverage result, not proof of exact factory collation or every repeated appearance.

The booster definitions must be published before downstream MTGJSON builds can
resolve the new sealed references. No provider identifiers have been invented.

## Sources and modeled pools

The source column links the complete Wizards list used for each season. Counts in
the last column are distinct possible physical gameplay cards, not pack size.
Adventure, split and Room cards count once. The curated count is the extracted
published list, except Kaldheim's independently corroborated Cinder Glade addition.

| Season | Source | Curated cards | Possible cards (regular / foil) |
| --- | --- | ---: | ---: |
| M20 | [Wizards](https://media.wizards.com/2019/downloads/promo_packs/M20_Promo_Pack_08162019.pdf) | 121 | 235 / 235 |
| ELD | [Wizards](https://media.wizards.com/2019/downloads/promo_packs/ELD_Promo_Pack_10022019.pdf) | 121 | 194 / 194 |
| THB | [Wizards](https://media.wizards.com/2020/downloads/promo_packs/THB_Promo_Pack_01202020.pdf) | 121 | 194 / 194 |
| IKO | [Wizards](https://media.wizards.com/2020/downloads/promo_packs/IKO_Promo_Pack_04172020.pdf) | 121 | 194 / 194 |
| M21 | [Wizards](https://media.wizards.com/2020/downloads/promo_packs/M21_Promo_Pack_06202020.pdf) | 121 | 194 / 194 |
| ZNR | [Wizards](https://media.wizards.com/2020/downloads/promo_packs/ZNR_Promo_Pack_09252020.pdf) | 121 | 194 / 194 |
| KHM | [Wizards](https://media.wizards.com/2021/downloads/promo_packs/KHM_Promo_Pack_02052020.pdf) | 121 | 194 / 194 |
| STX | [Wizards](https://media.wizards.com/2021/downloads/promo_packs/STX_Promo_Pack_042221.pdf) | 120 | 193 / 193 |
| AFR | [Wizards](https://media.wizards.com/2021/downloads/promo_packs/AFR_Promo_Pack_07122021.pdf) | 114 | 187 / 187 |
| MID | [Wizards](https://media.wizards.com/2021/downloads/promo_packs/MID_Promo_Pack_09162021-2.pdf) | 121 | 194 / 194 |
| NEO | [Wizards](https://media.wizards.com/2022/downloads/promo_packs/NEO_Promo_Pack_02092022.pdf) | 121 | 194 / 194 |
| SNC | [Wizards](https://media.wizards.com/2022/downloads/promo_packs/SNC_Promo_Pack_04152022.pdf) | 121 per finish | 186 / 186 |
| DMU | [Wizards](https://media.wizards.com/2022/downloads/promo_packs/DMU_Promo_Pack_08292022.pdf) | 121 | 186 / 186 |
| BRO | [Wizards](https://media.wizards.com/2022/downloads/promo_packs/BRO_Promo_Pack_11042022.pdf) | 121 | 186 / 186 |
| ONE | [Wizards](https://media.wizards.com/2023/downloads/promo_packs/ONE_Promo_Pack_01272023.pdf) | 121 | 186 / 186 |
| MOM | [Wizards](https://media.wizards.com/2023/downloads/promo_packs/MOM_Promo_Pack_04122023.pdf) | 113 | 158 / 158 |
| WOE | [Wizards](https://media.wizards.com/2023/downloads/promo_packs/WOE_Promo_Pack_08292023.pdf) | 121 | 186 / 186 |
| LCI | [Wizards](https://media.wizards.com/2023/downloads/promo_packs/LCI_Promo_Pack_11062023.pdf) | 121 | 194 / 194 |
| MKM | [Wizards](https://media.wizards.com/2024/downloads/promo_packs/MKM_Promo_Pack_02092024.pdf) | 111 | 176 / 176 |
| OTJ | [Wizards](https://media.wizards.com/2024/downloads/promo_packs/OTJ_Promo_Pack_04162024.pdf) | 121 | 186 / 186 |
| BLB | [Wizards](https://media.wizards.com/2024/downloads/promo_packs/BLB_Promo_Pack_07262024.pdf) | 121 | 186 / 186 |
| DSK | [Wizards](https://media.wizards.com/2024/downloads/promo_packs/DSK_Promo_Pack_09182024.pdf) | 121 | 186 / 186 |
| DFT | [Wizards](https://media.wizards.com/2025/downloads/promo_packs/DFT_Promo_Pack_02062025.pdf) | 121 | 186 / 186 |
| TDM | [Wizards](https://media.wizards.com/2025/downloads/promo_packs/TDM_Promo_Pack_04042025.pdf) | 121 | 186 / 186 |
| EOE | [Wizards](https://media.wizards.com/2025/downloads/promo_packs/EOE_Promo_Pack_07182025.pdf) | 121 | 186 / 186 |
| ECL | [Wizards](https://media.wizards.com/2026/downloads/promo_packs/ECL_Promo_Pack_01162026.pdf) | 121 | 186 / 186 |
| SOS | [Wizards](https://magic.wizards.com/en/products/card-set-archive) | 121 | 186 / 186 |
| FRA | [Wizards](https://magic.wizards.com/en/products/card-set-archive) | 121 | 186 / 186 |

## Slot and finish rules

- **M20:** four gameplay cards: a stamped M20 rare/mythic, a curated stamped card,
  a PPP1 stamped basic land, and one of five PM20 dark-frame promos. The curated
  card is replaced by a Japanese alternate-art WAR planeswalker in 25% of packs;
  all 36 are eligible in either finish. The compiled union has 235 physical cards,
  despite the launch article's 236-card marketing total. Do not invent a 236th
  printing. [WPN finish/replacement rules](https://wpn.wizards.com/en/news/everything-there-know-about-new-promo-packs).
- **ELD through DSK:** three gameplay cards plus an Arena code where available.
  The code is an accessory, excluded from `card_count`. DFT and later sources list
  only three gameplay slots, so no Arena code is assumed for them.
- **ZNR, KHM, STX, MID, NEO, DMU, BRO, MOM:** the seasonal slot excludes DFCs
  where specified. STX additionally excludes Lessons from that slot; its six
  rare/mythic Lessons occur in the curated list instead.
- **AFR, MOM, MKM:** seasonal cards assigned to the curated slot are excluded from
  the first slot according to each source's separation language. MKM's curated
  list includes its ten surveil lands. Other seasons retain source-described
  overlap rather than assuming every slot must be disjoint.
- **ONE, OTJ, BLB, DSK, DFT, TDM, EOE, ECL, SOS:** the first slot is rare-only;
  the set's mythics appear in the curated slot. FRA explicitly says rare or mythic
  in its first slot, so its model follows that wording.
- **SNC:** each curated sheet has 121 cards: 46 shared plus 75 unique to that
  finish. The foil-only group is the 75 PNCC stamped Commander printings. None
  appears in a nonfoil booster.
- **Purple Worm (PAFR 201p):** an uncommon explicitly included in TDM's curated
  list. It is not added to AFR's rare/mythic slot. A printing's set symbol does
  not establish the season in which its stamped version was distributed.

VOW and DBL reused MID packs
([WPN](https://wpn.wizards.com/en/news/look-inside-your-innistrad-crimson-vow-and-innistrad-double-feature-marketing-kit)).
FDN reused DSK packs until DFT
([WPN](https://wpn.wizards.com/en/news/magic-the-gathering-foundations-events-and-promos-overview)).
These are not extra seasonal pack definitions. Standard Showdown packs are a
separate earlier product family.

## Printing decisions and source limitations

The PDF lists generally give card names rather than set/collector numbers. The
models select the stamped printing, using the surrounding set groups to resolve
reprints. In particular, early curated Fabled Passage entries use PELD 244p,
M21-group Heroic Intervention and Temples use their PM21 printings, and later
Terror of the Peaks entries use POTJ 149p. MID's Heroic Intervention is PAER 109p,
consistent with its older-card group and a
[contemporaneous list identifying AER](https://note.com/kk_yp_107/n/nd18bf1177b27).
SNC and DMU use the regular PM21 Heroic Intervention printing; that set choice is
an inference where their name-only lists do not explicitly distinguish AER/M21.

**Kaldheim Cinder Glade:** Wizards' PDF lists only 120 curated names and omits it.
Both [TCGplayer's Kaldheim catalog](https://www.tcgplayer.com/categories/trading-and-collectible-card-games/magic-the-gathering/price-guides/promo-pack-kaldheim)
and [Cardsphere's Kaldheim checklist](https://www.cardsphere.com/sets/1304) identify
Cinder Glade 235/235p as a Kaldheim Promo Pack card in both finishes. Add PBFZ 235p
to KHM's curated list, bringing it to 121. This closes the last unmapped printing;
it is a catalog-backed correction, not an assumption from the land cycle alone.

**Showcase Reckoner Bankbuster:** PNEO 404p is cataloged under Brothers' War Promo
Packs ([TCGplayer](https://www.tcgplayer.com/search/magic/product?productName=Reckoner+Bankbuster+%28Showcase%29),
[EchoMTG](https://beta.echomtg.com/mtg/sets/pbro/promo-pack-the-brothers-war/)).
BRO's curated slot uses 404p, while NEO's seasonal slot excludes it and uses 255p.
Later name-only curated lists use regular 255p; an appearance of 404p in those
later seasons would warrant a targeted amendment rather than adding it everywhere.

**Copy errors and incomplete wording:** THB and MOM have wrong set names in
some slot prose; the named dark-frame cards determine the intended set. ECL's
foil paragraph says Tarkir. KHM/STX names contain typos, and LCI's PDF text has
broken ligatures; these are normalized to the named cards. STX has 120 names,
AFR 114, MOM 113, and MKM 111; the models do not pad those lists to 121.

**DMU/BRO/ONE foil disclaimer:** DMU repeats SNC's foil paragraph verbatim,
including SNC's name. BRO and ONE retain the claim that the curated foil list
is different, but publish only one list and no alternative membership. The models
use the sole published list in both finishes. This is an explicit working
interpretation of an inconsistent source, not a confirmed independent foil-list
comparison. SNC's genuinely separate lists are preserved exactly. A corrected
Wizards list or printing-specific opening evidence should supersede this decision.

## Probabilities and validation

Seasonal rare/mythic sheets use the existing estimated 2:1 per-card convention.
Curated sheets, dark-frame cards, M20 basic lands and Japanese planeswalkers use
estimated equal per-card weights. Only M20's 25% replacement rate is documented;
coverage does not establish actual relative pull rates.

All 56 definitions were freshly preprocessed and compiled against the card
index. Every possible card resolved through the production MTGJSON UUID exporter;
100 generated packs per definition had the expected size and finish. Every
candidate finish was checked against the actual printing. Additional assertions
check SNC's 75 foil-only cards, KHM Cinder Glade, and the NEO/BRO Bankbuster split.
The exact set/collector-number/finish union leaves zero `promo:promopack` orphans.
The sealed repository's structural validator and 87 tests pass; pre-existing
category/subtype warnings are unrelated to these products.
