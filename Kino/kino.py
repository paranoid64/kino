#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
kino.py
Erstellt eine SQLite-Datenbank mit allen Filmen auf der USB-Festplatte.
Bei jedem Start werden nur neue Videos hinzugefügt, alte gelöscht.
JSON wird für den Webserver erzeugt.
Autor: Marcus Lausch Datum: 2026-01-04
"""

import os
import json
import subprocess
import yaml
import sqlite3
import time
import socket
from socketserver import ThreadingMixIn
from http.server import HTTPServer, SimpleHTTPRequestHandler

# =============================
# KONFIGURATION Laden (YAML)
# =============================

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

BASE_DIR = config["base_dir"]
WEB_VIDEO_DIR = config["web_video_dir"]
COVER_DIR = config["cover_dir"]
PORT = config["port"]
NUM_THUMBNAILS = config.get("num_thumbnails", 5)
CHUNK_SIZE = config.get("chunked_size", 1)
TIMEOUT = config.get("timeout", 600)

os.makedirs(COVER_DIR, exist_ok=True)

# =============================
# SYMLINK ANLEGEN
# =============================

if os.path.islink(WEB_VIDEO_DIR):
    pass
elif os.path.exists(WEB_VIDEO_DIR):
    print(f"'{WEB_VIDEO_DIR}' existiert, ist aber kein Symlink!")
else:
    os.symlink(BASE_DIR, WEB_VIDEO_DIR)
    print(f"Symlink angelegt: {WEB_VIDEO_DIR} -> {BASE_DIR}")

# =============================
# DATABASE
# =============================

DB_FILE = "movies.db"
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,
    title TEXT,
    file TEXT UNIQUE,
    category TEXT,
    type TEXT,
    thumbnails TEXT,
    duration REAL,
    last_seen INTEGER
)
""")
conn.commit()

# =============================
# VIDEO-HILFSFUNKTIONEN
# =============================

def get_video_duration(file_path):
    """Gibt die Dauer des Videos in Sekunden zurück."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        output = result.stdout.decode("utf-8").strip().splitlines()
        if not output:
            print(f"Keine Dauer gefunden: {file_path}")
            return 0.0
        try:
            return float(output[-1])
        except ValueError:
            print(f"Ungültige Dauer (Header defekt?) für: {file_path}")
            return 0.0
    except Exception as e:
        print(f"Fehler beim Auslesen der Dauer von {file_path}: {e}")
        return 0.0

def generate_thumbnails(file_path, title, cover_dir=COVER_DIR, num=NUM_THUMBNAILS):
    """Generiert Thumbnails pro Video, wenn noch keine existieren."""
    duration = get_video_duration(file_path)
    thumbs = []

    if duration <= 0.0:
        print(f"Überspringe Thumbnails, Dauer ungültig: {title}")
        return thumbs

    os.makedirs(cover_dir, exist_ok=True)

    for i in range(num):
        t = duration * (i + 1) / (num + 1)
        thumb_file = f"{title}_{i+1}.jpg"
        thumb_path = os.path.join(cover_dir, thumb_file)

        # Wenn das Thumbnail bereits existiert, überspringen
        if os.path.exists(thumb_path):
            print(f"Thumbnail existiert bereits: {thumb_path}")
            thumbs.append(f"{cover_dir}/{thumb_file}")
            continue

        # Thumbnail erstellen, wenn es noch nicht existiert
        try:
            print(f"Erstelle Thumbnail für: {thumb_file}")
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(t), "-i", file_path, "-vframes", "1", "-q:v", "2", "-s", "320x180", thumb_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=30
            )
            thumbs.append(f"{cover_dir}/{thumb_file}")
            print(f"Thumbnail erstellt: {thumb_file}")

        except subprocess.CalledProcessError as e:
            print(f"Fehler beim Erstellen des Thumbnails für {file_path}: {e}")
            continue

    return thumbs

# =============================
# FILME SCANNEN UND DB UPDATE
# =============================

def clean_title(filename):
    # Unterstriche durch Leerzeichen ersetzen
    title = filename.replace("_", " ")
    title = os.path.splitext(title)[0]
    return title

current_time = int(time.time())

for top_category in os.listdir(BASE_DIR):
    top_path = os.path.join(BASE_DIR, top_category)
    if not os.path.isdir(top_path):
        continue

    for category in os.listdir(top_path):
        cat_path = os.path.join(top_path, category)
        if not os.path.isdir(cat_path):
            continue

        for f in os.listdir(cat_path):

            # Wenn die Datei mit '._' beginnt, löschen und überspringen
            if f.startswith('._'):
                file_path = os.path.join(cat_path, f)
                print(f"Lösche temporäre Datei: {file_path}")
                os.remove(file_path)  # Datei löschen
                continue

            # Prüfen auf unterstützte Videoformate
            if not f.lower().endswith((".mp4", ".mkv", ".mpeg", ".mpg", ".webm", ".ogv", ".m4v")):
                continue

            title = clean_title(f)
            file_path = os.path.join(cat_path, f)

            relative_path = os.path.relpath(file_path, BASE_DIR)
            web_path = f"{WEB_VIDEO_DIR}/{relative_path.replace(os.sep, '/')}"

            # Prüfen, ob der Eintrag schon existiert
            c.execute("SELECT id FROM movies WHERE file=?", (web_path,))
            row = c.fetchone()

            if row:
                # Nur last_seen aktualisieren
                c.execute("UPDATE movies SET last_seen=? WHERE id=?", (current_time, row[0]))
            else:
                print(f"Bearbeite Thumbnails für: {title}")
                thumbs = generate_thumbnails(file_path, title)
                duration = get_video_duration(file_path)
                print(f"Fertig mit {title}, {len(thumbs)} Thumbnails erstellt")
                c.execute(
                    "INSERT INTO movies (title, file, category, type, thumbnails, duration, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (title, web_path, category, top_category, json.dumps(thumbs), duration, current_time)
                )

conn.commit()

# =============================
# ALTE VIDEOS LÖSCHEN
# =============================

c.execute("SELECT id,file FROM movies")
for movie_id, file in c.fetchall():
    real_path = os.path.join(BASE_DIR, file[len(WEB_VIDEO_DIR)+1:].replace("/", os.sep))
    if not os.path.exists(real_path):
        print(f"Entferne nicht mehr vorhandenen Film: {file}")
        c.execute("DELETE FROM movies WHERE id=?", (movie_id,))
conn.commit()

# =============================
# JSON FÜR WEBSERVER
# =============================

c.execute("SELECT title,file,category,type,thumbnails,duration FROM movies")
rows = c.fetchall()
columns = [desc[0] for desc in c.description]

library = []
for r in rows:
    row = dict(zip(columns, r))
    row["thumbnails"] = json.loads(row["thumbnails"])
    library.append(row)

with open("library.json", "w", encoding="utf-8") as fp:
    json.dump({"movies": library}, fp, indent=2, ensure_ascii=False)

print(f"{len(library)} Filme gefunden – JSON gebaut")

# =============================
# WEBSERVER
# =============================

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer, bei dem jede Anfrage in einem eigenen Thread läuft."""
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.timeout = TIMEOUT  # Timeout für den Server

