import torch
import numpy as np

"""Tensor definition"""

torch.manual_seed(999)

x1 = torch.rand(2,5,5) # an random tensor
# print(x1)
x2 = torch.rand(2,5,5) # another one
# print(x2)

torch.manual_seed(999) # re-seed

x3 = torch.rand(2,5,5)
# print(x1 == x3) # identical after re-seed

e = torch.empty(5, 5)
# print(e) # empty tensor, almost zero
e = torch.zeros(5, 5, dtype=int)
# print(e.dtype) # empty tensor, exactly zero with type integer

m = torch.tensor([4.2, 6.9]) # manual tensor definition
# print(m)

"""Tensor operation"""

# addition
if x1.size() == x2.size() == x3.size():
    print('Operation permitted')
    x4 = x1 + x2 + x3 # also possible with torch.add(x1, x2, x3) -or- x1.add_(x2), underscore indicates an in-place operation (variable is modified directly)
    print(x4)

# subtraction
if x1.size() == x2.size() == x3.size():
    print('Operation permitted')
    x5 = x4 - x1
    x5 = torch.sub(x4, x1)
    x5 = x4.sub_(x1)
    print(x5)

# multiplication
if x1.size() == x2.size() == x3.size(): # identical dimensions required, unlike matrix multiplication, commutative
    print('Operation permitted')
    x3 = x1 * x2
    print(x3)
    x3 = torch.mul(x2, x1)
    print(x3)

# slicing
x = torch.rand(3, 3)
print(x)
print(x[0, :]) # first row
print(x[:, 1]) # second column
print(x[1, 2]) # entry, but as tensor
print(x[1, 2].item()) # entry, but actual item (one-element tensors only)

# re-shaping
x = torch.rand(4, 4) # 16 entries
y = x.view(16) # still 16 entries, 'reads' 2D tensor in 1D line
y = x.view(-1, 8) # give desired dimension, let pytorch handle sizing
print(x, y)

# conversion numpy <--> torch
a = torch.ones(5, 5)
print(a.dtype)
b = a.numpy()
print(b.dtype)
c = torch.from_numpy(b)
print(c.dtype)

a.add_(1) # add 1 to each tensor element, CPU computation stores a and b in same RAM location
print(a, '\n', b, 'both changed!')
