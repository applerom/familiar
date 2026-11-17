<!--
START_MODULE_CONTRACT: MOD-REGION-BP-ANSWERS
PURPOSE: Answer the numbered region questions of engine skills for this region in a few lines each, pointing at the pack records that hold the detail, so that a skill stays free of region facts and a researcher gets the answer by question id.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- every question id the memory-first skill asks is answered here or declared a gap in pack.toml [review: pack keeper]
CHANGES_WITH:
- MOD-SKILL-MEMORY-FIRST (question ids and wording)
- MOD-REGION-BP-SOURCES
- MOD-REGION-BP-CUSTODY
:END_MODULE_CONTRACT
-->
# Region answers: Belarus and the Podlaskie borderland

One section per question id. Each line ends with its status and the records
it rests on. Read the section you were sent to, not the file.

## RP-1

Which fields did a birth, marriage and death certificate of this country carry in each decade?

- A birth certificate of the 1940s-1950s issued to the family names the child and both parents with patronymics; it need not give the parents' places of birth or ages. [reported] (custody: by-birth-certificate-1940s-1950s)
- The register entry kept by the registry carries more than the certificate; when places of birth are needed, ask for the entry, not a repeat certificate. [reported] (custody: by-birth-certificate-1940s-1950s; source: zags-by)
- Marriage and death certificates of the period: not seen; do not promise ages or places from them. [unverified] (custody: by-marriage-certificate-1940s-1950s)

## RP-2

Which cemetery indexes exist here, and how many entries does each hold against its catalogue?

- Spachyn indexes 956 520 names on 5 633 cemeteries of Belarus, about half of the cemeteries not digitised; two large Minsk cemeteries are covered by a few percent of their catalogues. A zero is not a denial. [verified 2026-11-12] (source: spachyn)
- Помним is a public burial base with search by name, years, place and cemetery; the number of graves is not on its start page (about 100 000 in one publication, tens of thousands in another); coverage by cemetery unknown. [reported] (source: pomnim)
- Burial books are kept by the cemetery administration; ask with the name and the year of death. [unverified] (source: spachyn)

## RP-3

Which indexes hold service, award, repression, memorial-book and address-book records for this place and these years, and how do they read a zero?

