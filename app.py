import ccxt
import requests
import pandas as pd
from datetime import datetime
from pytz import timezone
import time
import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output
import plotly.express as px

# Keep your existing functions (get_funding_rates, get_mark_prices) as they are

app = dash.Dash(__name__)
server = app.server  # This is for Render deployment

app.layout = html.Div([
    html.H1('Funding Rates and Mark Prices'),
    dcc.Interval(
        id='interval-component',
        interval=300*1000,  # in milliseconds (5 minutes)
        n_intervals=0
    ),
    html.Div(id='funding-rates-table'),
    html.Div(id='mark-prices-table'),
    html.Div(id='merged-data-table'),
    dcc.Graph(id='funding-rates-chart')
])

@app.callback(
    [Output('funding-rates-table', 'children'),
     Output('mark-prices-table', 'children'),
     Output('merged-data-table', 'children'),
     Output('funding-rates-chart', 'figure')],
    Input('interval-component', 'n_intervals')
)
def update_data(n):
    # Get funding rates
    funding_data = get_funding_rates()
    funding_df = pd.DataFrame(funding_data, columns=['Symbol', 'Funding Rate', 'Current Funding Time (PST)', 'Max Leverage'])
    
    # Get mark prices
    mark_prices_df = get_mark_prices()
    
    # Merge the two tables
    merged_df = pd.merge(funding_df, mark_prices_df, left_on='Symbol', right_on='Name', how='left')
    merged_df.drop(columns=['Name'], inplace=True)
    
    # Create DataTables
    funding_table = dash_table.DataTable(
        data=funding_df.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in funding_df.columns],
        style_table={'overflowX': 'auto'}
    )
    
    mark_prices_table = dash_table.DataTable(
        data=mark_prices_df.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in mark_prices_df.columns],
        style_table={'overflowX': 'auto'}
    )
    
    merged_table = dash_table.DataTable(
        data=merged_df.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in merged_df.columns],
        style_table={'overflowX': 'auto'}
    )
    
    # Create a bar chart of funding rates
    fig = px.bar(funding_df, x='Symbol', y='Funding Rate', title='Funding Rates by Symbol')
    
    return html.Div([
        html.H2('Funding Rates'),
        funding_table
    ]), html.Div([
        html.H2('Mark Prices'),
        mark_prices_table
    ]), html.Div([
        html.H2('Merged Data'),
        merged_table
    ]), fig

if __name__ == '__main__':
    app.run_server(debug=True)