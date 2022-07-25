import os
import sys
import tkinter
import numpy as np
import pandas as pd
from tkinter import Tk, filedialog
from matplotlib import pyplot as plt


class MachineLog:
    def __init__(self) -> None:
        valid_dir = False
        while not valid_dir:
            root = Tk()
            self.logfile_dir = filedialog.askdirectory(title='Select logfile root directory')
            root.destroy()
            if self.logfile_dir == '':
                sys.exit('No directory selected, exiting..')
            for index, element in enumerate(os.listdir(self.logfile_dir)):
                if not os.path.isdir(os.path.join(self.logfile_dir, element)):
                    print(f'''Chosen path '{self.logfile_dir}' may only contain directories (one per fraction). Please retry..''')
                    break
                elif index == len(os.listdir(self.logfile_dir)) - 1:
                    valid_dir = True
        
        self.patient_record_df, self.patient_tuning_df = pd.DataFrame(), pd.DataFrame()
        self.fraction_list = os.listdir(self.logfile_dir)
        self.num_fractions = len(self.fraction_list)
        self.beam_list = []
        for f in self.fraction_list:
            beams_in_frac = os.listdir(os.path.join(self.logfile_dir, f))
            self.beam_list.append(beams_in_frac)
        
        for fraction_no, fraction_id in enumerate(self.fraction_list):
            for beam_no, beam_id in enumerate(self.beam_list[fraction_no]):
                current_beam_path = os.path.join(self.logfile_dir, fraction_id, beam_id)
                os.chdir(current_beam_path)
                while len(os.listdir('.')) <= 3:
                    os.chdir(os.listdir('.')[0])
                
                for file in os.listdir('.'):
                    if file.__contains__('beam.'):
                        beam_file = file
                with open(beam_file, 'r') as beam_file:
                    for line in beam_file.readlines():
                            if line.__contains__('PatientId'):
                                self.patient_id = int(line.split('>')[1].split('<')[0])
        
        record_df_exists = False
        tuning_df_exists = False
        for dirpath, dirnames, filenames in os.walk(os.path.join(self.logfile_dir, '..')):
            for fname in filenames:
                if fname.__contains__(f'{self.patient_id}_records') and fname.endswith('.csv'):
                    self.record_df_name = fname
                    print(f'''Found patient record dataframe '{self.record_df_name}', reading in..''')
                    self.patient_record_df = pd.read_csv(os.path.join(dirpath, fname), index_col='TIME', dtype={'BEAM_ID': str})
                    record_df_exists = True
                elif fname.__contains__(f'{self.patient_id}_tunings') and fname.endswith('.csv'):
                    self.tuning_df_name = fname
                    print(f'''Found patient tuning dataframe '{self.tuning_df_name}', reading in..''')
                    self.patient_tuning_df = pd.read_csv(os.path.join(dirpath, fname), index_col='TIME')
                    tuning_df_exists = True
        
        if not record_df_exists or not tuning_df_exists:
            print(f'''\nUnable to locate patient record/tuning dataframes.\nPlease run MachineLog.prepare_dataframe()''')                
        
        os.chdir(self.logfile_dir)
        
    def summarize_beams(self):
        print(f'Total {self.num_fractions} fractions in {self.logfile_dir}\n')
        for index, fraction in enumerate(self.fraction_list):
            print(f'[{index + 1}] - {fraction}')
            for beam in self.beam_list[index]:
                print('\t', beam)
    
    def prepare_dataframe(self):
        if not self.patient_record_df.empty and not self.patient_tuning_df.empty:
            print('Function call unnecessary, already read existing patient record/tuning dataframes:')
            print(f'  {self.record_df_name}\n  {self.tuning_df_name}')
            return None

        print(f'Initializing dataframe for patient-ID {self.patient_id}..')
        for fraction_no, fraction_id in enumerate(self.fraction_list):
            for beam_no, beam_id in enumerate(self.beam_list[fraction_no]):
                current_beam_path = os.path.join(self.logfile_dir, fraction_id, beam_id)
                os.chdir(current_beam_path)
                while len(os.listdir('.')) <= 3:
                    os.chdir(os.listdir('.')[0])

                map_records, tunings = [], []
                for file in os.listdir('.'):
                    if file.__contains__('beam.'):
                        beam_file = file
                    elif file.__contains__('beam_config.'):
                        beam_config = file
                    elif file.__contains__('map_record') and file.__contains__('part'):
                        map_records.append(file)
                    elif file.__contains__('map_record') and file.__contains__('tuning'):
                        tunings.append(file)
                
                if len(map_records) == 0 or len(tunings) == 0:
                    raise LookupError('No logfiles found!') 

                num_layers = max([int(fname.split('_')[2].split('_')[0]) for fname in map_records])

                with open(beam_file, 'r') as beam_file:
                    for line in beam_file.readlines():
                        if line.__contains__('GantryAngle'):
                            gantry_angle = float(line.split('>')[1].split('<')[0])
                        elif line.__contains__('pressure'):
                            pressure = float(line.split(',')[-1])
                        elif line.__contains__('temperature'):
                            temperature = float(line.split(',')[-1])
                
                    ref_pressure, ref_temperature = 1013., 293.
                    correction_factor = (ref_pressure * temperature) / (ref_temperature * pressure)
                    beam_file.close()
                
                for layer_id in range(num_layers):
                    to_do_layers, to_do_tunings = [], []
                    for record_file in map_records:
                        if int(record_file.split('_')[2].split('_')[0]) == layer_id:
                            record_file_df = pd.read_csv(record_file, delimiter=',', skiprows=10, skipfooter=11, engine='python')
                            record_file_df['TIME'] = pd.to_datetime(record_file_df['TIME'])
                            record_file_df.index = record_file_df['TIME']
                            record_file_df = record_file_df.loc[:, :'Y_DOSE_RATE(A)']
                            record_file_df = record_file_df.loc[(record_file_df['X_WIDTH(mm)'] != -10000.0) & (record_file_df['Y_WIDTH(mm)'] != -10000.0) & (record_file_df['X_POSITION(mm)'] != -10000.0) & (record_file_df['Y_POSITION(mm)'] != -10000.0)]
                            record_file_df.drop(columns=['TIME'], inplace=True)
                            current_spot_submap = record_file_df['SUBMAP_NUMBER'].min()
                            current_spot_id = 0
                            record_file_df['SPOT_ID'] = 0
                            while current_spot_submap <= record_file_df['SUBMAP_NUMBER'].max():
                                record_file_df.loc[record_file_df['SUBMAP_NUMBER'] == current_spot_submap, ['SPOT_ID']] = current_spot_id
                                current_spot_submap = record_file_df.loc[record_file_df['SUBMAP_NUMBER'] > current_spot_submap]['SUBMAP_NUMBER'].min()
                                current_spot_id += 1
                            
                            record_file_df.reindex()
                            to_do_layers.append(record_file_df)

                    for tuning_file in tunings:
                        if int(tuning_file.split('_')[2].split('_')[0]) == layer_id:
                            tuning_file_df = pd.read_csv(tuning_file, delimiter=',', skiprows=10, skipfooter=11, engine='python')
                            tuning_file_df['TIME'] = pd.to_datetime(tuning_file_df['TIME'])
                            tuning_file_df.index = tuning_file_df['TIME']
                            tuning_file_df = tuning_file_df.loc[:, :'Y_DOSE_RATE(A)']
                            tuning_file_df = tuning_file_df.loc[(tuning_file_df['X_WIDTH(mm)'] != -10000.0) & (tuning_file_df['Y_WIDTH(mm)'] != -10000.0) & (tuning_file_df['X_POSITION(mm)'] != -10000.0) & (tuning_file_df['Y_POSITION(mm)'] != -10000.0)]
                            tuning_file_df.drop(columns=['TIME'], inplace=True)
                            current_spot_submap = tuning_file_df['SUBMAP_NUMBER'].min()
                            current_spot_id = 0
                            tuning_file_df['SPOT_ID'] = 0
                            tuning_file_df.reindex()
                            while current_spot_submap <= tuning_file_df['SUBMAP_NUMBER'].max():
                                tuning_file_df.loc[tuning_file_df['SUBMAP_NUMBER'] == current_spot_submap, ['SPOT_ID']] = current_spot_id
                                current_spot_submap = tuning_file_df.loc[tuning_file_df['SUBMAP_NUMBER'] > current_spot_submap]['SUBMAP_NUMBER'].min()
                                current_spot_id += 1

                            tuning_file_df.reindex()
                            to_do_tunings.append(tuning_file_df)
                    
                    for i in range(len(to_do_tunings)):
                        if i > 0:
                            to_do_tunings[i]['SUBMAP_NUMBER'] += to_do_tunings[i - 1]['SUBMAP_NUMBER'].max()
                            to_do_tunings[i]['SPOT_ID'] += (to_do_tunings[i - 1]['SPOT_ID'].max() + 1)
                    for j in range(len(to_do_layers)):
                        if j > 0:
                            to_do_layers[j]['SPOT_ID'] += (to_do_layers[j - 1]['SPOT_ID'].max() + 1)
                    
                    layer_df = pd.concat(to_do_layers)
                    layer_df['LAYER_ID'] = layer_id
                    layer_df['TOTAL_LAYERS'] = num_layers
                    layer_df['BEAM_ID'] = beam_id
                    layer_df['GANTRY_ANGLE'] = gantry_angle
                    layer_df['FRACTION_ID'] = fraction_id
                    layer_df['PATIENT_ID'] = self.patient_id
                    tuning_df = pd.concat(to_do_tunings)
                    tuning_df['LAYER_ID'] = layer_id
                    tuning_df['TOTAL_LAYERS'] = num_layers
                    tuning_df['BEAM_ID'] = beam_id
                    tuning_df['GANTRY_ANGLE'] = gantry_angle
                    tuning_df['FRACTION_ID'] = fraction_id
                    tuning_df['PATIENT_ID'] = self.patient_id
                    del to_do_layers, to_do_tunings
                    
                    if self.patient_record_df.empty:
                        self.patient_record_df = layer_df
                        self.patient_tuning_df = tuning_df
                    else:
                        self.patient_record_df = pd.concat([self.patient_record_df, layer_df])    
                        self.patient_tuning_df = pd.concat([self.patient_tuning_df, tuning_df])
                    
                    del layer_df, tuning_df
    
                os.chdir(self.logfile_dir) 

            print(f'  ..Fraction {str(fraction_no + 1).zfill(2)}/{str(self.num_fractions).zfill(2)} complete..') 

        df_destination = r'N:\fs4-HPRT\HPRT-Docs\Lukas\Logfile_Extraction\dataframes'
        os.chdir(df_destination)
        print(f'''  ..Writing dataframe to '{df_destination}' as .CSV.. ''')
        self.patient_record_df.to_csv(f'patient_{self.patient_id}_records_data.csv')
        self.patient_tuning_df.to_csv(f'patient_{self.patient_id}_tunings_data.csv')
        print('Complete')
    
    def plot_beam_layers(self):
        beam_list = self.patient_record_df['BEAM_ID'].drop_duplicates()
        indices = beam_list.index.to_list()
        print('Key\tBeam-ID\t\tIn Fraction\tLayers\n')
        for choice, (index, beam) in enumerate(zip(indices, beam_list)):
            num_layers = int(self.patient_record_df['TOTAL_LAYERS'][index].mean())
            fraction = int(self.patient_record_df['FRACTION_ID'][index].mean())
            print(f'({choice + 1})\t{beam}\t\t{fraction}\t{num_layers}')

        while True:
            try:
                key = int(input('\n Select beam key: '))
                if key > len(beam_list):
                    print('Key out of bounds, select another..')
                    continue
                else:
                    break
            except:
                pass

        print('Selected beam is:', beam_list[key - 1])

        # for beam in beam_list:
        #     print(beam_list.index[beam_list['BEAM_ID'] == beam])
            
        # scope_recorf_df = self.patient_record_df.loc[self.patient_record_df['BEAM_ID' == beam_id]]

        
