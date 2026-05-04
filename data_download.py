import os
import databento as db
from dotenv import load_dotenv

load_dotenv()

client = db.Historical(os.environ["DATABENTO_API_KEY"])

# To zapytanie TYLKO wycenia, nie pobiera i nie zabiera kredytów
cost = client.metadata.get_cost(
    dataset="GLBX.MDP3",
    symbols="NQ.c.0",
    schema="trades",
    stype_in="continuous",
    start="2025-09-15",
    end="2026-05-04"
)

print(f"Szacowany koszt: {cost} USD")




# Konfiguracja zapytania
dataset = "GLBX.MDP3"
symbol = "NQ.c.0"
start_date = "2025-09-15"  # Zmień na swój zakres
end_date = "2026-05-04"    # Zrób mniejszy krok na próbę

print("Pobieranie danych...")

# Metoda pobierania bezpośrednio do pliku
client.timeseries.get_range(
    dataset=dataset,
    symbols=symbol,
    schema="trades",
    stype_in="continuous", # Kluczowe dla NQ.c.0
    start=start_date,
    end=end_date,
    path="nq_trades_data.dbn.zst" # Zapisze skompresowany plik
)

print("Gotowe! Plik nq_trades_data.dbn.zst został zapisany.")
