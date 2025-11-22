#!/usr/bin/env python3
import sys
import requests
import json
import argparse

# Výchozí URL agenta (předpokládáme, že běží na localhostu na portu 5005)
AGENT_URL = "http://localhost:5005"

def get_status():
    try:
        response = requests.get(f"{AGENT_URL}/status")
        if response.status_code == 200:
            data = response.json()
            print(f"Stav: {data['status']}")
            print("Konfigurace:")
            for key, value in data['config'].items():
                print(f"  {key}: {value}")
        else:
            print(f"Chyba: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("Nelze se připojit k agentovi. Běží kontejner agent-real-estate?")

def start_agent():
    try:
        response = requests.post(f"{AGENT_URL}/start")
        print(response.json().get("message", "Chyba"))
    except Exception as e:
        print(f"Chyba: {e}")

def stop_agent():
    try:
        response = requests.post(f"{AGENT_URL}/stop")
        print(response.json().get("message", "Chyba"))
    except Exception as e:
        print(f"Chyba: {e}")

def run_now():
    try:
        response = requests.post(f"{AGENT_URL}/run-now")
        print(response.json().get("message", "Chyba"))
    except Exception as e:
        print(f"Chyba: {e}")

def update_config(location=None, min_area=None, interval=None):
    data = {}
    if location:
        data["location"] = location
    if min_area:
        data["min_area"] = min_area
    if interval:
        data["interval"] = interval
        
    if not data:
        print("Nebyly zadány žádné parametry ke změně.")
        return

    try:
        response = requests.post(f"{AGENT_URL}/config", json=data)
        if response.status_code == 200:
            print(response.json().get("message", "OK"))
            print("Nová konfigurace:")
            for key, value in response.json().get("config", {}).items():
                print(f"  {key}: {value}")
        else:
            print(f"Chyba: {response.json().get('error', 'Neznámá chyba')}")
    except Exception as e:
        print(f"Chyba: {e}")

def send_prompt(message):
    try:
        response = requests.post(f"{AGENT_URL}/prompt", json={"message": message})
        if response.status_code == 200:
            data = response.json()
            print(f"Agent: {data.get('message')}")
            if "intent" in data:
                # Debug info (volitelné)
                # print(f"Debug (Intent): {data['intent']}")
                pass
        else:
            print(f"Chyba: {response.json().get('error', 'Neznámá chyba')}")
    except Exception as e:
        print(f"Chyba: {e}")

def main():
    parser = argparse.ArgumentParser(description="CLI pro ovládání Real Estate Agenta")
    subparsers = parser.add_subparsers(dest="command", help="Příkaz")

    # Příkaz status
    subparsers.add_parser("status", help="Zobrazit stav agenta")

    # Příkaz start
    subparsers.add_parser("start", help="Spustit agenta")

    # Příkaz stop
    subparsers.add_parser("stop", help="Pozastavit agenta")

    # Příkaz run-now
    subparsers.add_parser("run-now", help="Okamžitě spustit vyhledávání")

    # Příkaz prompt (chat)
    prompt_parser = subparsers.add_parser("prompt", help="Poslat agentovi instrukci v přirozeném jazyce")
    prompt_parser.add_argument("message", help="Zpráva pro agenta (v uvozovkách)")

    # Příkaz config
    config_parser = subparsers.add_parser("config", help="Změnit konfiguraci")
    config_parser.add_argument("--location", help="Lokalita (např. Praha)")
    config_parser.add_argument("--min-area", type=int, help="Minimální plocha v m2")
    config_parser.add_argument("--interval", type=int, help="Interval v sekundách")

    args = parser.parse_args()

    if args.command == "status":
        get_status()
    elif args.command == "start":
        start_agent()
    elif args.command == "stop":
        stop_agent()
    elif args.command == "run-now":
        run_now()
    elif args.command == "prompt":
        send_prompt(args.message)
    elif args.command == "config":
        update_config(args.location, args.min_area, args.interval)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
