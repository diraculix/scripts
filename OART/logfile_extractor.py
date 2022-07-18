import os
import sys
import numpy as np
import pandas as pd
import datetime as dt
from tkinter import filedialog
from matplotlib import pyplot as plt


class MachineLog:
    def __init__(self) -> None:
        valid_dir = False
        while not valid_dir:
            self.logfile_dir = filedialog.askdirectory(title='Select logfile root directory')
            if self.logfile_dir == '':
                sys.exit('No directory selected, exiting..')
            for index, element in enumerate(os.listdir(self.logfile_dir)):
                if not os.path.isdir(os.path.join(self.logfile_dir, element)):
                    print(f'''Chosen path '{self.logfile_dir}' may only contain directories (one per fraction). Please retry..''')
                    break
                elif index == len(os.listdir(self.logfile_dir)) - 1:
                    valid_dir = True
        
        self.fraction_list = os.listdir(self.logfile_dir)
        self.num_fractions = len(self.fraction_list)
        self.beam_list = []
        for f in self.fraction_list:
            beams_in_frac = os.listdir(os.path.join(self.logfile_dir, f))
            self.beam_list.append(beams_in_frac)
        
    def summarize_beams(self):
        print(f'Total {self.num_fractions} fractions in {self.logfile_dir}\n')
        for index, fraction in enumerate(self.fraction_list):
            print(f'[{index + 1}] - {fraction}')
            for beam in self.beam_list[index]:
                print('\t', beam)
        

