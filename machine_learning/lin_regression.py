import torch
import torch.nn as nn
import numpy as np                  # for data transforms
from sklearn import datasets        # generate linear regression dataset
import matplotlib.pyplot as plt

# (0) Prep data
x_np, y_np = datasets.make_regression(n_samples=100, n_features=1, noise=20, random_state=1)
x = torch.from_numpy(x_np.astype(np.float32))
y = torch.from_numpy(y_np.astype(np.float32))

y = y.view(-1, 1) # transform data in 100-row, 1-col vector

n_samples, n_features = x.shape

# (1) Model
in_size = n_features
out_size = 1
model = nn.Linear(in_size, out_size)

# (2) Loss and optimizer
learning_rate = 0.01
criterion = nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)

# (3) Training loop
n_epochs = 300
for epoch in range(n_epochs):
    y_pred = model(x)               # forward pass, estimate y
    loss = criterion(y, y_pred)     # calculate loss (MSE)
    loss.backward()                 # backward pass, compute gradients
    optimizer.step()                # update weights & biases
    optimizer.zero_grad()           # empty gradients (always!)

    if (epoch + 1) % 10 == 0:
        [weights, biases] = model.parameters()
        print(f'Epoch {str(epoch + 1).zfill(4)} | Weight: {weights[0].item():.6f}, Bias: {biases[0].item():.6f}, Loss: {loss:.6f}')

# plt.show()
# plt.plot(x, y, '.', x, weights[0].item() * x + biases[0].item(), '-')
# plt.show()

predicted = model(x).detach().numpy()
plt.plot(x_np, y_np, '.')
plt.plot(x_np, predicted, '-')
plt.show()
