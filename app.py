from flask import Flask
from dash import Dash, dcc, html, Input, Output, State
from dash.dependencies import ALL
from dash.dash_table import DataTable
import requests
import plotly.graph_objs as go
import dash_leaflet as dl
import time
import logging

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WeatherLogger")

app = Flask(__name__)

API_KEY = "WKP4UIOGuSG1BpMqHmWlfeqJyzR5uYUd"

# Вспомогательные функции для API

def get_location_key_by_name(city_name):
    """Получение ключа локации для города"""
    url = "http://dataservice.accuweather.com/locations/v1/cities/search"
    params = {"apikey": API_KEY, "q": city_name}
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            data = r.json()
            if data:
                return data[0].get("Key")
        elif r.status_code == 503:
            time.sleep(5)
            return get_location_key_by_name(city_name)
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе ключа города {city_name}: {e}")
    return None

def get_location_coordinates(city_name):
    """Получение координат для города"""
    url = f"http://dataservice.accuweather.com/locations/v1/cities/search"
    params = {"apikey": API_KEY, "q": city_name}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]["GeoPosition"]["Latitude"], data[0]["GeoPosition"]["Longitude"]
    except Exception as e:
        logger.error(f"Ошибка при запросе координат для {city_name}: {e}")
    return None

def get_weather_forecast(location_key, forecast_type='12h'):
    """Получение прогноза погоды для города"""
    endpoints = {
        '12h': f"http://dataservice.accuweather.com/forecasts/v1/hourly/12hour/{location_key}",
        '1d': f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}",
        '5d': f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}"
    }
    url = endpoints.get(forecast_type)
    params = {"apikey": API_KEY, "metric": "true", "details": "true"}
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            return r.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе прогноза для ключа {location_key}: {e}")
    return None

def prepare_graph_data(weather_data):
    """Подготовка данных для графиков"""
    if "DailyForecasts" in weather_data:
        forecasts = weather_data["DailyForecasts"]
        times = [f["Date"] for f in forecasts]
        temperatures = [(f["Temperature"]["Minimum"]["Value"] + f["Temperature"]["Maximum"]["Value"]) / 2 for f in forecasts]
        wind_speeds = [f.get("Day", {}).get("Wind", {}).get("Speed", {}).get("Value", 0) for f in forecasts]
        precip_probs = [f.get("Day", {}).get("PrecipitationProbability", 0) for f in forecasts]
    else:
        forecasts = weather_data
        times = [f["DateTime"] for f in forecasts]
        temperatures = [f["Temperature"]["Value"] for f in forecasts]
        wind_speeds = [f["Wind"]["Speed"]["Value"] for f in forecasts]
        precip_probs = [f["PrecipitationProbability"] for f in forecasts]
    return times, temperatures, wind_speeds, precip_probs

# Настройка интерфейса Dash
dash_app = Dash(__name__, server=app, url_base_pathname='/')

dash_app.layout = html.Div([
    html.Div(style={'textAlign': 'center', 'marginBottom': '20px'}, children=[
        html.H1("Погодный прогноз по маршруту", style={'color': '#007BFF', 'fontSize': '32px'}),
        html.P("Планируйте свои путешествия с учётом погодных условий!", style={'color': '#555'})
    ]),
    html.Div(style={'padding': '10px', 'border': '1px solid #ccc', 'borderRadius': '5px', 'marginBottom': '20px'}, children=[
        html.H2("Маршрут", style={'color': '#333'}),
        html.Label("Начальный город:", style={'fontWeight': 'bold'}),
        dcc.Input(id='start-city', type='text', placeholder='Введите начальный город', debounce=True, style={'marginBottom': '10px'}),
        html.Label("Промежуточные остановки:", style={'fontWeight': 'bold'}),
        html.Div(id='city-inputs-container', style={'marginBottom': '10px'}),
        html.Button('Добавить остановку', id='add-city-button', n_clicks=0, style={'marginBottom': '10px'}),
        html.Label("Конечный город:", style={'fontWeight': 'bold'}),
        dcc.Input(id='end-city', type='text', placeholder='Введите конечный город', debounce=True, style={'marginBottom': '20px'}),
    ]),
    html.Div(style={'padding': '10px', 'border': '1px solid #ccc', 'borderRadius': '5px', 'marginBottom': '20px'}, children=[
        html.H2("Настройки прогноза", style={'color': '#333'}),
        html.Label("Выберите временной интервал:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='time-interval-dropdown',
            options=[
                {'label': '12 часов', 'value': '12h'},
                {'label': '1 день', 'value': '1d'},
                {'label': '5 дней', 'value': '5d'}
            ],
            value='12h',
            clearable=False,
            style={'marginBottom': '10px'}
        ),
        html.Label("Выберите параметры для отображения:", style={'fontWeight': 'bold'}),
        dcc.Checklist(
            id='parameters-checklist',
            options=[
                {'label': 'Температура', 'value': 'temperature'},
                {'label': 'Осадки', 'value': 'precipitation'},
                {'label': 'Скорость ветра', 'value': 'wind'}
            ],
            value=['temperature', 'precipitation'],  # Выбраны по умолчанию
            inline=True,
            style={'marginBottom': '20px'}
        ),
    ]),
    html.Div(style={'textAlign': 'center', 'marginBottom': '20px'}, children=[
        html.Button('Показать прогноз', id='submit-button', n_clicks=0, style={'padding': '10px 20px', 'backgroundColor': '#007BFF', 'color': '#fff', 'border': 'none', 'borderRadius': '5px'})
    ]),
    html.Div(id='error-message', style={'color': 'red', 'marginTop': '10px', 'textAlign': 'center'}),
    html.Div(style={'marginBottom': '20px'}, children=[
        dcc.Graph(id='route-weather-graph')
    ]),
    html.Div(style={'padding': '10px', 'border': '1px solid #ccc', 'borderRadius': '5px', 'marginBottom': '20px'}, children=[
        html.H2("Таблица прогноза погоды", style={'color': '#333'}),
        DataTable(id='weather-table', style_table={'overflowX': 'auto'})
    ]),
    html.Div(style={'padding': '10px', 'border': '1px solid #ccc', 'borderRadius': '5px'}, children=[
        html.H2("Маршрут на карте", style={'color': '#333'}),
        dl.Map(id="route-map", style={'width': '100%', 'height': '500px'}, center=[55.751244, 37.618423], zoom=5, children=[
            dl.TileLayer(),
            dl.LayerGroup(id="map-layers")
        ])
    ])
])


