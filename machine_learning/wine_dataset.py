from hashlib import new
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
        x = xy[:, 1:]
        y = xy[:, [0]]


data = WineDataset()