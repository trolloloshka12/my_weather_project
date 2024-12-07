from flask import Flask, request, render_template
import requests

app = Flask(__name__)

API_KEY = "DvTIGor3G9AjzPN8J2A9BpXgG8knkCRS"

def get_location_key_by_name(city_name):
    url = "http://dataservice.accuweather.com/locations/v1/cities/search"
    params = {
        "apikey": API_KEY,
        "q": city_name
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        data = r.json()
        if data:
            return data[0].get("Key")
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

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        start_point = request.form.get("start_point")
        end_point = request.form.get("end_point")

        start_key = get_location_key_by_name(start_point)
        end_key = get_location_key_by_name(end_point)

        if not start_key or not end_key:
            return "Не могу найти координаты для этого города. Попробуйте другой город или проверьте написание."

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

        return render_template(
            "results.html",
            start_point=start_point,
            start_temp=start_temp,
            start_wind=start_wind,
            start_precip=start_precip,
            start_status="Плохая погода" if start_bad else "Хорошая погода",
            end_point=end_point,
            end_temp=end_temp,
            end_wind=end_wind,
            end_precip=end_precip,
            end_status="Плохая погода" if end_bad else "Хорошая погода"
        )

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
