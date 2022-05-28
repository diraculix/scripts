'''File: modify_doi.py >> change appearance of doi-links in LaTeX bibliography (.bib) files'''

import io
from tkinter import filedialog

# tkinter: choose bibfile
bibfilename = filedialog.askopenfilename(filetypes=[('Bibliography Files', '*.bib')])
bibfile = io.open(bibfilename, mode='r', encoding='utf-8')

# sweep over lines in file
n_doikeys = 0
for line in bibfile:
    if line.__contains__('doi ='):
        n_doikeys += 1

print(f'Found {n_doikeys} DOI keys')