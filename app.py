from flask import Flask, request, render_template
import requests

app = Flask(__name__)

API_KEY = "DvTIGor3G9AjzPN8J2A9BpXgG8knkCRS"

cities_coords = {
    "Москва": (55.7558, 37.6173),
    "Санкт-Петербург": (59.9343, 30.3351),
    "Новосибирск": (55.0084, 82.9357)
}

def get_location_key(lat, lon):
    url = "http://dataservice.accuweather.com/locations/v1/cities/geoposition/search"
    params = {"apikey": API_KEY, "q": f"{lat},{lon}"}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        data = r.json()
        return data.get("Key")
    return None

def get_weather_forecast(location_key):
    if not location_key:
        return None
    url = f"http://dataservice.accuweather.com/forecasts/v1/hourly/12hour/{location_key}"
    params = {"apikey": API_KEY, "metric": "true", "details": "true"}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json()
    return None

def check_bad_weather(temp, wind_speed, precip_prob):
    if temp < 0 or temp > 35 or wind_speed > 50 or precip_prob > 70:
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
        return "Не могу найти координаты для этого города."

    start_key = get_location_key(*start_coords)
    end_key = get_location_key(*end_coords)

    if not start_key or not end_key:
        return "Не удалось получить данные о локации."

    start_forecast = get_weather_forecast(start_key)
    end_forecast = get_weather_forecast(end_key)

    if not start_forecast or not end_forecast:
        return "Ошибка получения прогноза. Попробуйте позже."

    start_weather = start_forecast[0]
    end_weather = end_forecast[0]

    try:
        start_temp = start_weather["Temperature"]["Value"]
        start_wind = start_weather["Wind"]["Speed"]["Value"]
        start_precip = start_weather["PrecipitationProbability"]

        end_temp = end_weather["Temperature"]["Value"]
        end_wind = end_weather["Wind"]["Speed"]["Value"]
        end_precip = end_weather["PrecipitationProbability"]
    except KeyError:
        return "Данные о погоде неполны. Попробуйте другой город или позже."

    start_bad = check_bad_weather(start_temp, start_wind, start_precip)
    end_bad = check_bad_weather(end_temp, end_wind, end_precip)

    return (f"<h2>Результат:</h2>"
            f"<p><b>{start_point}</b>: Темп {start_temp}°C, ветер {start_wind} км/ч, осадки {start_precip}%. "
            f"Состояние: {'Плохая' if start_bad else 'Хорошая'} погода.</p>"
            f"<p><b>{end_point}</b>: Темп {end_temp}°C, ветер {end_wind} км/ч, осадки {end_precip}%. "
            f"Состояние: {'Плохая' if end_bad else 'Хорошая'} погода.</p>")

if __name__ == "__main__":
    app.run(debug=True)