class MyHandler(SimpleHTTPRequestHandler):

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".mp4": "video/mp4",
        ".m4v": "video/m4v",
        ".mpeg": "video/mpeg",
        ".mpg": "video/mpeg",
        ".webm": "video/webm",
        ".ogv": "video/ogg",
        ".mkv": "video/x-matroska",
        ".json": "application/json",
    }

    def handle(self):
        self.connection.settimeout(TIMEOUT)  # Timeout für jede Verbindung
        super().handle()  # Verarbeitet die Anfrage wie gewohnt

    def end_headers(self):
        #self.send_response(200)
        #self.protocol_version = "HTTP/1.1"
        #self.send_header("Connection", "keep-alive")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_GET(self):
        try:
            # Wenn das JSON angefordert wird
            if self.path == "/library.json":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"movies": library}, ensure_ascii=False).encode("utf-8"))
            else:
                file_path = self.translate_path(self.path)
                if os.path.exists(file_path) and file_path.endswith(('.mp4', '.mkv', '.webm', '.ogv', '.mpeg')):
                    self.stream_video(file_path)
                else:
                    super().do_GET()
        except ConnectionResetError:
            print(f"Client hat die Verbindung abgebrochen: {self.client_address}")
        except BrokenPipeError:
            print(f"Pipe ist kaputt, Verbindung abgebrochen: {self.client_address}")

    def stream_video(self, file_path):
        try:
            file_size = os.path.getsize(file_path)
            range_header = self.headers.get("Range")

            start = 0
            end = file_size - 1
            status = 200

            if range_header:
                start, end = self.parse_range(range_header, file_size)
                status = 206

            content_length = end - start + 1

            # ✅ IMMER ZUERST
            self.send_response(status)

            # ✅ DANN Header
            if status == 206:
                self.send_header(
                    "Content-Range",
                    f"bytes {start}-{end}/{file_size}"
                )

            self.send_header("Content-Type", self.guess_type(file_path))
            self.send_header("Content-Length", content_length)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Connection", "close")  # wichtig!
            self.end_headers()

            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length

                while remaining > 0:
                    data = f.read(min(1024 * 1024, remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)

        except BrokenPipeError:
            pass
        except Exception as e:
            print("Streaming-Fehler:", e)



    def parse_range(self, range_header, file_size):
        """Parst den Range-Header und gibt den byte-Bereich zurück."""
        byte_range = range_header.strip().split('=')[1]
        parts = byte_range.split('-')
        byte1 = int(parts[0]) if parts[0] else 0
        byte2 = int(parts[1]) if parts[1] else file_size - 1
        if byte1 > byte2 or byte2 >= file_size:
            raise ValueError("Ungültiger Range")
        return byte1, byte2


hostname = socket.gethostname()
print(f"Webserver läuft auf http://{hostname}:{PORT}")

httpd = ThreadedHTTPServer(("0.0.0.0", PORT), MyHandler)
try:
    httpd.serve_forever()
except Exception as e:
    print(f"Server konnte nicht gestartet werden: {e}")
finally:
    conn.close()
