import os
import sys
import numpy as np
from tkinter import filedialog

class LogfileExtractor:
    def __init__(self) -> None:
        self.logfile_dir = filedialog.askdirectory()  # contains fraction dirs
        if self.logfile_dir == '':
            sys.exit('No directory selected, exiting..')
        
        self.fraction_list = os.listdir(self.logfile_dir)
        self.num_fractions = len(self.fraction_list)
    
    def get_beam_data(self):
        for fraction in self.fraction_list:
            for beam in os.listdir(f'{self.logfile_dir}/{fraction}'):
                print(beam)
        

test = LogfileExtractor()
test.get_beam_data()