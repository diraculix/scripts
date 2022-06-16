# 1. Design model (input/output size, forward pass)
# 2. Construct loss and optimizer
# 3. Training loop:
#   - forward pass: compute prediction
#   - backward pass: gradients
#   - update weights

import torch
import torch.nn as nn

# sample training data (fixed)
X = torch.tensor([[1], [2], [3], [4]], dtype=torch.float32)
Y = torch.tensor([[2], [4], [6], [8]], dtype=torch.float32)

n_samples, n_features = X.shape

# model, automatically compute forward pass and weights
# Linear requires 2D-array (numbers, features)
in_size = n_features
out_size = n_features
model = nn.Linear(in_size, out_size)

print(f'Prediction before training: f(5) = {model(torch.tensor([5], dtype=torch.float32)).item():.3f}')

# training
learning_rate = 0.01
n_iters = 2500

loss = nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)

for epoch in range(n_iters):
    # prediction/forward pass
    y_pred = model(X)

    # loss (torch MSE)
    l = loss(y_pred, Y)

    # gradients (torch backward pass)
    l.backward()

    # update weights (torch optimizer)
    optimizer.step()

    # zero weights
    model.zero_grad()

    if (epoch + 1) % 200 == 0:
        [w, b] = model.parameters()
        print(f'epoch {epoch + 1}: weight = {w[0][0].item():.8f}, loss = {l:.8f}')

print(f'Prediction after training: f(5) = {model(torch.tensor([5], dtype=torch.float32)).item():.3f}')
