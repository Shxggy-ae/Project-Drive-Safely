# Project-Drive-Safely

## Traffic Beat

Een 2D-verkeersspel in Pygame met vier presetlevels, waaronder **Story** en
drie bundled MP3-tracks, plus een Custom Mode voor MP3-bestanden. Story
gebruikt origineel gegenereerde instrumentale audio van 60 seconden. De
MP3-ritme-inputs worden op een voorspelbare kwartnoot-grid uitgelijnd;
verkeers-events zijn begrensd op 160 BPM. Lange
muziekdelen maken een reeks auto's in
dezelfde rijrichting waarvoor je het licht kunt activeren. De stad gebruikt
een donkerder avondpalet, met gebouwen en duidelijke verkeerslichten.

### Starten op Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe index.py
```

Selecteer in VS Code `.venv\Scripts\python.exe` als Python-interpreter.

### Besturing

- **New Game:** kies een van de vier presetlevels. Story is het eerste level.
- **Song kiezen:** klik op een nummer, druk 1-4, of gebruik de pijltjestoetsen
  en Enter. Escape gaat terug naar het hoofdmenu.
- **Song preview:** druk op P om tien seconden van het geselecteerde presetnummer
  te beluisteren voordat je start.
- **MP3-presets:** Shotta's, Wait a Minute! en Neon Guts worden direct vanuit
  de `presets`-map geladen en ritme-geanalyseerd, onafhankelijk van de huidige
  werkmap van waaruit het spel is gestart.
- **Custom MP3:** kies een MP3-bestand; het spel analyseert de beats en speelt
  het nummer af tijdens het level. De gedetecteerde pieken worden op de beatgrid
  uitgelijnd; verkeers-events zijn begrensd op 160 BPM.
- **Verkeerslichten:** druk A = west, D = oost, W = noord en S = zuid; de
  pijltjestoetsen en klikken op een verkeerslicht werken ook. Je kunt op elk
  moment elke rij openen. De geel gemarkeerde rij is slechts een optionele
  suggestie, geen verplichte invoer. Het verkeer volgt de beatgrid, met maximaal
  twee auto's per beat zodat snelle nummers beheersbaar blijven.
- **Ritmescore:** elke rij-invoer geeft 50 punten; binnen het beatvenster zijn
  dat 100 punten en bouw je je on-beat-streak op. Een on-beat-activatie
  vermindert de wachttijd van die rij met vier beats in plaats van twee, zodat
  je duidelijk meer tijd krijgt voordat bestuurders ongeduldig worden. Buiten
  het beatvenster opent de rij ook gewoon en is er geen straf of rhythm-misser.
  Het venster is
  maximaal 400 ms aan weerszijden van de beat en wordt smaller bij een hoog
  tempo, zodat aangrenzende beats niet overlappen. Voltooi de track voor 1000
  bonuspunten. De beatrail toont beats die over 900 ms naar de hitlijn bewegen;
  het hitgebied blijft zichtbaar en licht op wanneer je binnen het venster zit.
  De metronoom volgt de gedetecteerde beats van het gekozen nummer; druk M om
  de tikken aan of uit te zetten. Muziek speelt op 80% volume en de metronoom
  op 20% harder dan de song. Score, BPM, beatrail, metronoomstatus en
  lane-patience staan compact in de boven- en onderbalk. Een waveform staat
  met 10% opacity subtiel op de achtergrond.
- **Highscore:** je beste score wordt getoond en opgeslagen in `highscore.txt`,
  zodat die ook na het afsluiten van het spel bewaard blijft.
- **Lane-signaal:** de startgids en borden naast de wegen tonen de toetsen. De
  verkeerslichten hebben duidelijke rode, gele en groene lampen. Elke druk
  opent de gekozen rij onmiddellijk, minstens drie verkeersbeats en langer
  wanneer een lange wachtrij meer tijd nodig heeft. Een andere rij
  activeren zet het vorige groene licht op geel. Auto's tonen met een pijl of
  ze linksaf, rechtdoor of rechtsaf gaan.
- **Wisselen van rij:** open een rij wanneer verkeer daarom vraagt. De
  patience van een wachtende rij loopt terug wanneer die rij wordt bediend en
  wordt direct gereset zodra de aanrijstrook geen auto's meer bevat.
- **60-seconden-vooruitblik:** de beat-analyse kijkt naar de volgende minuut.
  De zijbalk toont de aantallen per rij en de eerstvolgende auto's met hun
  rijrichting en aankomsttijd.
- **Patience:** wordt per beat bijgewerkt. Een bediende rij verliest twee
  wachttijden, of vier na een on-beat-activatie; een actieve groene rij met
  verkeer verliest er twee. Wachtende auto's bij rood verhogen de wachttijd,
  bewegende auto's verlagen die. Zonder auto's wordt de patience direct
  gereset. Bij 90% wordt het licht geel; bij 100% eindigt het spel. Vanaf 50%
  roepen wachtende bestuurders om aandacht en vanaf 75% verschijnt een
  gevaarswaarschuwing.
- Auto's kiezen willekeurig rechtdoor, linksaf of rechtsaf. Verkeer dat de
  stopstreep al is overgestoken blijft doorrijden. Meerdere geopende rijen
  kunnen tegelijk het kruispunt oprijden: een botsing tussen auto's uit
  verschillende rijrichtingen eindigt het spel; auto's die elkaar in dezelfde
  rij overlappen veroorzaken geen crash.
- **Spatie:** pauzeren/hervatten. **M:** metronoom aan/uit tijdens het spelen
  en terug naar menu na een level. Klik op RETRY op het game-over-scherm voor
  een nieuwe poging; zo blijft de R beschikbaar voor je naam.
- **Loading:** preset- en MP3-selecties tonen eerst een loading-scherm terwijl
  het nummer wordt geladen of geanalyseerd.
- **Extra voorzichtig tempo:** verkeers-events boven 160 BPM worden in de
  gameplay begrensd tot 160 BPM; presetkaarten tonen het tempo waarop de
  beatgrid en gameplay draaien.
  Dit voorkomt onhaalbare custom-songrijen.
- **Leaderboard:** kies HIGH SCORES in het hoofdmenu. Na een run kun je een
  naam van maximaal vijf tekens invoeren en met Enter opslaan. Gebruik RETRY
  voor een nieuwe poging of MENU (ESC) om terug te gaan; beide knoppen zijn
  klikbaar. Game overs tonen score, track en reden (patience, collision of
  tracktijd); ritmefouten beëindigen de run niet.
- **Menucontrols:** pijltjestoetsen of W/A/S/D navigeren de hoofdmappen;
  Enter bevestigt een keuze.

Preset- en customtracks spelen één keer af. De gameklok start tegelijk met de
muziek en het volume wordt in de laatste twee seconden geleidelijk zachter,
zodat de run tegelijk met het nummer eindigt.

De custom analyse gebruikt Pygame's MP3-decoder, audio-energiepieken en
langere energiedelen. Bij muziek zonder duidelijke beats gebruikt de analyse
een 120-BPM-bronritme en blijft het verkeersschema begrensd op 160 BPM. Auto's die de
stopstreep voorbij zijn blijven doorrijden, ook als het licht daarna rood wordt.
