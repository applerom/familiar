<!--
START_MODULE_CONTRACT: MOD-DEMO-CASE
PURPOSE: Show the memory-first start as a working file: every claim with what it stands on, the coverage of what was searched, and the one paper that would decide.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- every claim names its ground and weight, and a hearsay claim is never marked firm [review: engine lead]
- the case names its next test and the bridge paper [review: engine lead]
CHANGES_WITH:
- MOD-DEMO-VERSIONS (the question this case works on)
- MOD-DEMO-SEARCHES (coverage rows)
:END_MODULE_CONTRACT
-->
# Case: Rosa Calhau, where she came from

Invented for the Familiar demo. Start: memory-first. Question: `versions/rosa-birthplace.json`.

## Claims

| Claim | Stands on | Weight |
|---|---|---|
| Rosa Calhau is Helena's mother | doc-helena-baptism | firm |
| Rosa's birthplace begins with "Ponta d" | doc-helena-baptism, torn after the letter d | firm |
| Rosa came "from near Amaro's village" | m-rosa-came-to-marry | hearsay |
| Rosa was born about 1902 | m-rosa-came-to-marry | hearsay |
| Rosa died in Quarry Bend in 1981 | m-rosa-death | firm |
| Amaro was single in March 1921 | rec-santa-ludovina-1921-14 | firm |
| Manuel Tavares links the crossing and the baptism | rec-santa-ludovina-1921-14, doc-helena-baptism | probable |

## Coverage

| Search | Covered | Result |
|---|---|---|
| s-amaro-arrival | invented arrivals index, 1919-1926, 412 of 520 lists, three forms | found, line 14 |
| s-rosa-arrival | same index and years, six forms including the married name | not found; weak, the index misses a fifth of the lists |

## Bridge paper

Rosa's death certificate of 1981: a death record of the town names birthplace
and, often, parents. A living relative requests it; nobody alive is asked
where she was born, because nobody alive could have seen it.

## Next test

Request the death certificate. Until it comes, one bounded pass through the
baptisms of Ponta do Moinho for 1898-1906, with the coverage written down.

## What breaks the pattern

Rosa does not appear in an index that finds Amaro. Either she landed
elsewhere, or under her married name after a wedding on the island, or in a
list the index skipped. Each reading is a version-scene for the feed.