- 1941-1945 service and awards: Память народа (fuzzy names, ten rows per page, the site's own zero message). A zero for a woman or a non-combatant is the norm. [verified 2026-11-08] (source: pamyat-naroda)
- Also 1941-1945: ОБД Мемориал (needs a browser), Подвиг народа (captcha, the host passes it); paper files at ЦАМО, which takes one request per award with an identity document. [reported] (source: obd-memorial; source: podvig-naroda; source: tsamo)
- 1914-1918: Памяти героев Великой войны. [reported] (source: gwar)
- Polish army 1918-1939: the online search of the historical office, which stood behind an image captcha on 2026-11-12; files at the central archive by request. [reported] (source: caw-wbh)
- Repression: Открытый список for the Soviet side, the remembrance institute's index (over 316 000 records of people under Soviet occupation after 1939-09-17) for the Polish side. [reported] (source: openlist; source: ipn)
- Forced labour and displaced persons: Arolsen (both counters at zero is a zero), the occupation records of the Mogilev regional archive; the national archive has a request form on forced labour and a study of 2001, not a database; no open database of forced labourers for Minsk. [verified 2026-11-08] (source: arolsen; source: mogilev-regional-archive; source: narb)
- Losses under German occupation 1939-1945: the Straty base (over 5.5 million records); access terms not confirmed. [reported] (source: straty)
- Address books and newspapers of Minsk 1960-1980: the national library, not opened. [unverified] (source: nlb)

- Further reported repression and testimony routes have unknown year spans; check their collection coverage before interpreting a zero. Basis: source cards and their cited outside guide. [reported] (source: represii-by; source: yad-vashem; source: stsg-pows)

## RP-4

Where is a civil record of this year kept now, who may request it, and for how long is it closed?

- Belarus: in the registry office for 100 years from the day the record was made, then a state archive; the first copy stays in the office of the place, the second in the archives of the registry bodies of the regions and of Minsk. Archival records with a personal secret are closed for 75 years from creation. [verified 2026-11-12] (custody: by-civil-term; custody: by-personal-secret)
- Who may ask: a certificate with data from a record goes to the person, to parents for a child's birth, to relatives for a death, in exceptional cases to heirs, close relatives and the spouse; copies of records are not issued to citizens; the request goes to the office of residence or to the office or archive that keeps the record. [verified 2026-11-12] (custody: by-civil-term)
- Minsk: records of 1944-2013 are in the city's archives on paper only. [verified 2026-11-12] (custody: by-minsk-civil-fund)
- Minsk before 1944: the fund of 1918-1943 is said to be lost, earlier births only as restored records. [reported] (custody: by-minsk-before-1944)
- Personnel files of liquidated organisations: the territorial archive of the city or district; service and pay certificates are free. [verified 2026-11-12] (custody: by-liquidated-orgs)
- In the city that archive is the Minsk city archive. [reported] (source: minsk-city-archive)
- Poland: births 100 years and marriages and deaths 80 years in the registry office, counted from the end of the year of the record, then the state archive within 2 years; copies go to the person, the spouse, ascendants, descendants, siblings and those who show a legal interest. [verified 2026-11-12] (custody: pl-civil-term)

## RP-5

Where do rural parish and village-council records of this period sit, and which are open?

- Village councils: the regional (zonal) state archive; household registers are named in the archives law among documents kept 75 years before handover. [reported] (custody: by-village-councils; custody: by-household-books)
- Household registers: 75 years on temporary storage in the body that made them; the law does not say they are closed to a researcher. [verified 2026-11-12] (custody: by-household-books)
- Parish registers up to 1917: the national historical archive (request intake and reader access must be checked separately for Minsk and Grodno in source niab), microfilm catalogues on FamilySearch, second copies in Polish diocesan archives, older books in the Lithuanian historical archive. [reported] (custody: by-parish-before-1918; source: niab; source: familysearch; source: aab; source: eais)
- Interwar west (1919-1939): in the lands with the confessional system the clergy kept the metric books as civil records until the end of 1945. [verified 2026-11-12] (custody: pl-interwar-east)
- Interwar west: look for second copies in Polish archives. [unverified] (custody: pl-second-copies-east)
- Registers of the 1920s-1930s in the Soviet east: the archives of the registry offices and regional archives. [verified 2026-11-12] (custody: by-archives-by-period)


- A cover-only ePaveldas item can have its full book in EAIS: follow the holder's link or shelfmark and compare the actual file. The digitised-files list is a discovery route, not proof of access to each book. Basis: ex-ussr-kinship-research v1.46.0, references/seed-sources.md:285–286; outside observations of 2026-11-14, not rechecked by Familiar. [reported] (source: eais; source: epaveldas)
- metrikai.lt may lead from a volunteer entry to an LVIA shelfmark, leaf, act number and ePaveldas image. Establish the parish and years first; the index and its source image are one evidence lineage. Coverage of Belarusian parishes is unknown. Basis: the same guide, references/seed-sources.md:287; PR #267, reported 2026-11-14. [reported] (source: metrikai-lt; source: eais; source: epaveldas)

## RP-65

Which events moved where people took their sacraments and papers, and where are those papers today?

- After 1832: suppressions at Świsłocz, Klimówka, Łopienica and Koniuchy in 1832 reduced the Catholic network. The Grodno Dominican monastery closed in 1833, its school church only in 1863. Do not equate a dissolved order with a closed parish. Basis: forum transcription of the 1912 diocesan history, not the printed original; chronology: church-suppressions-1832. [reported] (source: wilno-churches-1910)
- After 1863: Wielka Brzostowica closed in 1864 and became Orthodox; Zelwa closed and was handed to the Orthodox in 1866; Łysków and Łukonica closed in 1866. Dereczyn is dated 1867-1869 in the transcription, even though its Catholic index ends in 1866. Basis: the same secondary list; chronology: church-suppressions-1863. [reported] (source: wilno-churches-1910; source: geneteka)
- Receiving parishes: the list places the later Mała Brzostowica chapel in Krynki parish and attaches the Łukonica cemetery chapel to Słonim. Its Różana chapels Szejpiaki and Połońsk closed in 1861 and 1866. Check diocesan directories for the specific year; a nearby chapel may itself have closed. Basis: the forum transcription, not an administrative decree. [reported] (source: wilno-churches-1910)
- Międzyrzecz: closed and transferred to Orthodox use in 1891; a regional place synthesis reports resumed Catholic worship in 1906-1907, while the secondary diocesan list describes new construction in 1912. Missing indexed births in 1887-1906 begin before the closure, so closure alone cannot explain that gap. Basis: regional place synthesis and collection report dated 2026-11-13, not newly read original registers; chronology: church-transfer-1891. [reported] (source: wilno-churches-1910; source: geneteka)
- Neighbouring Catholic registration: the regional collection report of 2026-11-13 found entries for settlements of the Międzyrzecz area in Różana books during 1891-1903. This is an index observation, not proof of travel, the physical baptismal site or formal parish attachment. Różana is a grounded search route; Wołkowysk, Słonim and Kosów Poleski need their own period and inventory check. [reported] (source: geneteka; source: wilno-churches-1910)
- Other-confession route: an Orthodox church in a former Catholic building may have kept separate Orthodox books. Search the church and consistory inventories independently; neither the building transfer nor a Catholic-looking surname proves conversion. The regional test report of 2026-11-13 did not establish that the Sławatycze Orthodox index is the Międzyrzecz church; Jeremicze duplicates also remain unexplained. [unverified] (source: geneteka; source: niab; source: eais)
- Faith law: the toleration decree of 17 April 1905 (old style; 30 April Gregorian) is a candidate explanation for returns from Orthodoxy, late entries and changed confessional registration. The generator's regional hypothesis note cites it, but the operative text and rules for children were not read for this pack. Check the law and local conversion lists before inferring a return or a delayed baptism. [unverified] (source: niab; source: eais)
- Temporary worship after 1905: Zelwa built a shed in 1905; Łysków used a shed from 1906; Wielka Brzostowica built a new church in 1910. Search books under the parish even when the old church was not returned. These local events do not establish a general return of buildings in 1905. Basis: forum transcription; chronology: temporary-worship-1905. [reported] (source: wilno-churches-1910)
- Current custody: check NIAB Grodno and NIAB Minsk separately by parish, confession and year. The regional catalogue report of 2026-11-13 attributes later Międzyrzecz books to Grodno and Różana material to Minsk; this does not establish every volume's custody. Inventories are not name indexes. FamilySearch offers catalogue and image routes, sometimes requiring host login; an indexed entry does not promise open images. [reported] (source: niab; source: familysearch; custody: by-parish-before-1918)
- Second copies: LVIA fond 604 (Vilna Catholic consistory), through EAIS, is a candidate for missing parish books. Existence of that fond does not establish duplicates for each parish in 1891-1906; check inventory, year, confession and completeness before ordering. The regional hypothesis note proposed this route without seeing the relevant files. [unverified] (source: eais)
- AAB Białystok reports Grodno deanery second copies for 1865-1937, with 1865-1910 digitised except one year in the inherited inventory note. The pack's 2026-11-12 page check did not re-establish those holdings; access is by arrangement, not an open online viewer. Do not extend Grodno deanery coverage to Wołkowysk or Różana without an inventory. [reported] (source: aab)
- Open index snapshot, from the regional catalogue collection of 2026-11-13: Różana baptisms 1796-1912, marriages ending 1890, deaths ending 1903; Międzyrzecz baptisms ending 1886 and resuming 1907, marriages ending 1891, deaths ending 1890. Zelwa, Łysków and Wołkowysk Catholic indexes end in 1864; Łukonica and Dereczyn in 1866. These are catalogue limits, not proof that later records were never made or are lost. [reported] (source: geneteka)
- Other indexed windows within 1887-1907: Słonim and Kosów Poleski 1887-1890 for all three register types; Porozów marriages 1887-1888 and 1897-1898, deaths 1892 and 1900-1904; Sławatycze Orthodox baptisms 1900 and 1902, marriages/deaths 1900-1902; Jeremicze Greek Catholic marriages 1900-1902; Siedzielniki Orthodox marriages 1901-1902 and 1906-1907, deaths 1906-1907. Basis: the same catalogue report; endpoints do not guarantee complete years. [reported] (source: geneteka)
- War, borders and displaced books: use chronology interwar, border-1939, border-1945 and occupation-1939-1946 to choose jurisdictions. The latter's resettlement summary is unverified. No parish-specific wartime evacuation, destruction or postwar transfer of books is established here; query parish, diocesan and state inventories, then compare an independent second copy. A regional test report found a numbering gap in a digital Różana baptism book for 1906; its cause and completeness of other copies remain unknown. [reported] (source: niab; source: eais; source: aab; source: familysearch)


## RP-61

- Compare departure applications with arrival and naturalization records: an application does not prove migration, and the historical label Russia does not establish ethnicity. JDC and the Canadian Russian-immigrant collection are collection-specific routes, not complete population censuses. Basis: ex-ussr-kinship-research v1.44.0, references/source-strategy.md:319–324 and references/seed-sources.md:406, outside observations, not rechecked by Familiar. [reported] (source: jdc-names; source: lac-russian-immigrants)

## RP-63

- Before a Soviet POW enquiry, choose the recipient by the camp or burial territory: the Dresden centre describes a Saxony remit and directs other cases to Bundesarchiv; historical Wehrkreis IV and modern Saxony are not identical. An index hit alone does not choose the archive. Basis: ex-ussr-kinship-research v1.46.0, references/seed-sources.md:371 and references/correspondence.md:28; rules reportedly read there on 2026-11-15, not rechecked by Familiar. [reported] (source: stsg-pows)
- In German captivity and forced-labour documents check swapped given/surnames and observed German index forms; distinguish MM/DD from DD/MM using the locale and image. Basis: ex-ussr-kinship-research v1.44.0, references/germany-forced-labour.md:7–11, outside observation, not rechecked by Familiar. [reported] (source: arolsen; source: stsg-pows)
- An incomplete Arolsen online collection may continue through an optional request and the local archive or civil registry at the event place. Waiting for a reply does not close other accessible routes. Basis: the same external guide, references/germany-forced-labour.md:20,24–29,33–39, not rechecked by Familiar. [reported] (source: arolsen)

## RP-67

- The Lithuanian surname dictionary suggests forms and search places, not a family's origin. Its early 1930s lists excluded the Vilna and Klaipėda regions, collected later; current copying terms require review before use. Basis: ex-ussr-kinship-research v1.46.0, references/seed-sources.md:288, outside reading of 2026-11-14, not rechecked by Familiar. [reported] (source: lki-surnames)
- In Geneteka use parent and pair search where relevant to the question; a person's role as parent in a child's act is not an event in the parent's own life. Basis: ex-ussr-kinship-research v1.44.0, references/source-strategy.md:98–102, outside observation, not rechecked by Familiar. [reported] (source: geneteka)
- In GWAR, `birth_place` alone does not establish birthplace: inspect the form group and document, separating captivity, reports, hospital and award cards. Basis: ex-ussr-kinship-research v1.44.0, references/ww1-search.md:17–21 and references/seed-sources.md:374, outside observation, not rechecked by Familiar. [reported] (source: gwar)
