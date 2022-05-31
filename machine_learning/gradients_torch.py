import torch

 # f = w * x
 # f = 2 * x

# sample training data (fixed)
X = torch.tensor([1, 2, 3, 4], dtype=torch.float32)
Y = torch.tensor([2, 4, 6, 8], dtype=torch.float32)

w = torch.tensor(0., dtype=torch.float32, requires_grad=True)

# model prediction
def forward(x):
    return w * x

# loss ... MSE (linear regression)
def loss(y, y_pred):
    return ((y - y_pred)**2).mean() # same syntax as in numpy

print(f'Prediction before training: f(5) = {forward(5):.3f}')

# training
learning_rate = 0.01
n_iters = 10

for epoch in range(n_iters):
    # prediction a.k.a. forward pass
    y_pred = forward(X)

    # loss
    l = loss(Y, y_pred)

    # gradients ... now backward pass
    l.backward() # gradient of loss dl/dw

    # update weights ... but do not include this in graph
    with torch.no_grad():
        w -= learning_rate * w.grad

    # zero gradients
    w.grad.zero_()

    if (epoch + 1) % 1 == 0:
        print(f'epoch {epoch + 1}: w = {w:.3f}, loss = {l:.8f}')

print(f'Prediction after training: f(5) = {forward(5):.3f}')

### now replace prediction/loss function/manual weight updater with PyTorch model/loss/optimizer