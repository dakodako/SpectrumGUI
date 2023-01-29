import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import seabreeze.spectrometers as sb 
devices = sb.list_devices()
spec = sb.Spectrometer(devices[0])

# print(spec)
fig, ax = plt.subplots(1, 1)
fig.set_size_inches(5,5)
points = [(0.1, 0.5), (0.5, 0.5), (0.9, 0.5)]
def animate(i):
    ax.clear()
    # Get the point from the points list at index i
    # spectrum = spec.get_spectrum()
    spectrum = spec.spectrum()
    x = spectrum[0]
    y = spectrum[1]
    # Plot that point using the x and y coordinates
    ax.plot(x, y, color='green', 
            label='original')
    # Set the x and y axis to display a fixed range
    # ax.set_xlim([0, 1])
    # ax.set_ylim([0, 1])
ani = FuncAnimation(fig, animate, frames=10,
                    interval=500, repeat=False)
plt.show()