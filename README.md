# Thunderbird Email Inspector

Bezpecny dry-run projekt pro prvni praci s lokalnim profilem Mozilla Thunderbird na Windows.

Cilem je pouze zjistit, kde Thunderbird uklada profily, jake ucty jsou v profilu nastavene a jake lokalni postovni slozky jsou dostupne. Skript nic nemaze, nic neposila, nic nepresouva a nemeni zadne soubory Thunderbirdu.

## Co projekt dela

- Najde standardni slozku Thunderbirdu ve Windows: `%APPDATA%\Thunderbird`.
- Nacte `profiles.ini` a vypise dostupne profily.
- Z aktivniho profilu precte `prefs.js` pouze pro zjisteni uctu a serveru.
- Vypise lokalni slozky v `Mail` a `ImapMail`.
- U kazde slozky ukaze cestu, velikost a zda jde pravdepodobne o mbox soubor.

## Co projekt nedela

- Nemaze e-maily.
- Nemeni profil Thunderbirdu.
- Neodesila zadne zpravy.
- Neotevira pripojeni k e-mailovym serverum.
- Necte ani nevypisuje obsah jednotlivych e-mailu.
- Nepracuje s hesly ani prihlasovacimi udaji.

## Pozadavky

- Windows 10 nebo Windows 11.
- Nainstalovany Mozilla Thunderbird.
- Python 3.10 nebo novejsi.

Overeni Pythonu v PowerShellu:

```powershell
python --version
```

Pokud prikaz nefunguje, nainstalujte Python z Microsoft Store nebo z https://www.python.org/downloads/windows/.

## Spusteni

V PowerShellu otevri slozku projektu a spust:

```powershell
python thunderbird_dry_run.py
```

Skript je ve vychozim nastaveni vzdy v dry-run rezimu. Pro jistotu vypise stav `DRY RUN: enabled`.

## Volitelne zadani profilu

Pokud mate vice profilu a chcete nacist konkretni cestu:

```powershell
python thunderbird_dry_run.py --profile "C:\Users\Admin\AppData\Roaming\Thunderbird\Profiles\xxxxxxxx.default-release"
```

## Volitelny JSON vystup

Pro dalsi zpracovani lze pouzit JSON:

```powershell
python thunderbird_dry_run.py --json
```

## Bezpecnostni pravidla

1. Skript pouziva pouze cteni souboru.
2. Skript ignoruje soubory s hesly a prihlasovacimi udaji.
3. Skript nevypisuje obsah zprav.
4. Skript je urceny jako prvni diagnosticky krok pred jakoukoliv synchronizaci.

## Typicky vystup

```text
DRY RUN: enabled
Thunderbird base: C:\Users\Admin\AppData\Roaming\Thunderbird
Selected profile: C:\Users\Admin\AppData\Roaming\Thunderbird\Profiles\xxxxxxxx.default-release

Accounts:
- account1: user@example.com, imap.example.com

Folders:
- ImapMail/imap.example.com/INBOX  125.4 MB  mbox
- Mail/Local Folders/Archive       32.8 MB   mbox
```

## Dalsi kroky

Az bude vystup zkontrolovany, lze bezpecne navrhnout dalsi samostatny skript pro hledani konkretnich zakazek, objednavek nebo newsletteru. Ten by mel zustat oddeleny od tohoto zakladniho dry-run inspektoru.
