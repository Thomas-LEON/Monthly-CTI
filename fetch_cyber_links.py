#!/usr/bin/env python3
"""Script de récupération mensuelle des URLs Silobreaker pour le rapport Cyber."""

import base64
import calendar
import datetime
import hashlib
import hmac
import json
import os
import urllib.parse
import urllib.request

# --- Configuration & Clés API ---
# Utilise les variables d'environnement (GitHub Secrets) ou des valeurs par défaut
API_KEY = os.getenv("SILOBREAKER_API_KEY", "c70tj2cfo7oatj6ox0li")
SHARED_KEY = os.getenv("SILOBREAKER_SHARED_KEY", "thwvr5huc2eb2p3bln0h")
BASE_URL = "https://api.silobreaker.com/"
PAGE_SIZE = 100

# --- Détermination automatique de la période (Mois précédent) ---
today = datetime.date.today()
first_day_current_month = today.replace(day=1)
last_day_prev_month = first_day_current_month - datetime.timedelta(days=1)
first_day_prev_month = last_day_prev_month.replace(day=1)

FROM_DATE = first_day_prev_month.strftime("%Y-%m-%d")
TO_DATE = last_day_prev_month.strftime("%Y-%m-%d")
MONTH_LABEL = last_day_prev_month.strftime("%B %Y").upper()

OUTPUT_FILENAME = (
    f"CYBER-REPORT-SOURCES-{last_day_prev_month.strftime('%m-%Y')}.md"
)

# --- Requêtes Silobreaker ciblées par Slide ---
SLIDE_QUERIES = {
    "SLIDE 1 - CYBER RISK LANDSCAPE (Metrics & KPIs)": [
        '(bank OR banking OR "financial sector") AND ("mean time to exploit" OR "patch time" OR "time to remediate" OR "vulnerability remediation") AND (report OR benchmark OR statistics)',
        '(bank OR "financial services") AND (ransomware OR "extortion" OR "data breach cost") AND ("YoY" OR "average cost" OR "spike" OR "million")',
        '("third-party risk" OR "supply chain" OR "vendor risk") AND (bank OR "financial institutions") AND ("critical vulnerabilities" OR "DORA" OR "concentration risk")',
        '("Agentic AI" OR "Shadow AI" OR "autonomous threat" OR "breakout speed") AND (bank OR "financial sector" OR "enterprise")',
    ],
    "SLIDE 2 - CASE STUDY (Bank Cyber Extortion & Attack Chain)": [
        'INTITLE (bank OR "financial institution" OR "banking group") AND ("data extortion" OR "ransomware" OR "breach" OR "exfiltration" OR "claimed responsibility") AND NOT (crypto OR bitcoin OR DeFi)',
        '(entitytype:"ThreatActor" OR "threat actor" OR "Lapsus$" OR "ransomware group") AND (bank OR "financial target") AND ("initial access" OR "kill chain" OR "lateral movement" OR "extortion")',
    ],
    "SLIDE 3 - EXTERNAL THREAT LANDSCAPE (Trends & Proof Points)": [
        '("ECB" OR "European Central Bank" OR "DORA" OR "NIS2" OR "regulatory directive") AND (cyber OR AI OR "ICT risk" OR audit OR compliance OR fine)',
        '("AI software supply chain" OR "prompt injection" OR "sandbox breakout" OR "model poisoning" OR "npm package" OR "state-sponsored") AND (cyber OR attack OR vulnerability)',
        '("MSP" OR "Managed Service Provider" OR "identity abuse" OR "credential theft" OR "privilege escalation") AND (bank OR "financial sector")',
    ],
}

# --- Fonctions API Silobreaker ---


def _build_full_url(relative_url: str) -> str:
    separator = "&" if "?" in relative_url else "?"
    return f"{BASE_URL}{relative_url}{separator}source=ApiKey"


def _sign(url: str, verb: str = "GET") -> str:
    full_url = _build_full_url(url)
    message = f"{verb} {full_url}".encode()
    digest = base64.b64encode(
        hmac.new(SHARED_KEY.encode(), message, digestmod=hashlib.sha1).digest()
    ).decode()
    return f"{full_url}&apiKey={API_KEY}&digest={urllib.parse.quote(digest)}"


def api_get(relative_url: str) -> dict:
    signed_url = _sign(relative_url)
    req = urllib.request.Request(
        signed_url, headers={"User-Agent": "CyberReportFetcher/1.0"}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def search_documents(query: str, from_date: str, to_date: str, page_size: int):
    full_query = f'{query} AND fromdate:"{from_date}" AND todate:"{to_date}"'
    params = urllib.parse.urlencode(
        {"query": full_query, "pageSize": page_size}
    )
    return api_get(f"v2/documents/search?{params}")


# --- Exécution principale ---


def main():
    print(f"=== Extraction Silobreaker pour la période : {FROM_DATE} au {TO_DATE} ===")
    results_by_slide = {}
    total_found = 0

    for section_title, queries in SLIDE_QUERIES.items():
        print(f"\n--- Recherche pour : {section_title} ---")
        section_urls = set()

        for idx, q in enumerate(queries, 1):
            try:
                content = search_documents(q, FROM_DATE, TO_DATE, PAGE_SIZE)
                items = content.get("Items", [])
                urls = {
                    doc.get("SourceUrl")
                    for doc in items
                    if doc.get("SourceUrl")
                }
                print(f"  [Requête {idx}/{len(queries)}] {len(urls)} URLs trouvées")
                section_urls.update(urls)
            except Exception as e:
                print(f"  [Requête {idx}/{len(queries)}] Erreur : {e}")

        results_by_slide[section_title] = sorted(section_urls)
        total_found += len(section_urls)

    # --- Génération du Markdown de sortie ---
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as md:
        md.write(f"# Cyber Threat Intelligence Sources - {MONTH_LABEL}\n")
        md.write(
            f"**Période d'analyse :** `{FROM_DATE}` au `{TO_DATE}`  \n"
        )
        md.write(f"**Total URLs extraites :** `{total_found}`\n\n")
        md.write(
            "> Ce document est prêt à être injecté dans Notebook Gemini pour la génération des slides.\n\n"
        )
        md.write("---\n\n")

        for section_title, urls in results_by_slide.items():
            md.write(f"## {section_title}\n\n")
            if urls:
                for url in urls:
                    md.write(f"- {url}\n")
            else:
                md.write(
                    "*Aucune source directe trouvée pour cette catégorie ce mois-ci.*\n"
                )
            md.write("\n---\n\n")

    print(f"\nTerminé ! Fichier généré avec succès : {OUTPUT_FILENAME}")


if __name__ == "__main__":
    main()
