# 1. Design model (input/output size, forward pass)
# 2. Construct loss and optimizer
# 3. Training loop:
#   - forward pass: compute prediction
#   - backward pass: gradients
#   - update weights

import torch
import torch.nn as nn

# sample training data (fixed)
X = torch.tensor([1, 2, 3, 4], dtype=torch.float32)
Y = torch.tensor([2, 4, 6, 8], dtype=torch.float32)

w = torch.tensor(0., dtype=torch.float32, requires_grad=True)


# model prediction
def forward(x):
    return w * x


print(f'Prediction before training: f(5) = {forward(5):.3f}')

# training
learning_rate = 0.01
n_iters = 10

loss = nn.MSELoss()
optimizer = torch.optim.SGD([w], lr=learning_rate)

for epoch in range(n_iters):
    # prediction/forward pass
    y_pred = forward(X)

    # loss (torch MSE)
    l = loss(y_pred, Y)

    # gradients (torch backward pass)
    l.backward()

    # update weights (torch optimizer)
    optimizer.step()

    # zero weights
    w.grad.zero_()

    if (epoch + 1) % 1 == 0:
        print(f'epoch {epoch + 1}: w = {w:.3f}, loss = {l:.8f}')

print(f'Prediction after training: f(5) = {forward(5):.3f}')
