# Player Data Collection Roster

This is the target data-collection queue for Proxima Football AI. It is not a ranking of the best 200 players. The names were selected to give the model varied positions, playing styles, career lengths, leagues, peak ages, injury histories, and development paths.

The repository currently contains 22 player JSON files, almost all of them attackers. Those players are marked `[x]`. Players still to collect are marked `[ ]`.

## Collection Rules

- Collect every available senior club season, including partial seasons after transfers.
- Keep one consistent player ID and team ID format across all files.
- Store the player's primary position for every season. Do not infer one career-wide position when the player changed roles.
- Use sourced values for appearances, goals, assists, minutes, position, and injuries. Do not present estimated advanced fields as sourced facts.
- Record a source URL and retrieval date for every sourced season.
- Prefer seasons from 2000 onward because advanced-stat coverage is substantially better.
- Include successful, average, injury-affected, early-peak, late-peak, short, and unusually long careers. A model trained only on superstars will overpredict everyone.
- Train goalkeepers separately from outfield players. Goalkeepers need saves, save percentage, post-shot xG, clean sheets, crosses stopped, sweeping actions, and goals conceded rather than an outfield goals/assists target.

## Target Distribution

| Group | Target | Why it is needed |
| --- | ---: | --- |
| Goalkeepers | 20 | Separate goalkeeper model and longevity patterns |
| Centre-backs | 30 | Aerial, ball-playing, recovery, and stopper profiles |
| Full-backs / wing-backs | 25 | Defensive, overlapping, inverted, and attacking profiles |
| Defensive midfielders | 25 | Ball-winning, holding, deep-playmaking, and hybrid profiles |
| Central / attacking midfielders | 30 | Creators, runners, controllers, and late scorers |
| Wingers / inside forwards | 30 | Wide creators, dribblers, scorers, and pace-dependent careers |
| Strikers | 30 | Poachers, target forwards, false nines, and mobile forwards |
| Hybrid attackers / number 10s | 10 | Role-changing and second-striker careers |
| **Total** | **200** | **180 outfield players plus 20 goalkeepers** |

## 1. Goalkeepers (20)

- [ ] Gianluigi Buffon
- [ ] Iker Casillas
- [ ] Manuel Neuer
- [ ] Petr Cech
- [ ] Edwin van der Sar
- [ ] Alisson Becker
- [ ] Ederson
- [ ] Thibaut Courtois
- [ ] Jan Oblak
- [ ] Marc-Andre ter Stegen
- [ ] Hugo Lloris
- [ ] Keylor Navas
- [ ] David de Gea
- [ ] Mike Maignan
- [ ] Gianluigi Donnarumma
- [ ] Emiliano Martinez
- [ ] Wojciech Szczesny
- [ ] Samir Handanovic
- [ ] Victor Valdes
- [ ] Oliver Kahn

## 2. Centre-backs (30)

- [ ] Virgil van Dijk
- [ ] Sergio Ramos
- [ ] Gerard Pique
- [ ] Carles Puyol
- [ ] Fabio Cannavaro
- [ ] Alessandro Nesta
- [ ] Paolo Maldini
- [ ] Rio Ferdinand
- [ ] Nemanja Vidic
- [ ] John Terry
- [ ] Thiago Silva
- [ ] Giorgio Chiellini
- [ ] Leonardo Bonucci
- [ ] Raphael Varane
- [ ] Pepe
- [ ] Diego Godin
- [ ] Vincent Kompany
- [ ] Mats Hummels
- [ ] Jerome Boateng
- [ ] Kalidou Koulibaly
- [ ] Aymeric Laporte
- [ ] Ruben Dias
- [ ] Antonio Rudiger
- [ ] Marquinhos
- [ ] David Alaba
- [ ] William Saliba
- [ ] Gabriel Magalhaes
- [ ] Ronald Araujo
- [ ] Alessandro Bastoni
- [ ] Josko Gvardiol

## 3. Full-backs and Wing-backs (25)

- [ ] Dani Alves
- [ ] Marcelo
- [ ] Ashley Cole
- [ ] Philipp Lahm
- [ ] Roberto Carlos
- [ ] Cafu
- [ ] Patrice Evra
- [ ] Javier Zanetti
- [ ] Maicon
- [ ] Dani Carvajal
- [ ] Jordi Alba
- [ ] Kyle Walker
- [ ] Trent Alexander-Arnold
- [ ] Andrew Robertson
- [ ] Achraf Hakimi
- [ ] Theo Hernandez
- [ ] Joao Cancelo
- [ ] Reece James
- [ ] Kieran Trippier
- [ ] Alphonso Davies
- [ ] Alejandro Balde
- [ ] Nuno Mendes
- [ ] Jeremie Frimpong
- [ ] Federico Dimarco
- [ ] Cesar Azpilicueta

## 4. Defensive Midfielders (25)

- [ ] Sergio Busquets
- [ ] Claude Makelele
- [ ] Casemiro
- [ ] Rodri
- [ ] N'Golo Kante
- [ ] Xabi Alonso
- [ ] Javier Mascherano
- [ ] Fernandinho
- [ ] Gilberto Silva
- [ ] Michael Essien
- [ ] Patrick Vieira
- [ ] Roy Keane
- [ ] Daniele De Rossi
- [ ] Gennaro Gattuso
- [ ] Joshua Kimmich
- [ ] Declan Rice
- [ ] Aurelien Tchouameni
- [ ] Moises Caicedo
- [ ] Joao Palhinha
- [ ] Sandro Tonali
- [ ] Bruno Guimaraes
- [ ] Martin Zubimendi
- [ ] Jorginho
- [ ] Nemanja Matic
- [ ] Yaya Toure

