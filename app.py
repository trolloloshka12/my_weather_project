from flask import Flask, request, render_template, redirect, url_for
from dash import Dash, dcc, html, Input, Output
import requests

API_KEY = "DvTIGor3G9AjzPN8J2A9BpXgG8knkCRS"

app = Flask(__name__)

# Интеграция Dash в Flask
dash_app = Dash(__name__, server=app, url_base_pathname='/dash/')
selected_cities = {"start": None, "end": None}  # Для хранения выбранных городов

# Функция для получения ключа локации
def get_location_key_by_name(city_name):
    url = "http://dataservice.accuweather.com/locations/v1/cities/search"
    params = {"apikey": API_KEY, "q": city_name}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        data = r.json()
        if data:
            return data[0].get("Key")
    return None

# Функция для получения прогноза погоды
def get_weather_forecast(location_key, interval="12hour"):
    if not location_key:
        return None
    url = f"http://dataservice.accuweather.com/forecasts/v1/hourly/{interval}/{location_key}"
    params = {"apikey": API_KEY, "metric": "true", "details": "true"}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json()
    return None

# Функция подготовки данных для графиков
def prepare_graph_data(location_key, interval="12hour"):
    forecast = get_weather_forecast(location_key, interval)
    if not forecast:
        return None
    times = [point["DateTime"] for point in forecast]
    temperatures = [point["Temperature"]["Value"] for point in forecast]
    wind_speeds = [point["Wind"]["Speed"]["Value"] for point in forecast]
    precip_probs = [point["PrecipitationProbability"] for point in forecast]
    return {"times": times, "temperatures": temperatures, "wind_speeds": wind_speeds, "precip_probs": precip_probs}

# Главная страница с вводом данных
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        selected_cities["start"] = request.form.get("start_point")
        selected_cities["end"] = request.form.get("end_point")
        return redirect(url_for('dash_page'))
    return render_template("index.html")

# Страница Dash для отображения графиков
@app.route("/dash/")
def dash_page():
    return dash_app.index()

# Настройка Dash
dash_app.layout = html.Div([
    html.H1("Прогноз погоды для маршрута"),
    html.Div([
        html.Button("12 часов", id="btn-12hour", n_clicks=0),
        html.Button("5 дней", id="btn-5day", n_clicks=0),
    ], style={"margin-bottom": "20px"}),
    html.Div(id="graphs-container"),
    html.Br(),
    html.A("Вернуться на главную", href="/", style={
        "display": "inline-block",
        "padding": "10px 20px",
        "background-color": "#007BFF",
        "color": "white",
        "text-decoration": "none",
        "border-radius": "5px",
        "font-size": "16px",
    })
])

# Callback для обновления графиков
@dash_app.callback(
    Output('graphs-container', 'children'),
    [Input('btn-12hour', 'n_clicks'), Input('btn-5day', 'n_clicks')]
)
def update_graphs(n_clicks_12hour, n_clicks_5day):
    # Определяем интервал на основе нажатий
    if not n_clicks_12hour:
        n_clicks_12hour = 0
    if not n_clicks_5day:
        n_clicks_5day = 0
    interval = "12hour" if n_clicks_12hour > n_clicks_5day else "5day"

    # Получаем данные для начального и конечного города
    start_city = selected_cities["start"]
    end_city = selected_cities["end"]
    start_data = prepare_graph_data(get_location_key_by_name(start_city), interval)
    end_data = prepare_graph_data(get_location_key_by_name(end_city), interval)

    if not start_data or not end_data:
        return [html.Div("Не удалось получить данные для одного или обоих городов.")]

    return [
        dcc.Graph(
            figure={
                "data": [
                    {
                        "x": start_data["times"],
                        "y": start_data["temperatures"],
                        "type": "line",
                        "name": start_city,
                        "hovertemplate": "Город: {}<br>Температура: %{y}°C<br>Время: %{x}<extra></extra>".format(start_city),
                    },
                    {
                        "x": end_data["times"],
                        "y": end_data["temperatures"],
                        "type": "line",
                        "name": end_city,
                        "hovertemplate": "Город: {}<br>Температура: %{y}°C<br>Время: %{x}<extra></extra>".format(end_city),
                    },
                ],
                "layout": {"title": "Температура"}
            }
        ),
        dcc.Graph(
            figure={
                "data": [
                    {
                        "x": start_data["times"],
                        "y": start_data["wind_speeds"],
                        "type": "line",
                        "name": start_city,
                        "hovertemplate": "Город: {}<br>Скорость ветра: %{y} км/ч<br>Время: %{x}<extra></extra>".format(start_city),
                    },
                    {
                        "x": end_data["times"],
                        "y": end_data["wind_speeds"],
                        "type": "line",
                        "name": end_city,
                        "hovertemplate": "Город: {}<br>Скорость ветра: %{y} км/ч<br>Время: %{x}<extra></extra>".format(end_city),
                    },
                ],
                "layout": {"title": "Скорость ветра"}
            }
        ),
        dcc.Graph(
            figure={
                "data": [
                    {
                        "x": start_data["times"],
                        "y": start_data["precip_probs"],
                        "type": "line",
                        "name": start_city,
                        "hovertemplate": "Город: {}<br>Вероятность осадков: %{y}%<br>Время: %{x}<extra></extra>".format(start_city),
                    },
                    {
                        "x": end_data["times"],
                        "y": end_data["precip_probs"],
                        "type": "line",
                        "name": end_city,
                        "hovertemplate": "Город: {}<br>Вероятность осадков: %{y}%<br>Время: %{x}<extra></extra>".format(end_city),
                    },
                ],
                "layout": {"title": "Вероятность осадков"}
            }
        ),
    ]

if __name__ == "__main__":
    app.run(debug=True)
