import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatch
from tkinter import *
from tkinter import filedialog
import os
import sys

global n_case
global interactions_table
script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))


'''____________________________________FUNCTIONS____________________________________'''


# filter for logfiles
def get_iwatch_files():
    dosxyz_dir = '/home/egs-user/EGSnrc/egs_home/dosxyznrc'
    iwatch_logs_dir = '/media/egs-user/WD_ELEMENTS/IWATCH_Logs'
    file_types = (('EGS log files', '*.egslog'), ('All files', '*.*'))
    log_files = filedialog.askopenfilenames(title='Choose EGS log file', initialdir=iwatch_logs_dir, filetypes=file_types)

    if len(log_files) == 0:
        sys.exit('No IWATCH logfiles selected. Exiting ..')
    
    return log_files


# count defined interaction occurrences
def get_interactions(iwatch_file):
    global n_case

    with open(iwatch_file, 'r') as iwatch:
        compton_z, moller_z, photo_z, xray_z, brems_z, pair_z, rayleigh_z = [], [], [], [], [], [], []
        lines = iwatch.readlines()
        found = False
        for n, line in enumerate(lines):
            if str(line).__contains__('NCASE'):
                found = True
                pos = n
                break

        try:
            ncase_line = lines[pos + 3].split(' ')
        except UnboundLocalError:
            sys.exit(f'Global variable NCASE not found in file {iwatch_file}, please check file validity')
        
        print(f'Retrieving IWATCH interaction data from file {iwatch_file} ..')

        for snip in ncase_line:
            if snip != '':
                n_case = int(snip)
                break   

        for line in lines:
            if str(line).__contains__('Compton  about to occur'):
                new_line = str(line).split(':')[-1]
                x = float(new_line[23:30])
                y = float(new_line[31:38])
                z = float(new_line[40:47])
                if abs(x) <= 5.0 and abs(y) <= 5.0:
                    compton_z.append(z)
            
            elif str(line).__contains__('Moller   about to occur'):
                new_line = str(line).split(':')[-1]
                x = float(new_line[23:30])
                y = float(new_line[31:38])
                z = float(new_line[40:47])
                if abs(x) <= 5.0 and abs(y) <= 5.0:
                    moller_z.append(z)

            elif str(line).__contains__('Photoelectric about to occur'):
                new_line = str(line).split(':')[-1]
                x = float(new_line[23:30])
                y = float(new_line[31:38])
                z = float(new_line[40:47])
                if abs(x) <= 5.0 and abs(y) <= 5.0:
                    photo_z.append(z)

            elif str(line).__contains__('Fluorescent X-ray created'):
                new_line = str(line).split(':')[-1]
                x = float(new_line[23:30])
                y = float(new_line[31:38])
                z = float(new_line[40:47])
                if abs(x) <= 5.0 and abs(y) <= 5.0:
                    xray_z.append(z)

            elif str(line).__contains__('bremsstrahlung  about to occur'):
                new_line = str(line).split(':')[-1]
                x = float(new_line[23:30])
                y = float(new_line[31:38])
                z = float(new_line[40:47])
                if abs(x) <= 5.0 and abs(y) <= 5.0:
                    brems_z.append(z)

            elif str(line).__contains__('Pair production about to occur'):
                new_line = str(line).split(':')[-1]
                x = float(new_line[23:30])
                y = float(new_line[31:38])
                z = float(new_line[40:47])
                if abs(x) <= 5.0 and abs(y) <= 5.0:
                    pair_z.append(z)
            
            elif str(line).__contains__('Rayleigh scattering occured'):
                new_line = str(line).split(':')[-1]
                x = float(new_line[23:30])
                y = float(new_line[31:38])
                z = float(new_line[40:47])
                if abs(x) <= 5.0 and abs(y) <= 5.0:
                    rayleigh_z.append(z)

        if len(compton_z) == 0:
            print('WARNING: No Compton scattering detected')
        if len(moller_z) == 0:
            print('WARNING: No Moller scattering detected')
        if len(photo_z) == 0:
            print('WARNING: No photoelectric effect detected')
        if len(xray_z) == 0:
            print('WARNING: No fluorescent X-ray detected')
        if len(brems_z) == 0:
            print('WARNING: No Bremsstrahlung detected')
        if len(pair_z) == 0:
            print('WARNING: No pair production detected')
        if len(rayleigh_z) == 0:
            print('WARNING: No Rayleigh scattering detected')
        
        print('>> DONE')
        iwatch.close()

        return compton_z, moller_z, photo_z, xray_z, brems_z, pair_z, rayleigh_z


# resample z-axis to enable histogram plotting
def resample_plot(z_array, increment=0.025):
    global n_case

    print(f'Resampling data of file with z-increment dz={increment} cm for plotting ..')

    z_axis = np.arange(0, 30, increment)
    resampled = np.zeros(len(z_axis))
    for index, z in enumerate(z_axis):
        count = 0
        for interaction_z in z_array:
            if index == 0:
                if interaction_z < z:
                    count += 1
            else: 
                if z_axis[index - 1] < interaction_z <= z_axis[index]:
                    count += 1
        
        resampled[index] = count / n_case * 100
    
    print('>> DONE')

    return z_axis, resampled


'''______________________________________MAIN_______________________________________'''


interactions_table = ['Compton', 'Møller', 'Photoelectric', 'Fluorescent', 'Bremsstrahlung', 'Pair Production', 'Rayleigh']
color_table = ['black', 'tab:green', 'tab:red', 'indigo', 'tab:pink', 'tab:gray', 'tab:cyan']
zorder_table = [5, 10, 0, 3, 20, 30, 25]
handles = [mpatch.Patch(color=color_table[i], label=interactions_table[i]) for i in range(len(interactions_table))]
line_table = ['-', ':', '--']

os.chdir(script_dir)

iwatch_files = get_iwatch_files()
out_dir = 'IWATCH_out'
if not os.path.exists(f'./{out_dir}'):
    os.mkdir(f'./{out_dir}')

for i, file in enumerate(iwatch_files):
    outfile_name = f'''IWATCH_out_{str(file).split('/')[-1].split('.')[0]}.txt'''
    outfile_string = f'Source file: {str(file)}\n\n'

    results = list(get_interactions(file))
    for j, data in enumerate(results):
        z_axis, z_counts = resample_plot(data)
        outfile_string += f'{interactions_table[j].upper()}\n\nz [cm]\trelative occurrence per history [%]\n'
        for k in zip(z_axis, z_counts):
            outfile_string += f'{float(k[0]).__round__(6)}\t{float(k[1]).__round__(6)}\n'
        outfile_string += '\n'
        plt.step(z_axis, z_counts, where='pre', linestyle=line_table[i], lw=0.7, color=color_table[j], zorder=zorder_table[j])
        with open(f'{out_dir}/{outfile_name}', 'w+') as target:
            print(f'Committing write to target: {out_dir}/{outfile_name}')
            target.write(outfile_string)
            target.close()
    print('\n')