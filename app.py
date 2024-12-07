from flask import Flask, request, render_template
import requests

app = Flask(__name__)

API_KEY = "ACCUWEATHER_API_KEY=DvTIGor3G9AjzPN8J2A9BpXgG8knkCRS"

# Пример координат
cities_coords = {
    "Москва": (55.7558, 37.6173),
    "Санкт-Петербург": (59.9343, 30.3351),
    "Новосибирск": (55.0084, 82.9357)
}

def get_location_key(lat, lon):
    location_url = "http://dataservice.accuweather.com/locations/v1/cities/geoposition/search"
    params = {"apikey": API_KEY, "q": f"{lat},{lon}"}
    try:
        response = requests.get(location_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("Key")
    except requests.RequestException:
        return None

def get_weather_forecast(location_key):
    if not location_key:
        return None
    forecast_url = f"http://dataservice.accuweather.com/forecasts/v1/hourly/12hour/{location_key}"
    params = {"apikey": API_KEY, "metric": "true"}
    try:
        response = requests.get(forecast_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.RequestException:
        return None

def check_bad_weather(temp, wind_speed, precip_prob):
    # Логика определения плохой погоды
    if temp < 0 or temp > 35:
        return True
    if wind_speed > 50:
        return True
    if precip_prob > 70:
        return True
    return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/check_route", methods=["POST"])
def check_route():
    start_point = request.form.get("start_point")
    end_point = request.form.get("end_point")

    start_coords = cities_coords.get(start_point)
    end_coords = cities_coords.get(end_point)

    if not start_coords or not end_coords:
        return "Не могу найти координаты для одного из введённых городов. Проверьте правильность названий."

    start_loc_key = get_location_key(*start_coords)
    end_loc_key = get_location_key(*end_coords)

    if not start_loc_key or not end_loc_key:
        return "Не удалось получить данные о локации. Попробуйте позже."

    start_forecast = get_weather_forecast(start_loc_key)
    end_forecast = get_weather_forecast(end_loc_key)

    if not start_forecast or not end_forecast:
        return "Ошибка при получении прогноза погоды. Попробуйте позже."

    start_weather = start_forecast[0]
    end_weather = end_forecast[0]

    start_temp = start_weather["Temperature"]["Value"]
    start_wind = start_weather["Wind"]["Speed"]["Value"]
    start_precip = start_weather["PrecipitationProbability"]

    end_temp = end_weather["Temperature"]["Value"]
    end_wind = end_weather["Wind"]["Speed"]["Value"]
    end_precip = end_weather["PrecipitationProbability"]

    start_bad = check_bad_weather(start_temp, start_wind, start_precip)
    end_bad = check_bad_weather(end_temp, end_wind, end_precip)

    start_status = "Плохая погода" if start_bad else "Хорошая погода"
    end_status = "Плохая погода" if end_bad else "Хорошая погода"

    result = (f"<h2>Результат:</h2>"
              f"<p><b>{start_point}</b>: Температура {start_temp}°C, ветер {start_wind} км/ч, осадки {start_precip}%. "
              f"Состояние: {start_status}.</p>"
              f"<p><b>{end_point}</b>: Температура {end_temp}°C, ветер {end_wind} км/ч, осадки {end_precip}%. "
              f"Состояние: {end_status}.</p>")

    return result

if __name__ == "__main__":
    app.run(debug=True)
