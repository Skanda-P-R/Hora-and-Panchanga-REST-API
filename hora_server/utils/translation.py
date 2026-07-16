"""Astrological and calendric terminology translations and payload localization."""

from __future__ import annotations

from typing import Any

TRANSLATIONS: dict[str, str] = {
    # Planets
    "Sun": "ಸೂರ್ಯ",
    "Moon": "ಚಂದ್ರ",
    "Mars": "ಕುಜ",
    "Mercury": "ಬುಧ",
    "Jupiter": "ಗುರು",
    "Venus": "ಶುಕ್ರ",
    "Saturn": "ಶನಿ",
    "Rahu": "ರಾಹು",
    "Ketu": "ಕೇತು",

    # Planet chart abbreviations
    "Su": "ಸೂ",
    "Mo": "ಚಂ",
    "Ma": "ಕು",
    "Me": "ಬು",
    "Ju": "ಗು",
    "Ve": "ಶು",
    "Sa": "ಶ",
    "Ra": "ರಾ",
    "Ke": "ಕೇ",

    # Rasis (Sanskrit transliterated in API)
    "Mesha": "ಮೇಷ",
    "Vrishabha": "ವೃಷಭ",
    "Mithuna": "ಮಿಥುನ",
    "Karka": "ಕಟಕ",
    "Simha": "ಸಿಂಹ",
    "Kanya": "ಕನ್ಯಾ",
    "Tula": "ತುಲಾ",
    "Vrishchika": "ವೃಶ್ಚಿಕ",
    "Dhanu": "ಧನು",
    "Makara": "ಮಕರ",
    "Kumbha": "ಕುಂಭ",
    "Meena": "ಮೀನ",

    # Rasis (English zodiac names used in Kundali module)
    "Aries": "ಮೇಷ",
    "Taurus": "ವೃಷಭ",
    "Gemini": "ಮಿಥುನ",
    "Cancer": "ಕಟಕ",
    "Leo": "ಸಿಂಹ",
    "Virgo": "ಕನ್ಯಾ",
    "Libra": "ತುಲಾ",
    "Scorpio": "ವೃಶ್ಚಿಕ",
    "Sagittarius": "ಧನು",
    "Capricorn": "ಮಕರ",
    "Aquarius": "ಕುಂಭ",
    "Pisces": "ಮೀನ",

    # Nakshatras
    "Ashwini": "ಅಶ್ವಿನಿ",
    "Bharani": "ಭರಣಿ",
    "Krittika": "ಕೃತ್ತಿಕಾ",
    "Rohini": "ರೋಹಿಣಿ",
    "Mrigashira": "ಮೃಗಶಿರ",
    "Ardra": "ಆರ್ದ್ರ",
    "Punarvasu": "ಪುನರ್ವಸು",
    "Pushya": "ಪುಷ್ಯ",
    "Ashlesha": "ಆಶ್ಲೇಷ",
    "Magha": "ಮಘಾ",
    "Purva Phalguni": "ಪೂರ್ವ ಫಲ್ಗುಣಿ",
    "Uttara Phalguni": "ಉತ್ತರ ಫಲ್ಗುಣಿ",
    "Hasta": "ಹಸ್ತ",
    "Chitra": "ಚಿತ್ರಾ",
    "Swati": "ಸ್ವಾತಿ",
    "Vishakha": "ವಿಶಾಖ",
    "Anuradha": "ಅನುರಾಧ",
    "Jyeshtha": "ಜ್ಯೇಷ್ಠ",
    "Mula": "ಮೂಲ",
    "Purva Ashadha": "ಪೂರ್ವಾಷಾಢ",
    "Uttara Ashadha": "ಉತ್ತರಾಷಾಢ",
    "Shravana": "ಶ್ರವಣ",
    "Dhanishtha": "ಧನಿಷ್ಠ",
    "Shatabhisha": "ಶತಭಿಷ",
    "Purva Bhadrapada": "ಪೂರ್ವ ಭಾದ್ರಪದ",
    "Uttara Bhadrapada": "ಉತ್ತರ ಭಾದ್ರಪದ",
    "Revati": "ರೇವತಿ",

    # Yogas
    "Vishkambha": "ವಿಷ್ಕಂಭ",
    "Priti": "ಪ್ರೀತಿ",
    "Ayushman": "ಆಯುಷ್ಮಾನ್",
    "Saubhagya": "ಸೌಭ್ಯಾಗ್ಯ",
    "Shobhana": "ಶೋಭನ",
    "Atiganda": "ಅತಿಗಂಡ",
    "Sukarma": "ಸುಕರ್ಮ",
    "Dhriti": "ಧೃತಿ",
    "Shula": "ಶೂಲ",
    "Ganda": "ಗಂಡ",
    "Vriddhi": "ವೃದ್ಧಿ",
    "Dhruva": "ಧ್ರುವ",
    "Vyaghata": "ವ್ಯಾಘಾತ",
    "Harshana": "ಹರ್ಷಣ",
    "Vajra": "ವಜ್ರ",
    "Siddhi": "ಸಿದ್ಧಿ",
    "Vyatipata": "ವ್ಯತೀಪಾತ",
    "Variyana": "ವರೀಯಾನ್",
    "Parigha": "ಪರಿಘ",
    "Shiva": "ಶಿವ",
    "Siddha": "ಸಿದ್ಧ",
    "Sadhya": "ಸಾಧ್ಯ",
    "Shubha": "ಶುಭ",
    "Shukla": "ಶುಕ್ಲ",
    "Brahma": "ಬ್ರಹ್ಮ",
    "Indra": "ಇಂದ್ರ",
    "Vaidhriti": "ವೈಧೃತಿ",

    # Karanas
    "Kimstughna": "ಕಿಂಸ್ತುಘ್ನ",
    "Bava": "ಬವ",
    "Balava": "ಬಾಲವ",
    "Kaulava": "ಕೌಲವ",
    "Taitila": "ತೈತಿಲ",
    "Gara": "ಗರ",
    "Vanija": "ವಣಿಜ",
    "Vishti": "ವಿಷ್ಟಿ",
    "Shakuni": "ಶಕುನಿ",
    "Chatushpada": "ಚತುಷ್ಪಾದ",
    "Naga": "ನಾಗ",

    # Tithi/Paksha words
    "Krishna": "ಕೃಷ್ಣ",
    "Shukla": "ಶುಕ್ಲ",
    "Pratipada": "ಪ್ರತಿಪದೆ",
    "Dvitiya": "ದ್ವಿತೀಯ",
    "Tritiya": "ತೃತೀಯ",
    "Chaturthi": "ಚತುರ್ಥಿ",
    "Panchami": "ಪಂಚಮಿ",
    "Shashthi": "ಷಷ್ಠಿ",
    "Saptami": "ಸಪ್ತಮಿ",
    "Ashtami": "ಅಷ್ಟಮಿ",
    "Navami": "ನವಮಿ",
    "Dashami": "ದಶಮಿ",
    "Ekadashi": "ಏಕಾದಶಿ",
    "Dvadashi": "ದ್ವಾದಶಿ",
    "Trayodashi": "ತ್ರಯೋದಶಿ",
    "Chaturdashi": "ಚತುರ್ದಶಿ",
    "Purnima": "ಪೌರ್ಣಮಿ",
    "Amavasya": "ಅಮಾವಾಸ್ಯೆ",

    # Weekdays (English / Sanskrit)
    "Monday": "ಸೋಮವಾರ",
    "Tuesday": "ಮಂಗಳವಾರ",
    "Wednesday": "ಬುಧವಾರ",
    "Thursday": "ಗುರುವಾರ",
    "Friday": "ಶುಕ್ರವಾರ",
    "Saturday": "ಶನಿವಾರ",
    "Sunday": "ಭಾನುವಾರ",
    "Somavara": "ಸೋಮವಾರ",
    "Mangalavara": "ಮಂಗಳವಾರ",
    "Budhavara": "ಬುಧವಾರ",
    "Guruvara": "ಗುರುವಾರ",
    "Shukravara": "ಶುಕ್ರವಾರ",
    "Shanivara": "ಶನಿವಾರ",
    "Ravivara": "ರವಿವಾರ",

    # Ayanas
    "Uttarayana": "ಉತ್ತರಾಯಣ",
    "Dakshinayana": "ದಕ್ಷಿಣಾಯನ",

    # Rutus (Seasons)
    "Vasanta": "ವಸಂತ",
    "Grishma": "ಗ್ರೀಷ್ಮ",
    "Varsha": "ವರ್ಷ",
    "Sharad": "ಶರದ್",
    "Hemanta": "ಹೇಮಂತ",
    "Shishira": "ಶಿಶಿರ",

    # Months (Masas)
    "Chaitra": "ಚೈತ್ರ",
    "Vaishakha": "ವೈಶಾಖ",
    "Jyeshtha": "ಜ್ಯೇಷ್ಠ",
    "Ashadha": "ಆಷಾಢ",
    "Shravana": "ಶ್ರಾವಣ",
    "Bhadrapada": "ಭಾದ್ರಪದ",
    "Ashvina": "ಆಶ್ವಯುಜ",
    "Kartika": "ಕಾರ್ತಿಕ",
    "Margashirsha": "ಮಾರ್ಗಶಿರ",
    "Pausha": "ಪುಷ್ಯ",
    "Magha": "ಮಾಘ",
    "Phalguna": "ಫಾಲ್ಗುಣ",
    "Adhika": "ಅಧಿಕ",

    # Samvatsaras
    "Prabhava": "ಪ್ರಭವ",
    "Vibhava": "ವಿಭವ",
    "Shukla": "ಶುಕ್ಲ",
    "Pramoduta": "ಪ್ರಮೋದೂತ",
    "Prajotpatti": "ಪ್ರಜೋತ್ಪತ್ತಿ",
    "Angirasa": "ಅಂಗಿರಸ",
    "Shrimukha": "ಶ್ರೀಮುಖ",
    "Bhava": "ಭಾವ",
    "Yuva": "ಯುವ",
    "Dhatu": "ಧಾತು",
    "Ishvara": "ಈಶ್ವರ",
    "Bahudhanya": "ಬಹುಧಾನ್ಯ",
    "Pramadi": "ಪ್ರಮಾದಿ",
    "Vikrama": "ವಿಕ್ರಮ",
    "Vrisha": "ವೃಷ",
    "Chitrabhanu": "ಚಿತ್ರಭಾನು",
    "Svabhanu": "ಸ್ವಭಾನು",
    "Tarana": "ತಾರಣ",
    "Parthiva": "ಪಾರ್ಥಿವ",
    "Vyaya": "ವ್ಯಯ",
    "Sarvajit": "ಸರ್ವಜಿತ್",
    "Sarvadhari": "ಸರ್ವಾಧಾರಿ",
    "Virodhi": "ವಿರೋಧಿ",
    "Vikruti": "ವಿಕೃತಿ",
    "Khara": "ಖರ",
    "Nandana": "ನಂದನ",
    "Vijaya": "ವಿಜಯ",
    "Jaya": "ಜಯ",
    "Manmatha": "ಮನ್ಮಥ",
    "Durmukhi": "ದುರ್ಮುಖಿ",
    "Hevilambi": "ಹೇವಿಲಂಬಿ",
    "Vilambi": "ವಿಲಂಬಿ",
    "Vikari": "ವಿಕಾರಿ",
    "Sharvari": "ಶಾರ್ವರಿ",
    "Plava": "ಪ್ಲವ",
    "Shubhakrut": "ಶುಭಕೃತ್",
    "Shobhakrut": "ಶೋಭಕೃತ್",
    "Krodhi": "ಕ್ರೋಧಿ",
    "Vishvavasu": "ವಿಶ್ವಾವಸು",
    "Parabhava": "ಪರಾಭವ",
    "Plavanga": "ಪ್ಲವಂಗ",
    "Kilaka": "ಕೀಲಕ",
    "Saumya": "ಸೌಮ್ಯ",
    "Sadharana": "ಸಾಧಾರಣ",
    "Virodhikrut": "ವಿರೋಧಿಕೃತ್",
    "Paridhavi": "ಪರಿದಾವಿ",
    "Ananda": "ಆನಂದ",
    "Rakshasa": "ರಾಕ್ಷಸ",
    "Nala": "ನಳ",
    "Pingala": "ಪಿಂಗಳ",
    "Kalayukta": "ಕಾಲಯುಕ್ತ",
    "Siddharthi": "ಸಿದ್ಧಾರ್ಥಿ",
    "Raudri": "ರೌದ್ರಿ",
    "Durmati": "ದುರ್ಮತಿ",
    "Dundubhi": "ದುಂದುಭಿ",
    "Rudhirodgari": "ರುಧಿರೋದ್ಗಾರಿ",
    "Raktakshi": "ರಕ್ತಾಕ್ಷಿ",
    "Krodhana": "ಕ್ರೋಧನ",
    "Akshaya": "ಅಕ್ಷಯ",

    # Muhurtas
    "Rahu Kalam": "ರಾಹುಕಾಲ",
    "Gulika Kalam": "ಗುಳಿಕ ಕಾಲ",
    "Yamaganda": "ಯಮಗಂಡ",
    "Abhijit Muhurta": "ಅಭಿಜಿತ್ ಮುಹೂರ್ತ",

    # Hora Period
    "day": "ಹಗಲು",
    "night": "ರಾತ್ರಿ",
}


def translate_string(text: str) -> str:
    # Localize "X min" remaining duration
    if text.endswith(" min"):
        num_part = text[:-4]
        return f"{num_part} ನಿಮಿಷ"

    if text in TRANSLATIONS:
        return TRANSLATIONS[text]

    words = text.split(" ")
    translated = []
    for word in words:
        translated.append(TRANSLATIONS.get(word, word))
    return " ".join(translated)


def localize_payload(payload: Any, lang: str) -> Any:
    if lang != "kan":
        return payload

    if isinstance(payload, dict):
        return {
            key: localize_payload(value, lang) for key, value in payload.items()
        }
    elif isinstance(payload, list):
        return [localize_payload(item, lang) for item in payload]
    elif isinstance(payload, str):
        return translate_string(payload)
    else:
        return payload
