import streamlit as st
import json
import pandas as pd
import requests
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Programmatically set the config to hide error details
st.set_option('client.showErrorDetails', False)

# Streamlit page configuration
st.set_page_config(page_title="Air Quality Dashboard", layout="wide")

# Set auto-refresh interval in seconds
st_autorefresh(interval=300000, limit=None, key="fizzbuzzcounter")
REFRESH_INTERVAL = 60

# Initialize session state variables
if 'data' not in st.session_state:
    st.session_state['data'] = pd.DataFrame()
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = 0

# Function to fetch data from API
def fetch_data():
    url = "http://sqm.mimasoft.cl:3000/api/datos-PM10"
    try:
        response = requests.get(url, timeout=10)  # Added timeout
        if response.status_code == 200:
            return pd.DataFrame(json.loads(response.text))
        else:
            st.error(f"Failed to fetch data. Status code: {response.status_code}")
            return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

# Auto-refresh using JavaScript
st.markdown(
    f"""
    <script>
        var lastUpdate = {int(time.time())};
        function checkForUpdate() {{
            if (Date.now() / 1000 - lastUpdate >= {REFRESH_INTERVAL}) {{
                window.location.reload();
            }}
        }}
        setInterval(checkForUpdate, 1000);
    </script>
    """,
    unsafe_allow_html=True
)

# Fetch new data if needed
current_time = time.time()
if current_time - st.session_state['last_update'] > REFRESH_INTERVAL or st.session_state['data'].empty:
    new_data = fetch_data()
    if not new_data.empty:  # Only update if we successfully got new data
        st.session_state['data'] = new_data
        st.session_state['last_update'] = current_time

df = st.session_state['data']

# Process data
if not df.empty:
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df['timestamp'] = pd.to_datetime(df['timestamp']).astype('int64') // 10**6

# Sidebar with refresh controls and status
st.sidebar.title("Control del Dashboard")

# Manual refresh button
if st.sidebar.button("Refrescar Datos 🔄"):
    st.session_state['data'] = fetch_data()
    st.session_state['last_update'] = time.time()
    st.rerun()

# Display last update time with auto-updating JavaScript
st.sidebar.markdown(
    f"""
    <div id="lastUpdate">
        Last updated: {datetime.fromtimestamp(st.session_state['last_update']).strftime('%Y-%m-%d %H:%M:%S')}
    </div>
    <script>
        function updateTimestamp() {{
            document.getElementById('lastUpdate').innerHTML = 
                'Last updated: ' + new Date({int(st.session_state['last_update'] * 1000)}).toLocaleString();
        }}
        setInterval(updateTimestamp, 1000);
    </script>
    """,
    unsafe_allow_html=True
)

# Function to filter and prepare chart data
def get_chart_data(station_name, last_n=None):
    if df.empty:
        return json.dumps([])
    filtered_data = df[df['station_name'] == station_name][['timestamp', 'valor']]
    filtered_data = filtered_data.dropna()  # Remove any NaN values
    return json.dumps(filtered_data.values.tolist())

# Define stations configuration
chart_configs = [
    {"title": "Estación Mejillones", "station": "E1"},
    {"title": "Estación Sierra Gorda", "station": "E2"},
    {"title": "Estación Hospital", "station": "E5"},
    {"title": "Estación Huara", "station": "E6"},
    {"title": "Estación Victoria", "station": "E7"},
    {"title": "Estación Colonia Pintados", "station": "E8"}
]

# Enhanced Highcharts configuration function
def highcharts_chart(chart_id, chart_title, chart_data):
    return f"""
    <script src="https://code.highcharts.com/highcharts.js"></script>
    <script src="https://code.highcharts.com/modules/exporting.js"></script>
    <script src="https://code.highcharts.com/modules/export-data.js"></script>
    <div id="{chart_id}" style="height: 500px;"></div>
    <script>
        Highcharts.chart('{chart_id}', {{
            boost: {{
                useGPUTranslations: true,
                usePreallocated: true
            }},
            chart: {{
                zooming: {{
                    type: 'x'
                }},
                animation: false
            }},
            title: {{
                text: '{chart_title}'
            }},
            xAxis: {{
                type: 'datetime',
                ordinal: false
            }},
            yAxis: {{
                title: {{
                    text: 'PM10 (ug/m3)'
                }},
                min: 0
            }},
            legend: {{
                enabled: false
            }},
            plotOptions: {{
                area: {{
                    marker: {{
                        radius: 2,
                        enabled: false
                    }},
                    lineWidth: 1,
                    fillOpacity: 1,
                    states: {{
                        hover: {{
                            lineWidth: 1
                        }}
                    }},
                    threshold: null
                }}
            }},
            series: [{{
                type: 'area',
                name: 'PM10',
                data: {chart_data},
                turboThreshold: 0,
                tooltip: {{valueSuffix: ' ug/m3'}},
                zones: [
                {{value: 130, color: "#15b01a"}},
                {{value: 180, color: "#fbfb00"}},
                {{value: 230, color: "#ffa400"}},
                {{value: 330, color: "#ff0000"}},
                {{value: 10000, color: "#8a3d92"}},
                ]
            }}]
        }});
    </script>
    """

# Layout: 3 columns x 2 rows
cols = st.columns(3)

# Render the charts
for i, config in enumerate(chart_configs):
    with cols[i % 3]:
        chart_data = get_chart_data(config["station"], 6000)
        st.components.v1.html(
            highcharts_chart(f"container{i}", config["title"], chart_data),
            height=500
        )

# Add error handling status
if df.empty:
    st.error("No data available. Please check your connection and try refreshing.")
