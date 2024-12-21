from dash import Dash, dcc, html

# Создаем приложение Dash
dash_app = Dash(__name__)

# Добавляем простой график
dash_app.layout = html.Div([
    html.H1("Пример графика с использованием Dash"),
    dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'Город 1'},
                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': 'Город 2'},
            ],
            'layout': {
                'title': 'Пример графика'
            }
        }
    )
])

if __name__ == "__main__":
    dash_app.run_server(debug=True)
