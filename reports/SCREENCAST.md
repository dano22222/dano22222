# Manus til en fem minutters skjermvideo

Manuset er laget for rolig tale med korte pauser mens du viser appen. Prøv det én gang med stoppeklokke. Skjermhandlingene i kursiv skal ikke leses opp. Bruk den samme eksisterende Streamlit-adressen og vis ferdige regiondata for NO3 i 2024. Ikke vis `.env`, API-nøkler eller Streamlit secrets.

## 0:00–0:35 | Innledning

*Vis forsiden av den eksisterende Streamlit-appen.*

Hei! I denne videoen skal jeg vise Part 3 av IND320-prosjektet mitt. Prosjektet undersøker norske vannmagasiner, kraftutveksling og værdata. I Part 1 jobbet jeg med utforskning og visualisering av magasindata. I Part 2 la jeg til API-er og en datakjede med Spark, Cassandra og MongoDB. I Part 3 har jeg utvidet løsningen med historiske værdata, sesonganalyse og metoder for å finne uvanlige observasjoner. Jeg har beholdt den samme Streamlit-adressen gjennom alle delene.

## 0:35–1:10 | Forbedringer fra Part 2

*Åpne Reservoir Data, velg et område og et kort datointervall. Vis tabellen og nedlastingsknappen. Åpne deretter Reservoir Plots.*

Først vil jeg vise forbedringene etter tilbakemeldingene fra Part 2. På datasiden kan jeg nå velge et datointervall. Det samme filteret brukes i oversiktstabellen, det detaljerte datasettet og CSV-filen jeg kan laste ned. Områdevalget deles mellom magasin- og væranalysene. Grafene viser som standard én variabel og ett område. Jeg kan fortsatt sammenligne områder, men dette er nå et aktivt valg. Det gjør grafene lettere å lese.

## 1:10–2:10 | STL og spektrogram

*Åpne STL and Spectrogram. Vis STL, endre én parameter, og åpne deretter spektrogramfanen.*

Den første nye siden analyserer fyllingsgraden i magasinene. Her bruker jeg én regelmessig ukentlig tidsserie for det valgte området over flere år. STL deler serien i en langsiktig trend, et sesongmønster og en restkomponent. Standardperioden er 52 uker. Jeg kan endre sesongutjevning, trendutjevning og robust tilpasning. Den robuste varianten reduserer påvirkningen fra uvanlige uker.

Den andre fanen viser et spektrogram av akkurat samme tidsserie. Det viser hvordan styrken til ulike periodiske mønstre utvikler seg over tid. Én syklus per år tilsvarer et årlig mønster. Jeg kan justere vinduslengde og overlapp. Et lengre vindu skiller frekvenser tydeligere, men gir mindre presis informasjon om når endringer skjer.

## 2:10–3:30 | Værdata, SPC og LOF

*Åpne SPC and LOF. Velg EL, område 3, år 2024 og 1000-point regional mean. Vis datadekningen. Åpne begge analysefanene og endre én parameter i hver.*

Værdelen bruker historiske ERA5-data fra Open-Meteo. Jeg har trukket 1000 tilfeldige punkter innenfor NO3 og bruker gjennomsnittlig temperatur og nedbør per time. Punktene er trukket i en arealriktig kartprojeksjon med en fast tilfeldig seed, slik at utvalget kan gjenskapes. Året 2024 er et skuddår og gir 8784 timer. ERA5 er et modellbasert reanalysedatasett, så punktene skal ikke tolkes som 1000 uavhengige værstasjoner.

I SPC-fanen bruker jeg en diskret cosinustransformasjon til å beregne en jevn nedbørsbaseline. Deretter bruker jeg median og median absolutt avvik fra hele året til å beregne robuste kontrollgrenser. Grafen viser den opprinnelige nedbøren, grensene og markerte uteliggere. Jeg kan endre frekvensgrensen og grensebredden. Siden nedbør er skjevfordelt, er grensene beskrivende og ikke et sikkert mål på hvor sjelden en hendelse er.

LOF-fanen finner lokalt uvanlige temperaturer og temperaturendringer. Funksjonen bruker standardiserte verdier og har én prosent som standardandel anomalier. Den viser også antall og hvilke timer som er markert. Et markert punkt betyr ikke automatisk at målingen er feil.

## 3:30–4:30 | Kode, testing og videreført funksjonalitet

*Vis kort `src/weather.py`, `src/analysis.py` og den kjørte Part 3-notebooken. Vis testresultatet og Electricity-siden.*

Koden er delt i gjenbrukbare funksjoner som brukes både i notebooken og appen. Værfunksjonen tar område og tidsintervall, slår opp koordinatene og mellomlagrer hver punktserie. Det gjør at en avbrutt nedlasting kan fortsette uten å hente alt på nytt. Den kontrollerer blant annet tidsdekning, enheter og manglende verdier.

Testene undersøker kjente sesongmønstre, innlagte avvik, rekonstruksjon av STL og en forventet årlig spektraltopp. Jeg har også tester for datofiltrering, punktplassering, caching og Streamlit. Den tidligere kraftutvekslingssiden er beholdt, og MongoDB-tilkoblingen bruker fortsatt miljøvariabler eller Streamlit secrets. Innloggingsinformasjon ligger ikke i GitHub.

## 4:30–5:00 | Dokumentasjon og avslutning

*Vis notebookens logg og AI-beskrivelse, README og merge-historikken på GitHub.*

Prosjektet har nå egne mapper for notebooker og rapporter, og en README med installasjon og bruk. Notebooken dokumenterer metodevalg, begrensninger, utviklingslogg og AI-bruk. En viktig geografisk begrensning er at administrative NVE-regioner brukes som dokumenterte tilnærminger for VASS-områdene. Utviklingen er gjort på en egen gren, med synlig sammenslåing til main. Samlet gir Part 3 flere måter å undersøke sesongmønstre og uvanlige observasjoner på, samtidig som tidligere funksjonalitet er videreført. Takk for at du så på!

## Etter opptaket

Legg den tilgjengelige videolenken inn i notebooken eller som innleveringskommentar i Canvas. Kontroller delingstillatelsene og at videoen varer omtrent fem minutter. PDF-en kan leveres som den ene tillatte filen i Canvas; videolenken kan gis i kommentaren, slik at PDF-en ikke må bygges om etter opptaket.
