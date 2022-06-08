import numpy as np
import matplotlib.pyplot as plt

x = list(np.linspace(0, 5, 100))    # could be anything
y = list(np.sin(x))                 # could be anything but same length


def three_point_diff(x, y):
    if len(x) != len(y):
        y = y[:len(x)]
    
    derivative = []
    for i in range(len(x)):
        if 0 < i < len(x) - 1:
            point = (y[i + 1] - y[i - 1]) / (x[i + 1] - x[i - 1])
            derivative.append(point)        
    
    return derivative


dy = three_point_diff(x, y)
print(len(y), len(dy))

plt.plot(x, y, label='sin(x)')
plt.plot(x[1:-1], dy, '.', label='dy/dx')
plt.plot(x, np.cos(x), label='cos(x)')  # proof
plt.legend()
plt.show()