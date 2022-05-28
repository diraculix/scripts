import torch

if torch.cuda.is_available(): # check if CUDA GPU support is available (False)
	print('CUDA support is available for current system')
else:
	print('No CUDA support available for current system')