class Beam(MachineLog):
    def __init__(self, log, fraction_id, beam_id) -> None:
        current_beam_path = os.path.join(log.logfile_dir, fraction_id, beam_id)
        os.chdir(current_beam_path)
        while len(os.listdir('.')) <= 3:
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

        self.num_layers = max([int(fname.split('_')[2].split('_')[0]) for fname in self.map_records])
        
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

    def collect_data(self, layers='all', plot=False, drop=True):
        self.layer_spot_data, self.layer_tuning_data = [], []
        if str(layers) == 'all':
            layers = range(self.num_layers)
        elif int(layers) > self.num_layers - 1:
            print(f'Selected layer-ID [{layers}] exceeds highest layer-ID [{self.num_layers - 1}], using max. value instead..')
            layers = [self.num_layers - 1]
        else:
            layers = [int(layers)]
            
        for layer_id in layers:
            to_do_layers, to_do_tunings = [], []
            for file in self.map_records:
                if int(file.split('_')[2].split('_')[0]) == layer_id:
                    to_do_layers.append(pd.read_csv(file, delimiter=',', skiprows=10, skipfooter=11, engine='python'))

            for file in self.tunings:
                if int(file.split('_')[2].split('_')[0]) == layer_id:
                    to_do_tunings.append(pd.read_csv(file, delimiter=',', skiprows=10, skipfooter=11, engine='python'))
            
            for i in range(len(to_do_tunings)):
                if i > 0:
                    to_do_tunings[i]['SUBMAP_NUMBER'] += to_do_tunings[i - 1]['SUBMAP_NUMBER'].max()
            for j in range(len(to_do_layers)):
                if j > 0:
                    to_do_layers[j]['SUBMAP_NUMBER'] += to_do_layers[j - 1]['SUBMAP_NUMBER'].max()
            
            layer_df = pd.concat(to_do_layers)
            tuning_df = pd.concat(to_do_tunings)
            del to_do_layers, to_do_tunings

            layer_df['TIME'] = pd.to_datetime(layer_df['TIME'])
            layer_df.index = layer_df['TIME']
            layer_beamtime = layer_df['TIME'].iloc[-1] - layer_df['TIME'].iloc[0]
            layer_df = layer_df.loc[:, :'Y_DOSE_RATE(A)']
            layer_df = layer_df.loc[(layer_df['X_WIDTH(mm)'] != -10000.0) & (layer_df['Y_WIDTH(mm)'] != -10000.0) & (layer_df['X_POSITION(mm)'] != -10000.0) & (layer_df['Y_POSITION(mm)'] != -10000.0)]
            layer_df.drop(columns=['TIME'], inplace=True)
            tuning_df['TIME'] = pd.to_datetime(tuning_df['TIME'])
            tuning_df.index = tuning_df['TIME']
            tuning_beamtime = tuning_df['TIME'].iloc[-1] - tuning_df['TIME'].iloc[0]
            tuning_df = tuning_df.loc[:, :'Y_DOSE_RATE(A)']
            tuning_df = tuning_df.loc[(tuning_df['X_WIDTH(mm)'] != -10000.0) & (tuning_df['Y_WIDTH(mm)'] != -10000.0) & (tuning_df['X_POSITION(mm)'] != -10000.0) & (tuning_df['Y_POSITION(mm)'] != -10000.0)]
            tuning_df.drop(columns=['TIME'], inplace=True)
            
            spot_dfs, tuning_dfs = [], []
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
        
        if plot:
            print('  ..Drawing..')
            fig, axs = plt.subplots(7, 7, sharex=True, sharey=True, figsize=(24, 24), dpi=150)
            ax0 = fig.add_subplot(111, frameon=False)
            fig.subplots_adjust(hspace=0.0, wspace=0.0)
            axs = axs.ravel()
            for index, layer in enumerate(self.layer_spot_data):
                layer_x_means, layer_y_means = [], []
                layer_x_stds, layer_y_stds = [], []
                tuning_x_means, tuning_y_means= [], []
                tuning_x_stds, tuning_y_stds = [] ,[]
                for spot in layer:
                    layer_x_means.append(spot['X_POSITION(mm)'].mean())
                    layer_x_stds.append(spot['X_POSITION(mm)'].std())
                    layer_y_means.append(spot['Y_POSITION(mm)'].mean())
                    layer_y_stds.append(spot['Y_POSITION(mm)'].std())
                for spot in self.layer_tuning_data[index]:
                    tuning_x_means.append(spot['X_POSITION(mm)'].mean())
                    tuning_x_stds.append(spot['X_POSITION(mm)'].std())
                    tuning_y_means.append(spot['Y_POSITION(mm)'].mean())
                    tuning_y_stds.append(spot['Y_POSITION(mm)'].std())

                axs[index].plot(layer_x_means, layer_y_means)
                axs[index].plot(layer_x_means[0], layer_y_means[0], 'o', markeredgewidth=0.1, color='black', markerfacecolor='none')
                # axs[index].quiver(layer_x_means[:1], layer_y_means[:1], layer_x_means[1]-layer_x_means[0], layer_y_means[1]-layer_y_means[0])#, scale_units='xy', angles='xy', scale=1)
                axs[index].plot(layer_x_means, layer_y_means, '.', markersize=2.0, color='black', label=f'spots')
                axs[index].plot(tuning_x_means, tuning_y_means, '.', markersize=2.0, color='limegreen', label=f'tunings')
                if index == int(len(self.layer_spot_data) / 2):
                    axs[index].set_xlim(np.median(layer_x_means) - 50, np.median(layer_x_means) + 50)
                    axs[index].set_ylim(np.median(layer_y_means) - 50, np.median(layer_y_means) + 50)
                # axs[index].errorbar(layer_x_means, layer_y_means, xerr=layer_x_stds, yerr=layer_y_stds)  #, xerr=layer_x_stds, yerr=layer_y_stds)
                axs[index].legend(loc='upper right')
                axs[index].annotate(f'Layer #{str(index + 1).zfill(2)}', xy=(1.0, 1.0), xycoords='axes points', fontsize=10)
            plt.suptitle(f'Spot Positions for Beam-ID: {self.beam_id} in Fraction: {self.fraction_id}', fontweight='bold', y=0.9)
            ax0.set_xlabel('X', fontweight='bold', labelpad=10)
            ax0.set_ylabel('Y', fontweight='bold', labelpad=10)
            plt.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
            output_dir = r'N:\fs4-HPRT\HPRT-Docs\Lukas\Logfile_Extraction\output'
            if not os.path.isdir(output_dir):
                os.mkdir(output_dir)
            try:
                plt.savefig(f'{output_dir}/{self.fraction_id}_{self.beam_id}_spots.pdf')
            except PermissionError:
                print(f'  Permission denied, no plot generated')
            
            plt.cla()
            plt.close(fig)
        
        if drop:
            dfs_to_join = []
            for layer_id in range(self.num_layers):
                for spot_id, spot in enumerate(self.layer_spot_data[layer_id]):
                    self.layer_spot_data[layer_id][spot_id]['FRACTION_ID'] = self.fraction_id
                    self.layer_spot_data[layer_id][spot_id]['BEAM_ID'] = self.beam_id
                    self.layer_spot_data[layer_id][spot_id]['LAYER_ID'] = layer_id
                    self.layer_spot_data[layer_id][spot_id]['SPOT_ID'] = spot_id
                
                dfs_to_join.append(pd.concat(self.layer_spot_data[layer_id]))
            log.fraction_beam_dfs.append(pd.concat(dfs_to_join))


