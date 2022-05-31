import numpy as np

 # f = w * x
 # f = 2 * x

# sample training data (fixed)
X = np.array([1, 2, 3, 4], dtype=np.float32)
Y = np.array([2, 4, 6, 8], dtype=np.float32)

w = 0.

# model prediction
def forward(x):
    return w * x

# loss ... MSE (linear regression)
def loss(y, y_pred):
    return ((y - y_pred)**2).mean()

# gradient a.k.a. derivative of loss (objective) function
# MSE = 1/N 2x (w*x - y)**2
# dJ/dw = 1/N 2x (w*x - y)
def gradient(x, y, y_pred):
    return np.dot(2 * x, y_pred - y) / len(x)

print(f'Prediction before training: f(5) = {forward(5):.3f}')

# training
learning_rate = 0.01
n_iters = 10

for epoch in range(n_iters):
    # prediction a.k.a. forward pass
    y_pred = forward(X)

    # loss
    l = loss(Y, y_pred)

    # gradients
    dw = gradient(X, Y, y_pred)

    # update weights
    w -= learning_rate * dw

    if (epoch + 1) % 1 == 0:
        print(f'epoch {epoch + 1}: w = {w:.3f}, loss = {l:.8f}')

print(f'Prediction after training: f(5) = {forward(5):.3f}')

### now get rid of manual gradient definition