from re import X
from traceback import print_tb
import torch

# check if CUDA GPU support is available (False for most notebooks)
if torch.cuda.is_available(): 
	print('CUDA support is available for current system')
else:
	print('No CUDA support available for current system')

# use torch's autograd function

x = torch.ones(3, 3, requires_grad=True)
y = x + 2

print(y)