if __name__ == '__main__':
    log = MachineLog()
    log.prepare_dataframe()
    # log.summarize_beams()
    # log.plot_beam_layers()
    sys.exit()

    out_dir = r'N:\fs4-HPRT\HPRT-Docs\Lukas\Logfile_Extraction\output'

    beam_id = '07'
    layer_id = 12
    spot_id = 20

    df = log.patient_record_df
    df = log.patient_record_df.loc[(df['BEAM_ID'] == beam_id) & (df['LAYER_ID'] == layer_id)]
    df.plot(
        # x=log.patient_record_df.loc[
        #         (log.patient_record_df['FRACTION_ID'] == 20191118) 
        #         & (log.patient_record_df['BEAM_ID'] == 5) 
        #         & (log.patient_record_df['LAYER_ID'] == 10)]['X_POSITION(mm)'],
        # y=log.patient_record_df.loc[
        #         (log.patient_record_df['FRACTION_ID'] == 20191118) 
        #         & (log.patient_record_df['BEAM_ID'] == 5) 
        #         & (log.patient_record_df['LAYER_ID'] == 10)]['Y_POSITION(mm)'],
        x='X_POSITION(mm)',
        y='Y_POSITION(mm)',
        kind='scatter',
        s=20.0, 
        facecolors='none', 
        edgecolors='black',
        linewidth=0.5,
        # markeredgewidth=1.0
    )
    plt.title(f'Layer #{layer_id} of Beam-ID {beam_id} over {log.num_fractions} Fractions', fontweight='bold')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')
    plt.savefig(out_dir + f'/{log.patient_id}_beam_{beam_id}_layer_{layer_id}_scatter.pdf')
    plt.show()

    df = log.patient_record_df.loc[(log.patient_record_df['BEAM_ID'] == beam_id) & (log.patient_record_df['LAYER_ID'] == layer_id) & (log.patient_record_df['SPOT_ID'] == spot_id)]['X_POSITION(mm)']
    df.plot.hist(
        edgecolor='black',
        bins=10,
        label=f'Spot #{spot_id}\nmean = {df.mean():.3f} mm\nstdev = {df.std():.3f} mm'
    )
    df.plot.kde(
        label='Density estimate'
    )
    plt.title(f'Layer #{layer_id} of Beam-ID {beam_id} over {log.num_fractions} Fractions', fontweight='bold')
    plt.xlabel('X [mm]')
    plt.legend()
    plt.savefig(out_dir + f'/{log.patient_id}_beam_{beam_id}_layer_{layer_id}_spot_{spot_id}_hist.pdf')
    plt.show()
    plt.clf()


    
    
