"""File: auto_threshold.py >>> localize radiochromic film in transmission scan and return average pixel values"""
import os
import sys
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import cv2
from tkinter import filedialog
from tkinter import *


#############################################
# FUNCTIONS
#############################################


def get_scan_data():
    data = []
    successful = False
    while not successful:
        try:
            target_dir = filedialog.askdirectory()
            os.chdir(target_dir)
        except OSError:
            sys.exit('Process cancelled by user. Exiting..')

        for file in os.listdir():
            if file.endswith('.tif'):
                data.append(file)
        if not data:
            prompt = input(f'''Directory '{target_dir}' does not contain any .TIF files. Select new dir [y/n]? ''')
            if prompt == 'y':
                pass
            else:
                sys.exit('Process cancelled by user. Exiting..')
        else:
            successful = True

    return data


def pre_process(channel, margin):
    dimY, dimX = np.shape(channel)
    processed = channel[margin:dimY - margin, margin:dimX - margin]

    return processed


def auto_threshold(scan, thresh):
    image = cv2.imread(scan)
    B, G, R = cv2.split(image)
    RGB = [R, G, B]
    for i in range(len(RGB)):
        RGB[i] = pre_process(RGB[i], margin=100)

    dimY, dimX = np.shape(RGB[0])
    centerY, centerX = int(dimY / 2), int(dimX / 2)

    yLowers, yUppers, xLowers, xUppers = [], [], [], []
    for channel in RGB:
        for x, px in enumerate(channel[centerY, :]):
            if px >= thresh:
                xUpper = x
        for x, px in enumerate(channel[centerY, :centerX]):
            if px < thresh:
                xLower = x

        for y, px in enumerate(channel[:, centerX]):
            if px >= thresh:
                yUpper = y
        for y, px in enumerate(channel[:centerY, centerX]):
            if px < thresh:
                yLower = y

        xLowers.append(xLower)
        xUppers.append(xUpper)
        yLowers.append(yLower)
        yUppers.append(yUpper)

    X1 = int(np.average(xLowers))
    X2 = int(np.average(xUppers))
    Y1 = int(np.average(yLowers))
    Y2 = int(np.average(yUppers))

    for i in range(len(RGB)):
        RGB[i] = RGB[i][Y1:Y2, X1:X2]

    return RGB


def analyze_area(scan, channels, edge, dpi, writePNG):
    halfROI = int(edge / (2 * 2.54) * dpi)
    dimY, dimX = np.shape(channels[0])
    centerY, centerX = int(dimY / 2), int(dimX / 2)

    if writePNG:
        recon = cv2.merge((channels[0], channels[1], channels[2]))
        recon = cv2.rectangle(recon, (centerX + halfROI, centerY + halfROI), (centerX - halfROI, centerY - halfROI),
                              (255, 255, 255), 2)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5), gridspec_kw={'width_ratios': [1, 1.045]})
        ax1.imshow(recon)
        ax1.text(centerX, centerY, f'Averaging ROI\n\n[{edge}cm]', fontsize=12, fontweight='bold',
                 ha='center', va='center', color='white')
        ax1.set_title('Cropped RGB Original')

    channelsAVG_DEV = []
    for i in range(len(channels)):
        channels[i] = channels[i][centerY - halfROI:centerY + halfROI, centerX - halfROI:centerX + halfROI]
        channelsAVG_DEV.append(str(round(np.average(channels[i]), 3)) + str('\t') + str(round(np.std(channels[i]), 3)))

    ROIdir = f'''{scan.split('_')[0]}_ROIs'''
    if str(ROIdir).__contains__('.'):
        ROIdir = f'''{scan.split('0')[0]}_ROIs'''
    try:
        os.mkdir(ROIdir)
    except OSError:
        pass

    if writePNG:
        print(f'''Writing PNG file to '{ROIdir}/{str(scan).split('.')[0]}_ROI.png' ''')
        redAVG = np.average(channels[0])
        labels = ['AVG', '+5%', '-5%']
        locs = [redAVG, redAVG + 0.05 * redAVG, redAVG - 0.05 * redAVG]
        zoom = ax2.imshow(channels[0], vmin=redAVG - 0.05 * redAVG, vmax=redAVG + 0.05 * redAVG, cmap='inferno_r')
        divider = make_axes_locatable(ax2)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        cb = fig.colorbar(zoom, cax=cax, orientation='vertical')
        cb.set_ticks(locs)
        cb.set_ticklabels(labels)
        ax2.set_title('Averaging ROI')
        fig.suptitle(f'''EBT3 Film #{str(scan).split('.')[0]} [ROI={edge}cm, RES={dpi}dpi]''', fontweight='bold')
        ax2.text(halfROI, halfROI, f'Red Channel', fontsize=12, fontweight='bold',
                 ha='center', va='center', color='white')
        fig.tight_layout()
        plt.savefig(f'''{ROIdir}/{str(scan).split('.')[0]}_ROI.png''', dpi=dpi)
        plt.close(fig)
    else:
        pass

    return channelsAVG_DEV


def write_data(scans, RGBaverages):
    target_name = scans[0].split('_')[0] + str('_RGB_values.txt')
    if target_name.__contains__('.'):
        target_name = scans[0].split('0')[0] + str('_RGB_values.txt')
    if os.path.isfile(target_name):
        continue_y_n = input(f'''\nTarget '{target_name}' exists. Overwrite [y/n]? ''')
        if continue_y_n == 'y':
            os.remove(target_name)
        else:
            sys.exit('Write to target cancelled by user, exiting..\n')

    header = 'No./MU\tR\tu(R)\tG\tu(G)\tB\tu(B)\n'
    with open(target_name, 'w+') as target:
        target.write(header)
        target.close()

    for fname, results in zip(scans, RGBaverages):
        with open(target_name, 'a') as target:
            if str(fname).__contains__('.'):
                target.write(f'''{str(fname).split('.')[0]}\t''')
            else:
                target.write(f'''{str(fname).split('_')[1]}\t''')

            for i in range(3):
                if i < 2:
                    target.write(f'{results[i]}\t')
                else:
                    target.write(f'{results[i]}\n')

        target.close()


#############################################
# MAIN LOOP
#############################################


scan_data = get_scan_data()
scan_results = []

print(f'Found {len(scan_data)} .TIF files. Begin auto-thresholding..')
for scan in scan_data:
    RGB_cropped = auto_threshold(scan, thresh=30)
    RGB_means_devs = analyze_area(scan, RGB_cropped, edge=4, dpi=150, writePNG=True)
    scan_results.append(RGB_means_devs)

print('>> DONE')

write_data(scan_data, scan_results)