## 5. Central and Attacking Midfielders (30)

- [ ] Luka Modric
- [ ] Toni Kroos
- [ ] Xavi
- [ ] Andres Iniesta
- [ ] Andrea Pirlo
- [ ] Steven Gerrard
- [ ] Frank Lampard
- [ ] Paul Scholes
- [ ] Cesc Fabregas
- [ ] Kevin De Bruyne
- [ ] David Silva
- [ ] Bernardo Silva
- [ ] Thiago Alcantara
- [ ] Ilkay Gundogan
- [ ] Marco Verratti
- [ ] Ivan Rakitic
- [ ] Wesley Sneijder
- [ ] Bastian Schweinsteiger
- [ ] Clarence Seedorf
- [ ] Federico Valverde
- [ ] Frenkie de Jong
- [ ] Pedri
- [ ] Gavi
- [ ] Jude Bellingham
- [ ] Nicolo Barella
- [ ] Hakan Calhanoglu
- [ ] Martin Odegaard
- [ ] Bruno Fernandes
- [ ] Jamal Musiala
- [ ] Florian Wirtz

## 6. Wingers and Inside Forwards (30)

- [x] Cristiano Ronaldo
- [x] Lionel Messi
- [x] Neymar
- [x] Mohamed Salah
- [x] Kylian Mbappe
- [x] Eden Hazard
- [x] Gareth Bale
- [x] Arjen Robben
- [x] Franck Ribery
- [x] Angel Di Maria
- [x] Riyad Mahrez
- [x] Sadio Mane
- [x] Son Heung-min
- [ ] Ronaldinho
- [ ] Luis Figo
- [ ] David Beckham
- [ ] Ryan Giggs
- [ ] Arda Turan
- [ ] Alexis Sanchez
- [ ] Pedro
- [ ] Raheem Sterling
- [ ] Leroy Sane
- [ ] Kingsley Coman
- [ ] Ousmane Dembele
- [ ] Vinicius Junior
- [ ] Bukayo Saka
- [ ] Khvicha Kvaratskhelia
- [ ] Rafael Leao
- [ ] Rodrygo
- [ ] Juan Cuadrado

## 7. Strikers (30)

- [x] Erling Haaland
- [x] Harry Kane
- [x] Karim Benzema
- [x] Luis Suarez
- [x] Sergio Aguero
- [x] Zlatan Ibrahimovic
- [x] Wayne Rooney
- [ ] Robert Lewandowski
- [ ] Didier Drogba
- [ ] Samuel Eto'o
- [ ] Thierry Henry
- [ ] Ronaldo Nazario
- [ ] Ruud van Nistelrooy
- [ ] Fernando Torres
- [ ] David Villa
- [ ] Edinson Cavani
- [ ] Gonzalo Higuain
- [ ] Radamel Falcao
- [ ] Robin van Persie
- [ ] Carlos Tevez
- [ ] Miroslav Klose
- [ ] Mario Gomez
- [ ] Diego Costa
- [ ] Romelu Lukaku
- [ ] Pierre-Emerick Aubameyang
- [ ] Jamie Vardy
- [ ] Lautaro Martinez
- [ ] Victor Osimhen
- [ ] Alexander Isak
- [ ] Julian Alvarez

## 8. Hybrid Attackers and Number 10s (10)

- [x] Antoine Griezmann
- [x] Marco Reus
- [ ] Thomas Muller
- [ ] Kaka
- [ ] Mesut Ozil
- [ ] Juan Roman Riquelme
- [ ] Francesco Totti
- [ ] Alessandro Del Piero
- [ ] Dennis Bergkamp
- [ ] Paulo Dybala

## Dataset Quality Gates

Do not mark a player complete until all applicable checks pass:

- The JSON parses and matches the project's `player`, `teams`, and `seasons` structure.
- Each season has a numeric season, team, position, appearances, goals, assists, and minutes.
- Duplicate `(player_id, season, team_id, league_id)` rows have been resolved.
- Totals are not copied into every competition row and then summed again.
- Current and retired status is explicit.
- Missing values are `null`, not invented zeroes, unless the true sourced value is zero.
- Estimated fields are labeled with their method and are not mixed with sourced fields without provenance.
- The importer succeeds with no failed files.

## Reference Pools

- [StatsBomb Open Data](https://github.com/statsbomb/open-data) provides free event, lineup, and position data suitable for validation and feature engineering.
- [StatsBombPy](https://github.com/statsbomb/statsbombpy) documents fields such as player, position, shots, xG, passes, duels, and goalkeeper events.
- [FBref](https://fbref.com/en/) separates standard, shooting, playing-time, miscellaneous, and goalkeeping tables; use the same table definitions consistently across seasons.
- [FBref position-assignment note](https://fbref.com/en/about/errata) explains that primary-position labels require a meaningful amount of playing time, which is why season-level position should be preserved.
- [UEFA squad lists](https://www.uefa.com/uefachampionsleague/news/029d-1ea2da6b438f-0a4889826e05-1000--champions-league-squads-league-phase-selections-confirmed/) are a useful official cross-check for current elite players and registered positions.

