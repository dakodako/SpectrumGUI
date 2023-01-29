
# import seabreeze.spectrometers as sb
# from seabreeze.spectrometers import Spectrometer
from threading import Lock
# import seabreeze.cseabreeze as csb
# seabreeze.use('cseabreeze')
# from seabreeze.spectrometers import list_devices, Spectrometer

from dash import Dash, dcc, html, Input, Output
import plotly
import plotly.graph_objects as go
import DashOceanOpticsSpectrometer as doos
print(">>>>>>>>>>")
colors = {}

with open("colors.txt", 'r') as f:
    for line in f.readlines():
        colors[line.split(' ')[0]] = line.split(' ')[1].strip('\n')
# devices = sb.list_devices()
# spec = sb.Spectrometer(devices[0])
# spec.integration_time_micros(100000)
# wavelengths = spec.wavelengths()
# intensities = spec.intensities()
# print(spec)
# print(spec)

spec_lock = Lock()
comm_lock = Lock()

# spec = doos.DashOceanOpticsSpectrometers(spec_lock, comm_lock)
spec = doos.PhysicalSpectrometer(spec_lock, comm_lock)

# spec.assign_spec()
# spectrum = spec.get_spectrum()
# print(spectrum)
app = Dash(__name__)
app.layout = html.Div(
    [
        dcc.Graph(id='live-graph'),
        dcc.Interval(
            id='interval-component',
            interval=1*500, # in milliseconds
            n_intervals=0
        )
    ]
)

@app.callback(Output('live-graph','figure'),
              Input('interval-component', 'n_intervals'))
def update_plot(input_data):

    traces = []
    wavelengths = []
    intensities = []

    x_axis = {
            'title': 'Wavelength (nm)',
            'titlefont': {
                'family': 'Helvetica, sans-serif',
                'color': colors['secondary']
            },
            'tickfont': {
                'color': colors['tertiary']
            },
            'dtick': 100,
            'color': colors['secondary'],
            'gridcolor': colors['grid-colour']
    }
    y_axis = {
        'title': 'Intensity (AU)',
        'titlefont': {
            'family': 'Helvetica, sans-serif',
            'color': colors['secondary']
        },
        'tickfont': {
            'color': colors['tertiary']
        },
        'color': colors['secondary'],
        'gridcolor': colors['grid-colour'],
    }
    
    spectrum = spec.get_spectrum()
    wavelengths = spectrum[0]
    intensities = spectrum[1]
    
    x_axis['range'] = [
        min(wavelengths),
        max(wavelengths)
    ]
    y_axis['range'] = [
        0,
        max(intensities)
    ]
    traces.append(go.Scatter(
        x=wavelengths,
        y=intensities,
        name='Spectrometer readings',
        mode='lines',
        line={
            'width': 1,
            'color': colors['accent']
        }
    ))

    layout = go.Layout(
        height=600,
        font={
            'family': 'Helvetica Neue, sans-serif',
            'size': 12
        },
        margin={
            't': 20
        },
        titlefont={
            'family': 'Helvetica, sans-serif',
            'color': colors['primary'],
            'size': 26
        },
        xaxis=x_axis,
        yaxis=y_axis,
        paper_bgcolor=colors['background'],
        plot_bgcolor=colors['background'],
    )
    # print(traces)
    return {'data': traces,
            'layout': layout}

if __name__ == '__main__':
    app.run_server(debug=False)
