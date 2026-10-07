import json
import os
import requests
import urllib3
from bs4 import BeautifulSoup

# Wyłączenie ostrzeżeń SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KONFIGURACJA ---
URL_GLOWNA = "https://liga.futbolsport.pl/"
URL_TERMINARZ = "https://liga.futbolsport.pl/terminarz"
URL_GALERIE = "https://liga.futbolsport.pl/galerie"

NAZWA_DRUZYNY = "Canvas Logistics"
TELEGRAM_BOT_TOKEN = "8827199378:AAFxeZ8dQxSQMxfniNEtPXihk6gaM4P-vLs"
TELEGRAM_CHAT_ID = "2143266199"
STATE_FILE = "bot_stan.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def wyslij_telegram(tekst):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": tekst,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        odpowiedz = requests.post(api_url, data=payload, timeout=10)
        odpowiedz.raise_for_status()
    except Exception as e:
        print(f"Błąd wysyłania na Telegram: {e}")


def wczytaj_stan():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ostatni_artykul": "", "ostatni_mecz": "", "ostatnia_galeria": ""}


def zapisz_stan(stan):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(stan, f, ensure_ascii=False, indent=2)


def pobierz_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"Błąd pobierania {url}: {e}")
        return None


# 1. ARTYKUŁY
def sprawdz_artykuly(stan):
    soup = pobierz_soup(URL_GLOWNA)
    if not soup:
        return

    link_element = None
    for a in soup.find_all("a", href=True):
        if "Czytaj więcej" in a.get_text(strip=True):
            link_element = a
            break

    if not link_element:
        return

    art_url = link_element["href"]
    if not art_url.startswith("http"):
        art_url = "https://liga.futbolsport.pl" + (
            art_url if art_url.startswith("/") else "/" + art_url
        )

    tytul = "Nowy wpis"
    parent = link_element.parent
    for _ in range(4):
        if not parent:
            break
        header = parent.find(["h2", "h3", "h4", "h5", "strong"])
        if header and "Czytaj więcej" not in header.get_text():
            tytul = header.get_text(strip=True)
            break
        parent = parent.parent

    if art_url != stan.get("ostatni_artykul"):
        print(f"Wykryto artykuł: {tytul}")
        if stan.get("ostatni_artykul"):
            msg = (
                f"📰 <b>Nowy artykuł na futbolsport.pl!</b>\n\n"
                f"<b>{tytul}</b>\n\n"
                f"🔗 <a href='{art_url}'>Czytaj więcej</a>"
            )
            wyslij_telegram(msg)
        stan["ostatni_artykul"] = art_url


# 2. TERMINARZ
def sprawdz_terminarz(stan):
    soup = pobierz_soup(URL_TERMINARZ)
    if not soup:
        return

    znaleziony_mecz = None
    for row in soup.find_all("tr"):
        komorki = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        row_text = " ".join(komorki)
        if NAZWA_DRUZYNY.lower() in row_text.lower() and "- : -" in row_text:
            znaleziony_mecz = komorki
            break

    if not znaleziony_mecz:
        print("Nie znaleziono nadchodzącego meczu Canvas Logistics w terminarzu.")
        return

    mecz_id = " | ".join(znaleziony_mecz)
    if mecz_id != stan.get("ostatni_mecz"):
        print(f"Wykryto nadchodzący mecz: {mecz_id}")
        if stan.get("ostatni_mecz"):
            msg = (
                f"⚽ <b>Nowy mecz w terminarzu!</b>\n\n"
                f"📋 <b>Informacje:</b>\n"
                f"{mecz_id}\n\n"
                f"🔗 <a href='{URL_TERMINARZ}'>Zobacz pełny terminarz</a>"
            )
            wyslij_telegram(msg)
        stan["ostatni_mecz"] = mecz_id


# 3. GALERIE ZDJĘĆ
def sprawdz_galerie(stan):
    soup = pobierz_soup(URL_GALERIE)
    if not soup:
        return

    pierwsza_galeria = None
    for a in soup.find_all("a", href=True):
        if "/galerie/" in a["href"]:
            nazwa = a.get_text(strip=True)
            if nazwa and len(nazwa) > 3:
                link = a["href"]
                if not link.startswith("http"):
                    link = "https://liga.futbolsport.pl" + (
                        link if link.startswith("/") else "/" + link
                    )
                pierwsza_galeria = (nazwa, link)
                break

    if not pierwsza_galeria:
        return

    nazwa_galerii, link_galerii = pierwsza_galeria
    if link_galerii != stan.get("ostatnia_galeria"):
        print(f"Wykryto nową galerię: {nazwa_galerii}")
        if stan.get("ostatnia_galeria"):
            msg = (
                f"📸 <b>Dodano nową galerię zdjęć!</b>\n\n"
                f"🖼️ <b>{nazwa_galerii}</b>\n\n"
                f"🔗 <a href='{link_galerii}'>Zobacz zdjęcia</a>"
            )
            wyslij_telegram(msg)
        stan["ostatnia_galeria"] = link_galerii


def main():
    stan = wczytaj_stan()
    sprawdz_artykuly(stan)
    sprawdz_terminarz(stan)
    sprawdz_galerie(stan)
    zapisz_stan(stan)


if __name__ == "__main__":
    main()
