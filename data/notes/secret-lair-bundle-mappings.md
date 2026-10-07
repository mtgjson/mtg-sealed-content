# Secret Lair bundle mapping recovery

Audit date: 2026-10-08. Starting points: `status.txt` and `data/review.yaml`.

## Confirmed contents

| Family | Bundle | Included drop editions |
| --- | --- | ---: |
| 2019 launch | The Full Bundle | 7 |
| Secretversary 2020 | Foils Forever / No Foils, No Nonsense / The Bundle Bundle | 4 / 4 / 8 |
| Smitten 2021 | All-Our-Love | 9 |
| Out of Time 2021 | World's Non-foil-est / World's Bundliest | 5 / 9 |
| Winter 2023 | Prophets Predicted nonfoil / foil / Everything | 6 / 7 / 13 |
| Spring 2023 | Those Non-Foils / Those Foils / It's Raining | 5 / 8 / 13 |

Seven products were absent from the catalog and four had no contents. The two existing 2023 combined bundles already referenced the empty products; completing those children also restores their traversal. Out of Time's existing four-drop foil bundle was checked and retained. Fourteen provider review rows identify the seven older products and are moved into their definitions, not ignored.

Each bundle references the existing sealed drops. This preserves their edition-specific decks, tokens, fixed bonuses and variable bonus pools without duplicating card definitions. There are 59 distinct child drop editions across the recovered bundle families. Completing bundle membership does not independently validate every historical bonus probability.

## Sources and edition details

- [2019 official recap](https://magic.wizards.com/en/news/announcements/secret-lair-recap-2019-11-25): seven named drops; sale opens December 2, 2019. Several drops are foil-only despite not having `Foil` in the catalog name. The bundle follows those original product identities.
- [Secretversary announcement](https://magic.wizards.com/en/news/announcements/announcing-secret-lairs-secretversary-superdrop-2020-11-25): three bundles. The foil half includes We Hope You Like Squirrels; the nonfoil half instead includes Party Hard, Shred Harder. [Cardmarket's Secretversary product](https://www.cardmarket.com/en/Magic/Products/Other-Boxes/Secret-Lair-Drop-Series-Secretversary-Superdrop) explicitly lists both halves, resolving the catalog's shortened name to The Bundle Bundle.
- [Smitten announcement](https://magic.wizards.com/en/news/announcements/announcing-secret-lairs-smitten-superdrop-2021-02-10): nine editions, including foil-only Faerie, Faerie, Faerie Rad. The ordinary Valentine's products are referenced; separately shipped replacement Heliod packs are not added to the original sealed bundle.
- [Out of Time announcement](https://magic.wizards.com/en/news/announcements/good-times-secret-lairs-out-time-superdrop-2021-08-24): five nonfoil editions and four foil editions. Teferi's Time Trouble is nonfoil-only. The combined bundle references both halves.
- Winter 2023 official [nonfoil](https://secretlair.wizards.com/us/en/product/811124/the-prophets-predicted-non-foils-bundle), [foil](https://secretlair.wizards.com/us/en/product/811121/the-prophets-predicted-foils-bundle) and [combined](https://secretlair.wizards.com/us/en/product/811118/the-prophets-predicted-everything-bundle) lists: the seventh foil drop is Showcase: All Will Be One Step-and-Compleat Edition, not a traditional-foil substitute.
- Spring 2023 official [nonfoil](https://secretlair.wizards.com/us/en/product/814011/those-non-foils-just-won-t-let-up-bundle), [foil](https://secretlair.wizards.com/us/en/product/814006/those-foils-are-really-coming-down-bundle) and [combined](https://secretlair.wizards.com/us/en/product/814002/it-s-raining-foils-and-non-foils-bundle) lists: the foil bundle includes all three Halo Foil March of the Machine volumes. The nonfoil bundle includes none of them.

## Metadata and remaining scope

The 2019 launch bundle uses its explicitly announced December 2 sale date, matching the sale-date convention of its existing launch drops. For the other six new definitions, exact physical release dates remain unset: the review queue mixes preorder dates with catalog dates, and dates on related drops do not by themselves prove bundle fulfillment dates. Existing 2023 dates are retained; the official Spring pages say shipping began May 1 in the US / May 2 in Europe, which does not resolve the repository's April 28 versus August 11 discrepancy without a separate date-convention review.

The Ultimate Pencil Superdrop review row remains unresolved and is not silently equated to another product. Non-SLD review entries are outside this batch. Status-report leads still requiring separate work include Helvault allocation, Multiverse Gift Box preview boosters, FRA land packs/prerelease, and newer HOB/MBC/TRK/TRC products. Prior exclusions for foreign editions, Eighth/Ninth Edition, Land Stations and ordinary Promo/Showdown packs remain in force.

## Verification

Fresh canonical deck export and the current search-engine UUID exporter agree on all 59 referenced decklists' card identities, collector numbers, quantities and foil flags (normalizing front-only adventure names for comparison). Across distinct child editions these export 263 base-card copies and nine tokens; every token has a usable UUID. All 29 distinct referenced bonus pools compile, and all 16 distinct direct bonus entries export successfully. These totals describe distinct child editions, not one physical bundle.

Recursive traversal verifies each advertised drop exactly once, including both existing 2023 combined bundles. Winter's combined bundle expands to 61 base cards and 13 bonus slots; Spring's to 55 and 13. The original launch bundle expands to 26 base cards, six tokens and seven bonus slots. All 14 removed review identifiers occur on exactly one new canonical product. Repository structural validation passes with existing unrelated category warnings.
