# Spotter Backend

Backend sencillo en Django + Django REST Framework para planificar viajes.

## Instalacion

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

Configura `OPENROUTESERVICE_API_KEY` en `.env` antes de probar rutas reales.

## Endpoint

`POST /api/trips/plan/`

```json
{
  "current_location": "Cali, Colombia",
  "pickup_location": "Miami, FL",
  "dropoff_location": "Atlanta, GA",
  "current_cycle_used": 20
}
```

La ruta se calcula con OpenRouteService usando:

- geocoding para `current_location`, `pickup_location` y `dropoff_location`
- directions para `current_location -> pickup_location -> dropoff_location`
- distancia total, duracion total, coordenadas y polyline de la ruta
