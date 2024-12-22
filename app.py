from flask import Flask, request, render_template
from dash import Dash, dcc, html, Input, Output, State
from dash.dependencies import ALL
from dash.dash_table import DataTable
import requests
import plotly.graph_objs as go
import time
import logging

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Убедитесь, что здесь установлен ваш реальный API-ключ
API_KEY = "WKP4UIOGuSG1BpMqHmWlfeqJyzR5uYUd"


def get_location_key_by_name(city_name):
    """Получение ключа локации для заданного города"""
    url = "http://dataservice.accuweather.com/locations/v1/cities/search"
    params = {
        "apikey": API_KEY,
        "q": city_name
    }
    try:
        r = requests.get(url, params=params)
        logger.info(f"Запрос к API: {r.url}")
        if r.status_code == 200:
            data = r.json()
            if data:
                return data[0].get("Key")

        if r.status_code == 401:
            logger.error("Ошибка авторизации: Проверьте API_KEY.")
        elif r.status_code == 503:
            logger.warning("Сервис AccuWeather недоступен. Повторяем запрос...")
            time.sleep(5)
            return get_location_key_by_name(city_name)
        else:
            logger.error(f"Ошибка: Не удалось найти ключ для города '{city_name}'.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса для города '{city_name}': {e}")
    return None


def get_weather_forecast(location_key, forecast_type='12h', retries=3):
    """
    Получение прогноза погоды для заданного ключа локации.

    :param location_key: str, ключ локации AccuWeather
    :param forecast_type: str, тип прогноза ('12h', '1d', '5d')
    :param retries: int, количество повторных попыток в случае ошибки
    :return: list, данные прогноза
    """
    if not location_key:
        logger.error("Ключ локации отсутствует.")
        return None

    if retries <= 0:
        logger.error("Превышено количество повторных попыток.")
        return None

    if forecast_type == '12h':
        url = f"http://dataservice.accuweather.com/forecasts/v1/hourly/12hour/{location_key}"
    elif forecast_type in ['1d', '5d']:
        days = forecast_type[0]
        url = f"http://dataservice.accuweather.com/forecasts/v1/daily/{days}day/{location_key}"
    else:
        logger.error(f"Неверный тип прогноза: {forecast_type}.")
        return None

    params = {
        "apikey": API_KEY,
        "metric": "true",
        "details": "true"
    }

    try:
        r = requests.get(url, params=params)
        logger.info(f"Запрос к API: {r.url}")

        if r.status_code == 200:
            return r.json()

        if r.status_code == 503:
            logger.warning("Сервис недоступен. Повторяем запрос...")
            time.sleep(5)
            return get_weather_forecast(location_key, forecast_type, retries - 1)

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса для ключа '{location_key}': {e}")
    return None


def prepare_graph_data(weather_data):
    """Подготовка данных для графиков"""
    if "DailyForecasts" in weather_data:  # Данные для дневного прогноза
        forecasts = weather_data["DailyForecasts"]
        times = [forecast["Date"] for forecast in forecasts]
        temperatures = [(forecast["Temperature"]["Minimum"]["Value"] + forecast["Temperature"]["Maximum"]["Value"]) / 2
                        for forecast in forecasts]
        wind_speeds = [forecast.get("Day", {}).get("Wind", {}).get("Speed", {}).get("Value", 0) for forecast in
                       forecasts]
        precip_probs = [forecast.get("Day", {}).get("PrecipitationProbability", 0) for forecast in forecasts]
    else:  # Данные для почасового прогноза
        forecasts = weather_data
        times = [forecast["DateTime"] for forecast in forecasts]
        temperatures = [forecast["Temperature"]["Value"] for forecast in forecasts]
        wind_speeds = [forecast["Wind"]["Speed"]["Value"] for forecast in forecasts]
        precip_probs = [forecast["PrecipitationProbability"] for forecast in forecasts]

    return times, temperatures, wind_speeds, precip_probs


# Интеграция Dash
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
dash_app = Dash(__name__, server=app, url_base_pathname='/', external_stylesheets=external_stylesheets)