class Beam(MachineLog):
    def __init__(self, log, fraction_id, beam_id) -> None:
        current_beam_path = os.path.join(log.logfile_dir, fraction_id, beam_id)
        os.chdir(current_beam_path)
        while len(os.listdir('.')) < 2:
            os.chdir(os.listdir('.')[0])
        
        self.beam_id = beam_id
        self.fraction_id = fraction_id
        self.map_records, self.tunings, unused = [], [], []
        for file in os.listdir('.'):
            if file.__contains__('beam.'):
                self.beam_file = file
            elif file.__contains__('beam_config.'):
                self.beam_config = file
            elif file.__contains__('map_record') and file.__contains__('part'):
                self.map_records.append(file)
            elif file.__contains__('map_record') and file.__contains__('tuning'):
                self.tunings.append(file)
            else:
                unused.append(file)

        if len(self.map_records) == 0 or len(self.tunings) == 0:
            raise LookupError('No logfiles found!')          

        self.num_layers = len(self.map_records)  
        
        with open(self.beam_file, 'r') as beam_file:
            for line in beam_file.readlines():
                if line.__contains__('GantryAngle'):
                    self.gantry_angle = float(line.split('>')[1].split('<')[0])
                elif line.__contains__('pressure'):
                    pressure = float(line.split(',')[-1])
                elif line.__contains__('temperature'):
                    temperature = float(line.split(',')[-1])
                
            ref_pressure, ref_temperature = 1013., 293.
            self.correction_factor = (ref_pressure * temperature) / (ref_temperature * pressure)
            beam_file.close()
        
        # print(f'\nBeam file: \n {self.beam_file}\nConfig file: \n {self.beam_config}\nMap records: \n {np.array(self.map_records)}\nTunings: \n {np.array(self.tunings)}\nUnused: \n {np.array(unused)}')
   
    def collect_beam_data(self, layers='all') -> None:
        self.layerdict = dict(zip([id for id in range(self.num_layers)],[layer for layer in self.map_records]))
        self.tuningdict = dict(zip([id for id in range(self.num_layers)],[layer for layer in self.tunings]))
        self.layer_spot_data, self.layer_tuning_data = [], []

        if str(layers) == 'all':
            layers = range(self.num_layers)
        elif int(layers) > self.num_layers - 1:
            print(f'Selected layer-ID [{layers}] exceeds highest layer-ID [{self.num_layers - 1}], using max. value instead..')
            layers = [self.num_layers - 1]
        else:
            layers = [int(layers)]

        for layer_id in layers:
            spot_dfs, tuning_dfs = [], []
            layer_df = pd.read_csv(self.layerdict[layer_id], delimiter=',', skiprows=10, skipfooter=11, engine='python')
            tuning_df = pd.read_csv(self.tuningdict[layer_id], delimiter=',', skiprows=10, skipfooter=11, engine='python')    
            layer_df['TIME'] = pd.to_datetime(layer_df['TIME'])
            layer_df.index = layer_df['TIME']
            total_beamtime = layer_df['TIME'].iloc[-1] - layer_df['TIME'].iloc[0]
            layer_df = layer_df.loc[:, :'Y_DOSE_RATE(A)']
            layer_df = layer_df.loc[(layer_df['X_WIDTH(mm)'] != -10000.0) & (layer_df['Y_WIDTH(mm)'] != -10000.0) & (layer_df['X_POSITION(mm)'] != -10000.0) & (layer_df['Y_POSITION(mm)'] != -10000.0)]
            layer_df.drop(columns=['TIME'], inplace=True)
            
            while not layer_df.empty:  # mine dataframe until empty
                current_spot = layer_df.loc[layer_df['SUBMAP_NUMBER'] == min(layer_df['SUBMAP_NUMBER'])]
                layer_df.drop(current_spot.index, inplace=True)
                spot_dfs.append(current_spot)
            
            while not tuning_df.empty:  # mine dataframe until empty
                current_tune = tuning_df.loc[tuning_df['SUBMAP_NUMBER'] == min(tuning_df['SUBMAP_NUMBER'])]
                tuning_df.drop(current_tune.index, inplace=True)
                tuning_dfs.append(current_tune)
            
            self.layer_spot_data.append(spot_dfs)
            self.layer_tuning_data.append(tuning_dfs)
            del spot_dfs, tuning_dfs
        
        print('  ..Drawing..')
        fig, axs = plt.subplots(6, 5, sharex=True, sharey=True, figsize=(15, 15), dpi=70)
        ax0 = fig.add_subplot(111, frameon=False)
        fig.subplots_adjust(hspace=0.0, wspace=0.0)
        axs = axs.ravel()
        for index, layer in enumerate(self.layer_spot_data):
            layer_x_means, layer_y_means = [], []
            layer_x_stds, layer_y_stds = [], []
            tuning_x_means, tuning_y_means= [], []
            tuning_x_stds, tuning_y_stds = [] ,[]  # HERE!
            for spot in layer:
                layer_x_means.append(spot['X_POSITION(mm)'].mean())
                layer_x_stds.append(spot['X_POSITION(mm)'].std())
                layer_y_means.append(spot['Y_POSITION(mm)'].mean())
                layer_y_stds.append(spot['Y_POSITION(mm)'].std())
            
            axs[index].plot(layer_x_means, layer_y_means)
            axs[index].plot(layer_x_means, layer_y_means, '.', color='black', label=f'Layer {str(index).zfill(2)}')
            if index == int(len(self.layer_spot_data) / 2):
                axs[index].set_xlim(np.median(layer_x_means) - 30, np.median(layer_x_means) + 30)
                axs[index].set_ylim(np.median(layer_y_means) - 30, np.median(layer_y_means) + 30)
            # axs[index].errorbar(layer_x_means, layer_y_means, xerr=layer_x_stds, yerr=layer_y_stds)  #, xerr=layer_x_stds, yerr=layer_y_stds)
            axs[index].legend(loc='upper right')
        plt.suptitle(f'Spot Positions for Beam-ID: {self.beam_id} in Fraction: {self.fraction_id}', fontweight='bold', y=0.9)
        ax0.set_xlabel('X', fontweight='bold', labelpad=10)
        ax0.set_ylabel('Y', fontweight='bold', labelpad=10)
        plt.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
        output_dir = f'{log.logfile_dir}/../output'
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        plt.savefig(f'{output_dir}/{self.fraction_id}_{self.beam_id}_spots.pdf')
        del fig, axs


if __name__ == '__main__':
    log = MachineLog()
    print('Will collect information about selected fields:')
    for fraction in range(log.num_fractions):
        for beam in range(len(log.beam_list[fraction])):
            testbeam = Beam(log, log.fraction_list[fraction], log.beam_list[fraction][beam])
            if beam == 0:
                print(' ', str(fraction + 1).zfill(2), '- [BEAM-ID]', testbeam.beam_id, '[FX-ID]', testbeam.fraction_id, '[GANTRY]', testbeam.gantry_angle)
            else:
                print(7*' '+'[BEAM-ID]', testbeam.beam_id, '[FX-ID]', testbeam.fraction_id, '[GANTRY]', testbeam.gantry_angle)
    del testbeam
    proceed = input('Start data mining [y/n]? ')
    if proceed == 'n':
        sys.exit('Process cancelled by user, exiting..')
    
    print('Starting..')
    for fraction in range(log.num_fractions):
        for beam in range(len(log.beam_list[fraction])):
            beam = Beam(log, log.fraction_list[fraction], log.beam_list[fraction][beam])
            print(' ', str(fraction + 1).zfill(2), '- [BEAM-ID]', beam.beam_id, '[FX-ID]', beam.fraction_id, '[GANTRY]', beam.gantry_angle)
            beam.collect_beam_data(layers='all')
        print(f'Fraction {str(fraction + 1).zfill(2)}/{log.num_fractions} complete')
        
