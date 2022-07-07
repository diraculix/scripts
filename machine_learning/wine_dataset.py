# goal: divide large datasets into batches, perform training over batches

import torch
import torchvision
from torch.utils.data import Dataset, DataLoader
import numpy as np
import math

class WineDataset(Dataset):
    def __init__(self):
        # data loading
        target = 'C:\\Users\\lukas\\scripts\\machine_learning\\data\\wine.csv'
        xy = np.loadtxt(target, delimiter="," , skiprows=1, dtype=np.float32)
        self.x = torch.from_numpy(xy[:, 1:])
        self.y = torch.from_numpy(xy[:, [0]])
        self.n_samples = xy.shape[0]

    def __getitem__(self, index):
        return self.x[index], self.y[index]
    
    def __getlen__(self):
        return self.n_samples

data = WineDataset()