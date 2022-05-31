import torch

### networks are chained computation nodes, each performs a certain operation
### PyTorch stores 'computational graphs' with local gradients for each operation, which is quite simple
### at the end, a loss function is calculated which is to be minimized --> propagate backwards through local gradients 
### three steps: (1) forward pass, compute loss (2) compute local gradients (3) Backward pass, compute d(loss)/d(weights) ... chain rule

"""linear regression: estimate ^y = w * x (linear expression), give fixed real y, compute loss, backpropagate """

x = torch.tensor(1.0) # input (fixed)
y = torch.tensor(2.0) # real value (fixed)

w = torch.tensor(1.0, requires_grad=True) # weight (variable)

# forward pass, compute loss
y_hat = w * x
loss = (y_hat - y)**2

print(loss)

# backward pass
loss.backward()
print(w.grad)

### update weights, then commit next forward pass