# Коллбэки для взаимодействия пользователя

@dash_app.callback(
    Output('city-inputs-container', 'children'),
    Input('add-city-button', 'n_clicks'),
    State('city-inputs-container', 'children')
)
def add_city_input(n_clicks, existing_inputs):
    """Добавление промежуточных остановок"""
    if n_clicks == 0:
        return []
    new_input = dcc.Input(
        id={'type': 'city-input', 'index': n_clicks},
        type='text',
        placeholder=f'Остановка {n_clicks}',
        debounce=True,
        style={"margin-bottom": "10px"}
    )
    return existing_inputs + [new_input]

@dash_app.callback(
    [Output('route-weather-graph', 'figure'),
     Output('weather-table', 'data'),
     Output('weather-table', 'columns'),
     Output('error-message', 'children'),
     Output('map-layers', 'children')],
    [Input('submit-button', 'n_clicks')],
    [State('start-city', 'value'),
     State('end-city', 'value'),
     State({'type': 'city-input', 'index': ALL}, 'value'),
     State('time-interval-dropdown', 'value'),
     State('parameters-checklist', 'value')]
)
def update_graph_table_map(n_clicks, start_city, end_city, intermediate_cities, forecast_type, selected_params):
    """Обновление графиков, таблиц и карты"""
    if n_clicks == 0:
        return {}, [], [], "", []

    all_cities = [start_city.strip()] + [city.strip() for city in intermediate_cities if city and city.strip()] + [end_city.strip()]
    all_cities = [city for city in all_cities if city]

    if len(all_cities) < 2:
        return {}, [], [], "Введите начальный и конечный города.", []

    weather_data = {}
    errors = []
    map_markers = []

    for city in all_cities:
        try:
            location_key = get_location_key_by_name(city)
            if not location_key:
                errors.append(f"Не удалось найти город '{city}'.")
                continue

            forecast = get_weather_forecast(location_key, forecast_type)
            if not forecast:
                errors.append(f"Не удалось получить прогноз для '{city}'.")
                continue

            weather_data[city] = prepare_graph_data(forecast)
            location_data = get_location_coordinates(city)
            if location_data:
                latitude, longitude = location_data
                popup_content = f"{city}: Температура {forecast['DailyForecasts'][0]['Temperature']['Maximum']['Value']}°C"
                map_markers.append(dl.Marker(position=[latitude, longitude], children=[dl.Popup(popup_content)]))
        except Exception as e:
            errors.append(f"Ошибка обработки города {city}: {str(e)}")

    if not weather_data:
        return {}, [], [], " ".join(errors), []

    figure = {'data': [], 'layout': {'title': 'Прогноз погоды', 'xaxis': {'title': 'Время'}}}
    table_data = []
    columns = [
        {'name': 'Город', 'id': 'city'},
        {'name': 'Дата/Время', 'id': 'datetime'},
        {'name': 'Температура (°C)', 'id': 'temperature'},
        {'name': 'Скорость ветра (км/ч)', 'id': 'wind'},
        {'name': 'Осадки (%)', 'id': 'precipitation'}
    ]

    for city, data in weather_data.items():
        times, temperatures, wind_speeds, precip_probs = data
        if 'temperature' in selected_params:
            figure['data'].append(go.Scatter(x=times, y=temperatures, mode='lines+markers', name=f'Температура ({city})'))
        if 'precipitation' in selected_params:
            figure['data'].append(go.Scatter(x=times, y=precip_probs, mode='lines+markers', name=f'Осадки ({city})'))
        if 'wind' in selected_params:
            figure['data'].append(go.Scatter(x=times, y=wind_speeds, mode='lines+markers', name=f'Скорость ветра ({city})'))

        for i, time in enumerate(times):
            table_data.append({
                'city': city,
                'datetime': time,
                'temperature': temperatures[i],
                'wind': wind_speeds[i],
                'precipitation': precip_probs[i]
            })

    map_layers = map_markers if len(map_markers) <= 1 else [dl.Polyline(positions=[[m.position[0], m.position[1]] for m in map_markers], color="blue"), *map_markers]

    return figure, table_data, columns, " ".join(errors), map_layers

if __name__ == "__main__":
    app.run(debug=True)