dash_app.layout = html.Div([
    html.H1("Погодный прогноз по маршруту"),
    html.Div([
        html.Label("Начальный город:"),
        dcc.Input(id='start-city', type='text', placeholder='Введите начальный город', debounce=True, style={'margin-bottom': '10px'}),
        html.Label("Промежуточные остановки:"),
        html.Div(id='city-inputs-container', style={'margin-bottom': '10px'}),
        html.Button('Добавить остановку', id='add-city-button', n_clicks=0, style={'margin-bottom': '10px'}),
        html.Label("Конечный город:"),
        dcc.Input(id='end-city', type='text', placeholder='Введите конечный город', debounce=True, style={'margin-bottom': '20px'})
    ], style={'margin-bottom': '20px'}),
    html.Label("Выберите временной интервал:"),
    dcc.Dropdown(
        id='time-interval-dropdown',
        options=[
            {'label': '12 часов', 'value': '12h'},
            {'label': '1 день', 'value': '1d'},
            {'label': '5 дней', 'value': '5d'}
        ],
        value='12h',
        clearable=False,
        style={'margin-bottom': '20px'}
    ),
    html.Label("Выберите параметры для отображения:"),
    dcc.Checklist(
        id='parameters-checklist',
        options=[
            {'label': 'Температура', 'value': 'temperature'},
            {'label': 'Осадки', 'value': 'precipitation'},
            {'label': 'Скорость ветра', 'value': 'wind'}
        ],
        value=['temperature', 'precipitation'],  # Выбраны по умолчанию
        inline=True,
        style={'margin-bottom': '20px'}
    ),
    html.Button('Показать прогноз', id='submit-button', n_clicks=0),
    html.Div(id='error-message', style={'color': 'red', 'margin-top': '10px'}),
    dcc.Graph(id='route-weather-graph'),
    html.Div([
        html.H2("Таблица прогноза погоды"),
        DataTable(id='weather-table', style_table={'overflowX': 'auto'})
    ], style={'margin-top': '20px'})
])


@dash_app.callback(
    Output('city-inputs-container', 'children'),
    Input('add-city-button', 'n_clicks'),
    State('city-inputs-container', 'children')
)
def add_city_input(n_clicks, existing_inputs):
    if n_clicks == 0:
        return []
    new_input = dcc.Input(
        id={'type': 'city-input', 'index': n_clicks},
        type='text',
        placeholder=f'Остановка {n_clicks}',
        debounce=True
    )
    return existing_inputs + [new_input]


@dash_app.callback(
    [Output('route-weather-graph', 'figure'),
     Output('weather-table', 'data'),
     Output('weather-table', 'columns'),
     Output('error-message', 'children')],
    [Input('submit-button', 'n_clicks')],
    [State('start-city', 'value'),
     State('end-city', 'value'),
     State({'type': 'city-input', 'index': ALL}, 'value'),
     State('time-interval-dropdown', 'value'),
     State('parameters-checklist', 'value')]
)
def update_graph_and_table(n_clicks, start_city, end_city, intermediate_cities, forecast_type, selected_params):
    if n_clicks == 0:
        return {}, [], [], ""

    all_cities = [start_city.strip()] + \
                 [city.strip() for city in intermediate_cities if city and city.strip()] + \
                 [end_city.strip()]
    all_cities = [city for city in all_cities if city]

    if len(all_cities) < 2:
        return {}, [], [], "Введите начальный и конечный города."

    weather_data = {}
    errors = []

    for city in all_cities:
        try:
            location_key = get_location_key_by_name(city)
            if not location_key:
                errors.append(f"Не удалось найти город '{city}'.")
                continue

            forecast = get_weather_forecast(location_key, forecast_type)
            if forecast:
                weather_data[city] = prepare_graph_data(forecast)
            else:
                errors.append(f"Не удалось получить прогноз для '{city}'.")

        except Exception as e:
            errors.append(f"Ошибка при обработке города '{city}': {str(e)}")

    if not weather_data:
        return {}, [], [], " ".join(errors)

    # Формирование графика
    figure = {'data': [], 'layout': {'title': 'Погодный прогноз по маршруту', 'xaxis': {'title': 'Время'}}}

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
        for i in range(len(times)):
            if 'temperature' in selected_params:
                figure['data'].append(go.Scatter(x=times, y=temperatures, mode='lines+markers', name=f'Температура ({city})'))
            if 'precipitation' in selected_params:
                figure['data'].append(go.Scatter(x=times, y=precip_probs, mode='lines+markers', name=f'Осадки ({city})'))
            if 'wind' in selected_params:
                figure['data'].append(go.Scatter(x=times, y=wind_speeds, mode='lines+markers', name=f'Скорость ветра ({city})'))

            # Заполняем таблицу
            table_data.append({
                'city': city,
                'datetime': times[i],
                'temperature': temperatures[i],
                'wind': wind_speeds[i],
                'precipitation': precip_probs[i]
            })

    return figure, table_data, columns, " ".join(errors) if errors else ""



if __name__ == "__main__":
    app.run(debug=True)
