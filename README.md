# 🎬 Kino – Lokale Video-Mediathek mit Webserver

Kino ist ein Python-Projekt zur Verwaltung und Bereitstellung einer lokalen Filmsammlung.
Es scannt eine Verzeichnisstruktur (z. B. eine USB-Festplatte), erzeugt automatisch eine SQLite-Datenbank, erstellt Vorschaubilder (Thumbnails) für Videos und stellt die Inhalte über einen integrierten Webserver bereit.
Beim Start werden nur neue Videos hinzugefügt, nicht mehr vorhandene automatisch entfernt und eine JSON-Bibliothek für Web-Frontends erzeugt.
Kino ist sehr schlank und läuft bei mir auf einem Raspberry Pi 2B. Die Videos werden in kleinen 1-MB-Paketen gesendet, sodass der Pi auch mit mehreren Clients keine Probleme hat. 

# Tips


# Verzeichnisstruktur
```ASE_DIR/
├── Filme/
│   ├── Action/
│   │   ├── movie_1.mkv
│   │   └── movie_2.mp4
│   └── Drama/
│       └── movie_3.mp4
└── Serien/
    └── SciFi/
        └── episode_1.mkv
```

Top-Ordner → type (z. B. Filme, Serien)

Unterordner → category (z. B. Action, Drama)

Dateiname → Filmtitel (Unterstriche werden automatisch zu Leerzeichen)


# Konfiguration (config.yaml)
```
base_dir: /media/usb/kino
web_video_dir: videos
cover_dir: covers
port: 8080
num_thumbnails: 5
chunked_size: 1
timeout: 600
```

| Schlüssel        | Beschreibung                                |
| ---------------- | ------------------------------------------- |
| `base_dir`       | Basisverzeichnis mit allen Videos, bei mir externe USB festlatte am Rasbbery Pi 2 B           |
| `web_video_dir`  | Symlink für den Webserver                   |
| `cover_dir`      | Ordner für generierte Thumbnails            |
| `port`           | Port des Webservers                         |
| `num_thumbnails` | Anzahl Thumbnails pro Video                 |
| `timeout`        | Server- und Verbindungs-Timeout in Sekunden |

# Abhängigkeiten

Python ≥ 3.8
ffmpeg
ffprobe

# Installation

sudo apt install ffmpeg
pip install pyyaml

## Kino als systemd-Dienst (Autostart & Watchdog)

Damit `kino.py` automatisch beim Systemstart läuft und **nach einem Crash selbstständig neu startet**, wird es als **systemd-Dienst** eingerichtet.

---

## Voraussetzungen

- Linux mit **systemd** (z. B. Debian, Ubuntu, Raspberry Pi OS)
- Python 3 installiert
- Projekt liegt z. B. unter:

```
/opt/kino/
├── kino.py
├── config.yaml
├── movies.db
└── covers/
```

### User kino analegen

```
sudo useradd -r -s /bin/false kino
sudo chown -R kino:kino /opt/kino
```

### Service datei

`sudo nano /etc/systemd/system/kino.service`

**Inhalt:**

```
[Unit]
Description=Kino Medienserver
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=kino
Group=kino
WorkingDirectory=/opt/kino
ExecStart=/usr/bin/python3 /opt/kino/kino.py

# Neustart bei Absturz
Restart=always
RestartSec=5

# Watchdog
WatchdogSec=60
TimeoutStopSec=30

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Dienst aktivieren & starten

```
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable kino.service
sudo systemctl start kino.service
```
