import torch

# check if CUDA GPU support is available (False for most notebooks)
if torch.cuda.is_available(): 
	print('CUDA support is available for current system')
else:
	print('No CUDA support available for current system')

"""use torch's autograd function"""

x = torch.ones(3, 3, requires_grad=True) # generates computational graph for back-propagation
y = x + 2 # forward pass of tensor
print(y) # observe attribute grad_fn=<AddBackward0>, which computes gradients

z = y * y * 2
print(z) # different grad_fn=<MulBackward0>

# v = torch.ones(3, 3)
# z.backward(v) # pass vector for matrix multiplication (chain rule) to calculate dz/dy

z = z.mean()
z.backward() # compute gradient dz/dy, no args necessary because z is scalar (mean), mostly the case

print(x.grad)

# prevent tracking of gradients
a = torch.ones(3, 3, requires_grad=True) # like before
print(a)
a.detach_() # in-place operation, also possible with a = a.detach()
print(a)

b = torch.rand(3, 3, requires_grad=True)
with torch.no_grad():
	c = b * b
	print(c) # no grad
c = b * b
print(c) # with grad

"""dummy training experiment - CAVE"""

weights = torch.ones(4, requires_grad=True)

# incorrect
for epoch in range(3):
	model_output = (weights * 3).sum()
	model_output.backward()
	print(weights.grad) # every iteration adds to the grad function --> incorrect!

weights = torch.ones(4, requires_grad=True)

# correct
for epoch in range(3):
	model_output = (weights * 3).sum()
	model_output.backward()
	print(weights.grad) 

	weights.grad.zero_() # solution --> correct gradients