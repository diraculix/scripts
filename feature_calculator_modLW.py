############################Start program author information################################
#******************************************************************************************#
#******************************************************************************************#
#******************Title: Feature Calculator (All-in-One)**********************************#
#******************Author: Marvin Reimold (marvin.reimold@psi.ch)**************************#
#******************Author: Arturs Meijers (arturs.meijers@psi.ch)**************************#
#******************Author: Francesco Fracchiolla (francesco.fracchiolla@apss.tn.it)********#
#******************Datum: 06.12.2025*******************************************************#
#******************Version: 6.0************************************************************#
#******************************************************************************************#
#******************************************************************************************#
##############################End program author information################################


#############################Start User Configurable Parameters#############################
#******************************************************************************************#
# ======================================================================================== #
# 1. GLOBAL SETTINGS & FILE PATHS
# (These parameters are required for ALL features)
# ======================================================================================== #
# Define the full path to the main treatment folder.
# Script expects subfolders: "..._spots", "..._logs", "CT", "Structure_set" inside this path.
PATH_TREATMENT = r"Q:\PHYSIK\PROTONEN\Studien_Forschungsprojekte\RION\Patienten_Datenanalyse\RION-UKD004\Feature-Calculation"

# Memory Management:
# True = Faster but requires more RAM (loads all dose grids at once).
# False = Slower but works on computers with less RAM (reads files one by one).
PRELOAD_DOSE_GRIDS_IN_MEMORY = False


# ======================================================================================== #
# 2. FEATURE SELECTION SWITCHBOARD
# (Set flags to True/False to enable specific calculations)
# ======================================================================================== #
FEATURES_TO_CALCULATE = {
    # --- Group A: Data Preparation (Run these first) ---
    "Export_Matched_Timeline": False,    # Creates 'matched_spot_time_info.txt'
    "Calculate_Spot_Dose_Rates": False,  # Creates 'DR_*.dcm' files (Required for Group B & C)
    
    # --- Group B: Organ Specific Text Export (CSV) ---
    # This single switch exports BOTH Physical Dose (Gy) and LET (keV/um) csv files
    "Export_Organ_Physical_Dose_and_LET_CSV": True, 

    # --- Group C: 3D DICOM Map Generation ---
    "GLOBAL_VWMDR": True,                    # Global Voxel-Wise Max Dose Rate
    "Dose_Above_Dose_Rate_TI": True,         # Dose accumulated above rate threshold (Time Interval)
    "Global_VWMDR_TI": True,                 # Max Dose Rate over specific Time Intervals
    "Dose_Above_Dose_Rate": True,           # Dose accumulated above rate threshold (per spot)
    "Dose_Above_LET": True,                 # Dose accumulated above LET threshold (per spot)
    "Variable_RBE_Plan_Dose": True,         # Plan Dose weighted by LET
    "VRBE_Dose_Above_VRBE_Dose_Rate": True, # vRBE Dose above vRBE Rate threshold
}


# ======================================================================================== #
# 3. FEATURE-SPECIFIC PARAMETERS
# (Only modify sections relevant to the features enabled above)
# ======================================================================================== #

# ---------------------------------------------------------------------------------------- #
# [A] ORGAN EXPORT CONFIGURATION
# Used by: "Export_Organ_Physical_Dose_and_LET_CSV"
# ---------------------------------------------------------------------------------------- #
# List the exact ROI names (case-sensitive, each entry in "") from the Structure Set (.dcm) to export.
STRUCTURES_TO_EXPORT = ["OpticNerve_L", "OpticNerve_R", "Chiasm"]

# Number of CPU cores to use for parallel extraction (Higher is faster).
NUMBER_CPUS = 12


# ---------------------------------------------------------------------------------------- #
# [B] DOSE RATE THRESHOLD CONFIGURATION
# Used by: "Dose_Above_Dose_Rate", "Dose_Above_Dose_Rate_TI"
# ---------------------------------------------------------------------------------------- #
# The thresholds (in Gy/s) to check against.
# A separate DICOM file will be generated for every value in this list, separate numbers by commas.
DOSE_RATE_THRESHOLDS = [2]


# ---------------------------------------------------------------------------------------- #
# [C] TIME INTERVAL CONFIGURATION
# Used by: "Global_VWMDR_TI", "Dose_Above_Dose_Rate_TI"
# ---------------------------------------------------------------------------------------- #
# The sliding window sizes (in milliseconds) to analyze, separate numbers by commas.
TIME_INTERVALS_MS = [20, 50]

# The step size (in milliseconds) for the sliding window integration.
# Smaller steps = higher precision but slower calculation.
TIME_STEP_MS = 10


# ---------------------------------------------------------------------------------------- #
# [D] RBE & LET CONFIGURATION
# Used by: "Variable_RBE_Plan_Dose", "VRBE_Dose_Above_VRBE_Dose_Rate"
# ---------------------------------------------------------------------------------------- #
# Linear scaling factor for LET to RBE conversion.
LET_SCALER = 0.1

# Thresholds (in Gy(RBE)/s) for the Variable RBE features.
VRBE_DOSE_RATE_THRESHOLDS = [2]

# ---------------------------------------------------------------------------------------- #
# [E] DOSE ABOVE LET CONFIGURATION  <--- [NEW SECTION]
# Used by: "Dose_Above_LET"
# ---------------------------------------------------------------------------------------- #
# The thresholds (in keV/um) to check against.
# Accumulates dose only where the LET exceeds these values.
LET_THRESHOLDS = [3, 5, 7]

# ======================================================================================== #
# 4. LOG FILE & MATCHING CONFIGURATION
# (Technical settings for aligning Plan to Machine Logs. Rarely needs changing.)
# Used by: ALL FEATURES (This is the core timing engine)
# ======================================================================================== #
# Tolerances for matching a planned spot to a log record.
SPOT_POSITION_TOLERANCE_MM = 3.0
MU_TOLERANCE = 0.1
ENERGY_TOLERANCE_MEV = 0.5

# Machine Log File CSV settings.
LOG_FILE_HEADER_ROWS = 0
LOG_COLUMN_X = 'X Position [mm]'
LOG_COLUMN_Y = 'Y Position [mm]'
LOG_COLUMN_ENERGY = 'Energy [MeV]'
LOG_COLUMN_MU = 'Monitor Units [MU]'
LOG_COLUMN_START_TIME = 'Start Time'
LOG_COLUMN_DURATION = 'Duration [ms]'
LOG_FILE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S:%f'

#******************************************************************************************#
##############################End User Configurable Parameters##############################


##################################Start importing packages##################################
#*********************************Import packages******************************************#
import os
import pydicom as dicom
import glob
import numpy as np
import sys
import pandas as pd
import re
from tqdm import tqdm
from pydicom.uid import generate_uid
import SimpleITK as sitk
from scipy.ndimage import shift
from rt_utils import RTStructBuilder
import multiprocessing as mp
from pathlib import Path
#******************************************************************************************#
####################################End importing packages##################################


##################################Start definition functions################################

#******************Helper: CT and Structure Processing*************************************#
def read_in_ct_data(path_ct_dicom_series):
    """ Reads CT DICOM series to establish geometry for resampling. """
    dsCTs = []
    for pathCTDicom in Path(path_ct_dicom_series).iterdir():
        if pathCTDicom.suffix == '.dcm':
            dsCTs.append(dicom.dcmread(pathCTDicom))
    
    # 1. Sort slices by Instance Number
    dsCTs.sort(key=lambda x: float(x.ImagePositionPatient[2]))
    
    # 2. Calculate Spacing (MUST BE POSITIVE)
    pixel_spacing_x = float(dsCTs[0].PixelSpacing[1]) # Swap X/Y for SimpleITK
    pixel_spacing_y = float(dsCTs[0].PixelSpacing[0])
    
    # Calculate Z vector between first two slices
    origin0 = np.array([float(x) for x in dsCTs[0].ImagePositionPatient])
    
    if len(dsCTs) > 1:
        origin1 = np.array([float(x) for x in dsCTs[1].ImagePositionPatient])
        z_vector = origin1 - origin0
        z_spacing = np.linalg.norm(z_vector)
        
        # Compute the normalized Z direction vector
        z_direction_norm = z_vector / z_spacing
    else:
        # Fallback for single slice
        z_spacing = float(dsCTs[0].SliceThickness)
        # Assume standard Z direction if cannot be calculated
        z_direction_norm = np.array([0.0, 0.0, 1.0])

    ctSpacing = [pixel_spacing_x, pixel_spacing_y, z_spacing]

    # 3. Construct Direction Matrix
    # DICOM ImageOrientationPatient gives the X and Y direction vectors of the slice
    orient = [float(x) for x in dsCTs[0].ImageOrientationPatient]
    dir_x = np.array(orient[:3])
    dir_y = np.array(orient[3:])
    dir_z = z_direction_norm
    
    # Flatten into the 9-element tuple SimpleITK expects (X, Y, Z components)
    ctDirection = (
        dir_x[0], dir_x[1], dir_x[2],
        dir_y[0], dir_y[1], dir_y[2],
        dir_z[0], dir_z[1], dir_z[2]
    )

    ctImagePositionPatientMin = [float(each) for each in dsCTs[0].ImagePositionPatient]
    ctImagePositionPatientMax = [float(each) for each in dsCTs[-1].ImagePositionPatient]
    
    ctArray = []     
    for dsCT in dsCTs:
        ctArray.append(dsCT.pixel_array * dsCT.RescaleSlope + dsCT.RescaleIntercept)
    ctArray = np.array(ctArray)
    
    return ctArray, ctSpacing, ctImagePositionPatientMin, ctImagePositionPatientMax, ctDirection

def resize_dicom_dose_image(ctArray_shape, doseArray, doseSpacing, ctSpacing, 
                            doseImagePositionPatient, ctImagePositionPatientMin, 
                            doseDirection, ctDirection):
    """ Resamples a dose/LET grid to match the CT geometry using SimpleITK. """
    
    # 1. Setup SOURCE (Dose) Image
    doseImage = sitk.GetImageFromArray(doseArray)
    doseImage.SetOrigin(doseImagePositionPatient)
    doseImage.SetSpacing(doseSpacing)
    doseImage.SetDirection(doseDirection) # Apply correct rotation/orientation
    
    # 2. Setup TARGET (CT) Resampler
    resampler = sitk.ResampleImageFilter()
    resampler.SetOutputOrigin(ctImagePositionPatientMin)
    resampler.SetOutputSpacing(ctSpacing)
    resampler.SetOutputDirection(ctDirection) # Ensure output matches CT rotation
    resampler.SetSize(ctArray_shape) 
    
    # 3. Execute
    # Default is Linear Interpolation, which is appropriate for Dose.
    resampled_image = resampler.Execute(doseImage)
    
    # 4. Extract
    doseArrayResampled = sitk.GetArrayFromImage(resampled_image)
    
    return doseArrayResampled

def organ_extraction_worker(args):
    """ Worker function for multiprocessing extraction. """
    (index, indices, beamlet_name, start_time, duration, 
     base_folder, subfolder_name, file_prefix, 
     ct_shape, ct_spacing, ct_origin_min, ct_direction, mode) = args

    filename = f"{file_prefix}{beamlet_name}.dcm"
    file_path = os.path.join(base_folder, subfolder_name, filename)
    if not os.path.exists(file_path):
        return np.zeros((2 + np.shape(indices)[1]))

    ds = dicom.dcmread(file_path)
    dataArray = ds.pixel_array * ds.DoseGridScaling
    
    
    # Swap X/Y spacing for SimpleITK
    dataSpacing = [float(ds.PixelSpacing[1]), float(ds.PixelSpacing[0]), float(ds.SliceThickness)]
    dataOrigin = [float(x) for x in ds.ImagePositionPatient]
    
    # Construct Dose Direction Matrix (Source)
    # Dose grids from TPS usually have ImageOrientationPatient.
    if "ImageOrientationPatient" in ds:
        dDir = [float(x) for x in ds.ImageOrientationPatient]
        rx, ry, rz = dDir[0], dDir[1], dDir[2]
        cx, cy, cz = dDir[3], dDir[4], dDir[5]
        # Cross product for Z
        zx = ry * cz - rz * cy
        zy = rz * cx - rx * cz
        zz = rx * cy - ry * cx
        dataDirection = (rx, ry, rz, cx, cy, cz, zx, zy, zz)
    else:
        # Fallback to Identity if missing (Unlikely for valid DICOM)
        dataDirection = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    # ----------------------------------------------
    
    resampled = resize_dicom_dose_image(ct_shape, dataArray, dataSpacing, ct_spacing, 
                                        dataOrigin, ct_origin_min, dataDirection, ct_direction)
                                        
    # Advanced indexing works with numpy arrays (which indices now is)
    extracted_values = resampled[indices[0], indices[1], indices[2]]

    if mode == "PhysicalDose":
        if duration > 0:
            duration_sec = duration / 1000.0
            extracted_values = (extracted_values * duration_sec) / 1.1
        else:
            extracted_values = np.zeros_like(extracted_values)

    result_row = np.zeros((2 + np.shape(indices)[1]))
    result_row[0] = start_time
    result_row[1] = duration
    result_row[2:] = extracted_values
    return result_row

#******************Helper: Get Number of Fractions*****************************************#
def get_number_of_fractions(plan_folder):
    """
    Extracts NumberOfFractionsPlanned from the DICOM Plan file.
    Searches in 'plan' or 'Plan' subfolder.
    """
    # Attempt to locate the 'plan' folder (handling case sensitivity)
    plan_subfolder = os.path.join(plan_folder, "plan")
    if not os.path.exists(plan_subfolder):
        plan_subfolder = os.path.join(plan_folder, "Plan")

    dicom_files = glob.glob(os.path.join(plan_subfolder, '*.dcm'))
    
    if not dicom_files:
        print(f"[WARNING] No DICOM Plan file found in {plan_subfolder}. Defaulting Fractions to 'Unknown'.")
        return "Unknown"

    try:
        ds = dicom.dcmread(dicom_files[0])
        if "FractionGroupSequence" in ds and len(ds.FractionGroupSequence) > 0:
            fractions = ds.FractionGroupSequence[0].NumberOfFractionsPlanned
            print(f"  Found Number of Fractions: {fractions}")
            return fractions
        else:
            print("[WARNING] FractionGroupSequence not found in Plan. Defaulting to 1.")
            return 1
    except Exception as e:
        print(f"[ERROR] Could not read fractions from plan: {e}")
        return "Error"
#******************************************************************************************#

#******************Feature Controller: Organ Export****************************************#
def calculate_feature_organ_export(mode, spots_folder, output_folder, spot_timeline, 
                                   ct_path, struct_path, roi_list, num_cpus, num_fractions): # <--- Added num_fractions arg
    """
    Calculates organ-specific CSV exports.
    """
    print(f"\n--- Feature: Exporting Organ {mode} CSVs ---")
    ct_data = read_in_ct_data(ct_path) 
    ct_array, ct_spacing, ct_min, ct_max, ct_direction = ct_data
    ct_shape = ct_array.shape[::-1]
    
    print(f"Loading Structure Set: {os.path.basename(struct_path)}")
    rtstruct = RTStructBuilder.create_from(dicom_series_path=ct_path, rt_struct_path=struct_path)
    
    combined_indices = None
    voxel_counts = []
    valid_rois = []
    
    print("Generating voxel masks...")
    for roi in roi_list:
        try:
            mask = np.transpose(rtstruct.get_roi_mask_by_name(roi), (2,0,1))
            idxs = np.array(np.where(mask == 1))
            
            count = np.shape(idxs)[1]
            voxel_counts.append(count)
            valid_rois.append(roi)
            if combined_indices is None:
                combined_indices = idxs
            else:
                combined_indices = np.concatenate((combined_indices, idxs), axis=1)
        except Exception as e:
            print(f"Warning: Could not process ROI '{roi}'. Error: {e}")

    if combined_indices is None: return

    if mode == "PhysicalDose":
        subfolder = "Spot_Dose_Rate"
        prefix = "DR_"
        unit = "Gy"
    elif mode == "LET":
        subfolder = "Spot_LET"
        prefix = "LET_"
        unit = "keV/um"

    args_list = []
    b_names = spot_timeline['beaml_nme'].to_numpy()
    starts = spot_timeline['start_time'].to_numpy()
    durs = spot_timeline['duration'].to_numpy()

    for i in range(len(b_names)):
        args_list.append((
            i, combined_indices, b_names[i], starts[i], durs[i],
            spots_folder, subfolder, prefix,
            ct_shape, ct_spacing, ct_min, ct_max, mode
        ))

    print(f"Extracting data using {num_cpus} CPUs...")
    with mp.Pool(num_cpus) as pool:
        results = list(tqdm(pool.imap(organ_extraction_worker, args_list), total=len(b_names)))
    
    data_matrix = np.array(results)
    
    # Destination is passed explicitly via output_folder
    output_dir = output_folder
    if not os.path.exists(output_dir): os.makedirs(output_dir)
        
    col_time = ['Spot start time in ms', 'Spot time in ms']
    current_idx = 2
    for i, roi in enumerate(valid_rois):
        count = int(voxel_counts[i])
        end_idx = current_idx + count
        
        roi_z = combined_indices[0, current_idx-2:end_idx-2]
        roi_y = combined_indices[1, current_idx-2:end_idx-2]
        roi_x = combined_indices[2, current_idx-2:end_idx-2]
        col_voxels = [f'[{z+1},{y+1},{x+1}] in {unit}' for z, y, x in zip(roi_z, roi_y, roi_x)]
        
        roi_data = data_matrix[:, current_idx:end_idx]
        final_data = np.hstack((data_matrix[:, :2], roi_data))
        df = pd.DataFrame(final_data, columns=col_time + col_voxels)
        df.insert(0, 'Beamlet name', b_names)
        
        file_tag = "PhysDose_" if mode == "PhysicalDose" else prefix
        
        # --- MODIFIED: Append Fraction Count to Filename ---
        csv_name = f"{file_tag}{roi}_Fractions_{num_fractions}.csv"
        # ---------------------------------------------------

        df.to_csv(os.path.join(output_dir, csv_name), index=False)
        print(f"Saved {csv_name}")
        current_idx = end_idx
#******************************************************************************************#

#******************Feature 4: Dose Above Dose Rate (Time Interval)*************************#
def calculate_feature_dose_above_dose_rate_ti(spots_folder, output_folder, thresholds, intervals, step, spot_timeline):
    """
    Calculates accumulated dose where the sliding-window dose rate exceeds a threshold.
    """
    print(f"\n--- Calculating: Dose Above Dose Rate (Time Interval) ---")
    spot_dose_folder = os.path.join(spots_folder, "Spot_Dose")
    
    # 1. Load Dose Grids
    dose_grids = None
    if PRELOAD_DOSE_GRIDS_IN_MEMORY:
        print("Pre-loading spot dose grids...")
        dose_grids = {}
        for be_name in tqdm(spot_timeline['beaml_nme'], desc="Loading Grids"):
            path = os.path.join(spot_dose_folder, f"D_{be_name}.dcm")
            if os.path.exists(path):
                ds = dicom.dcmread(path)
                dose_grids[be_name] = ds.pixel_array * ds.DoseGridScaling
    
    # 2. Get Reference & Setup
    ref_dcm = dicom.dcmread(os.path.join(spot_dose_folder, f"D_{spot_timeline['beaml_nme'].iloc[0]}.dcm"))
    grid_shape = ref_dcm.pixel_array.shape
    total_time = spot_timeline['end_time'].max()
    
    if not os.path.exists(output_folder): os.makedirs(output_folder)

    # 3. Processing Loop
    for interval_ms in intervals:
        print(f"\n  Processing Interval Window: {interval_ms} ms")
        interval_s = interval_ms / 1000.0
        
        # Initialize one accumulator grid per threshold
        accumulators = {thresh: np.zeros(grid_shape, dtype=np.float32) for thresh in thresholds}
        
        # Iterate through time in small, discrete steps
        for t_current in tqdm(np.arange(0, total_time, step), desc=f"Int {interval_ms}ms | Step {step}ms"):
            t_next = t_current + step
            t_window_end = t_current + interval_ms
            
            # A. Calculate Dose Rate for the Window [t, t + interval]
            dose_in_window = np.zeros(grid_shape, dtype=np.float32)
            # Find spots active in the window
            window_spots = spot_timeline[(spot_timeline['start_time'] < t_window_end) & (spot_timeline['end_time'] > t_current)]
            
            for _, spot in window_spots.iterrows():
                be_name = spot['beaml_nme']
                # Calculate overlap duration
                overlap = min(t_window_end, spot['end_time']) - max(t_current, spot['start_time'])
                if overlap > 0 and spot['duration'] > 0:
                    fraction = overlap / spot['duration']
                    if PRELOAD_DOSE_GRIDS_IN_MEMORY and be_name in dose_grids:
                        dose_in_window += dose_grids[be_name] * fraction
                    else:
                        # Fallback for low-RAM mode (re-read file)
                        d_path = os.path.join(spot_dose_folder, f"D_{be_name}.dcm")
                        if os.path.exists(d_path):
                            ds = dicom.dcmread(d_path)
                            dose_in_window += (ds.pixel_array * ds.DoseGridScaling) * fraction
            
            dose_rate_map = dose_in_window / interval_s
            
            # B. Calculate Dose for the Step [t, t + step]
            # This is the actual dose delivered in this unique time slice
            dose_in_step = np.zeros(grid_shape, dtype=np.float32)
            step_spots = spot_timeline[(spot_timeline['start_time'] < t_next) & (spot_timeline['end_time'] > t_current)]
            
            for _, spot in step_spots.iterrows():
                be_name = spot['beaml_nme']
                overlap = min(t_next, spot['end_time']) - max(t_current, spot['start_time'])
                if overlap > 0 and spot['duration'] > 0:
                    fraction = overlap / spot['duration']
                    if PRELOAD_DOSE_GRIDS_IN_MEMORY and be_name in dose_grids:
                        dose_in_step += dose_grids[be_name] * fraction
                    else:
                        d_path = os.path.join(spot_dose_folder, f"D_{be_name}.dcm")
                        if os.path.exists(d_path):
                            ds = dicom.dcmread(d_path)
                            dose_in_step += (ds.pixel_array * ds.DoseGridScaling) * fraction

            # C. Accumulate
            for thresh in thresholds:
                # Add dose ONLY where the window rate exceeds threshold
                mask = np.where(dose_rate_map >= thresh, 1, 0)
                if np.any(mask):
                    accumulators[thresh] += (dose_in_step * mask)

        # 4. Save Results for this Interval
        for thresh, grid in accumulators.items():
            max_val = grid.max()
            scale = max_val / (2**16 - 1) if max_val > 0 else 1.0
            
            out_dcm = ref_dcm
            out_dcm.PixelData = (grid / scale).astype(np.uint16).tobytes()
            out_dcm.DoseGridScaling = scale
            out_dcm.SOPInstanceUID = generate_uid()

            if 'ReferencedRTPlanSequence' in out_dcm and out_dcm.ReferencedRTPlanSequence:
                out_dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()
            
            fname = f"Dose_Above_{thresh}Gys_Interval_{interval_ms}ms.dcm"
            out_path = os.path.join(output_folder, fname)
            out_dcm.save_as(out_path)
            print(f"    Saved: {fname}")
#******************************************************************************************#

#******************Feature: Dose Above LET*************************************************#
def calculate_feature_dose_above_let(spots_folder, output_folder, thresholds):
    """
    Accumulates Dose only in voxels where the LET exceeds a specific threshold.
    """
    print(f"\n--- Calculating: Dose Above LET ---")
    spot_dose_folder = os.path.join(spots_folder, "Spot_Dose")
    spot_let_folder = os.path.join(spots_folder, "Spot_LET")
    
    # Get list of all dose files
    files = glob.glob(os.path.join(spot_dose_folder, 'D_*.dcm'))
    
    if not files: 
        print("No Spot Dose files found.")
        return
        
    if not os.path.exists(output_folder): os.makedirs(output_folder)

    # Loop through each requested threshold
    for thresh in thresholds:
        acc_dose = None
        ref_dcm = None
        
        # Iterate over all spots to accumulate dose
        for path in tqdm(files, desc=f"Dose > LET {thresh} keV/um"):
            # Derive matching LET file path
            base = os.path.basename(path).replace('D_', '')
            let_path = os.path.join(spot_let_folder, 'LET_' + base)
            
            # Skip if matching LET file doesn't exist
            if not os.path.exists(let_path): continue
            
            # Read Dose and LET
            d_ds = dicom.dcmread(path)
            l_ds = dicom.dcmread(let_path)
            
            dose = d_ds.pixel_array * d_ds.DoseGridScaling
            let = l_ds.pixel_array * l_ds.DoseGridScaling
            
            # Initialize accumulator using the geometry of the first file
            if acc_dose is None:
                acc_dose = np.zeros_like(dose)
                ref_dcm = d_ds
            
            # THE CORE LOGIC:
            # Add Dose to accumulator ONLY if LET at that voxel >= Threshold
            acc_dose += (dose * (let >= thresh))
            
        # Save the result if data was processed
        if acc_dose is not None:
            max_val = acc_dose.max()
            scale = max_val / (2**16 - 1) if max_val > 0 else 1.0
            
            # Update Pixel Data
            ref_dcm.PixelData = (acc_dose / scale).astype(np.uint16).tobytes()
            ref_dcm.DoseGridScaling = scale
            ref_dcm.SOPInstanceUID = generate_uid()
            
            if 'ReferencedRTPlanSequence' in ref_dcm and ref_dcm.ReferencedRTPlanSequence:
                ref_dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

            out_name = f"Dose_Above_LET_{thresh}_keVum.dcm"
            ref_dcm.save_as(os.path.join(output_folder, out_name))
            print(f"  Saved: {out_name}")
#******************************************************************************************#

#******************Feature 0a: Export Matched Timeline*************************************#
def export_matched_timeline_file(output_folder, spot_timeline):
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    output_file_path = os.path.join(output_folder, 'matched_spot_time_info.txt')
    export_df = spot_timeline[['beaml_nme', 'start_time', 'duration']].copy()
    export_df.columns = ['Beamlet name', 'Spot start time in ms', 'Spot time in ms']
    export_df.to_csv(output_file_path, index=False)
    print(f"Successfully exported matched timeline to: {output_file_path}")

#******************Feature 0b: Calculate Spot Dose Rates***********************************#
def calculate_feature_spot_dose_rates(spots_folder, spot_timeline):
    print("\n--- Calculating: Spot Dose Rates (Generation of DR_*.dcm files) ---")
    spot_dose_folder = os.path.join(spots_folder, "Spot_Dose")
    output_folder = os.path.join(spots_folder, "Spot_Dose_Rate")
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    
    count = 0
    for index, spot in tqdm(spot_timeline.iterrows(), total=spot_timeline.shape[0], desc="Generating DR files"):
        be_name = spot['beaml_nme']
        duration_ms = spot['duration']
        input_path = os.path.join(spot_dose_folder, f"D_{be_name}.dcm")
        output_path = os.path.join(output_folder, f"DR_{be_name}.dcm")
        
        if not os.path.exists(input_path): continue
        dicom_dose = dicom.dcmread(input_path)
        dose = dicom_dose.pixel_array * dicom_dose.DoseGridScaling
        dose_rate = (dose / (duration_ms / 1000.0)) if duration_ms > 0 else np.zeros_like(dose)
        max_dr = np.max(dose_rate)
        scale = max_dr / (2**16 - 1) if max_dr > 0 else 1.0
        dicom_dose.PixelData = (dose_rate / scale).astype(np.uint16).tobytes()
        dicom_dose.DoseGridScaling = scale

        if 'ReferencedRTPlanSequence' in dicom_dose and dicom_dose.ReferencedRTPlanSequence:
            dicom_dose.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

        dicom_dose.save_as(output_path)
        count += 1
    print(f"Generated {count} Spot Dose Rate files.")

#******************Feature 1: Global VWMDR*************************************************#
def calculate_feature_global_vwmdr(spot_dose_rate_folder, output_folder):
    output_filename = "global_VWMDR_spot.dcm"
    dicom_file_list = glob.glob(os.path.join(spot_dose_rate_folder, '*.dcm'))
    if not dicom_file_list: return
    
    global_max = None
    ref_dcm = None
    for i, file_path in enumerate(tqdm(dicom_file_list, desc="Processing GLOBAL_VWMDR")):
        ds = dicom.dcmread(file_path)
        data = ds.pixel_array * ds.DoseGridScaling
        if i == 0:
            global_max = data
            ref_dcm = ds
        else:
            global_max = np.maximum(global_max, data)
            
    max_val = global_max.max()
    scale = max_val / (2**16 - 1) if max_val > 0 else 1.0
    ref_dcm.PixelData = (global_max / scale).astype(np.uint16).tobytes()
    ref_dcm.DoseGridScaling = scale
    ref_dcm.SOPInstanceUID = generate_uid()

    if 'ReferencedRTPlanSequence' in ref_dcm and ref_dcm.ReferencedRTPlanSequence:
        ref_dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

    if not os.path.exists(output_folder): os.makedirs(output_folder)
    ref_dcm.save_as(os.path.join(output_folder, output_filename))
    print(f"Saved GLOBAL_VWMDR.")

#******************Feature 2: Variable RBE Plan Dose (RESTORED)****************************#
def calculate_feature_variable_rbe_dose(plan_folder, output_folder, let_scaler):
    output_filename = "Variable_RBE_Plan_Dose.dcm"
    plan_dose_folder = os.path.join(plan_folder, "Plan_dose")
    plan_let_folder = os.path.join(plan_folder, "Plan_LET")
    
    dose_files = [f for f in glob.glob(os.path.join(plan_dose_folder, '*.dcm')) if '_Template_' not in f]
    let_files = [f for f in glob.glob(os.path.join(plan_let_folder, '*.dcm')) if '_Template_' not in f]
    
    if len(dose_files) != 1 or len(let_files) != 1:
        print("Error: Plan Dose or LET files missing/ambiguous.")
        return

    d_ds = dicom.dcmread(dose_files[0])
    l_ds = dicom.dcmread(let_files[0])
    
    phys_dose = (d_ds.pixel_array * d_ds.DoseGridScaling) / 1.1
    let = l_ds.pixel_array * l_ds.DoseGridScaling
    rbe_dose = (1 + let_scaler * let) * phys_dose
    
    max_val = rbe_dose.max()
    scale = max_val / (2**16 - 1) if max_val > 0 else 1.0
    
    d_ds.PixelData = (rbe_dose / scale).astype(np.uint16).tobytes()
    d_ds.DoseGridScaling = scale
    d_ds.SOPInstanceUID = generate_uid()
    
    if 'ReferencedRTPlanSequence' in d_ds and d_ds.ReferencedRTPlanSequence:
        d_ds.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

    if not os.path.exists(output_folder): os.makedirs(output_folder)
    d_ds.save_as(os.path.join(output_folder, output_filename))
    print("Saved Variable RBE Plan Dose.")

#******************Feature 3: Dose Above Dose Rate (RESTORED)******************************#
def calculate_feature_dose_above_dose_rate(spots_folder, output_folder, thresholds):
    spot_dose_folder = os.path.join(spots_folder, "Spot_Dose")
    spot_dr_folder = os.path.join(spots_folder, "Spot_Dose_Rate")
    files = glob.glob(os.path.join(spot_dose_folder, 'D_*.dcm'))
    
    if not files: return
    if not os.path.exists(output_folder): os.makedirs(output_folder)

    for thresh in thresholds:
        acc_dose = None
        ref_dcm = None
        for path in tqdm(files, desc=f"DADR {thresh} Gy/s"):
            base = os.path.basename(path).replace('D_', '')
            dr_path = os.path.join(spot_dr_folder, 'DR_' + base)
            if not os.path.exists(dr_path): continue
            
            d_ds = dicom.dcmread(path)
            dr_ds = dicom.dcmread(dr_path)
            
            dose = d_ds.pixel_array * d_ds.DoseGridScaling
            dr = dr_ds.pixel_array * dr_ds.DoseGridScaling
            
            if acc_dose is None:
                acc_dose = np.zeros_like(dose)
                ref_dcm = d_ds
            
            acc_dose += (dose * (dr >= thresh))
            
        if acc_dose is not None:
            max_val = acc_dose.max()
            scale = max_val / (2**16 - 1) if max_val > 0 else 1.0
            ref_dcm.PixelData = (acc_dose / scale).astype(np.uint16).tobytes()
            ref_dcm.DoseGridScaling = scale
            ref_dcm.SOPInstanceUID = generate_uid()
            
            if 'ReferencedRTPlanSequence' in ref_dcm and ref_dcm.ReferencedRTPlanSequence:
                ref_dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

            ref_dcm.save_as(os.path.join(output_folder, f"Dose_Above_{thresh}_Gys.dcm"))

#******************Feature 5: Global VWMDR TI (RESTORED)***********************************#
def calculate_feature_global_vwmdr_ti(spots_folder, output_folder, intervals, step, spot_timeline):
    spot_dose_folder = os.path.join(spots_folder, "Spot_Dose")
    dose_grids = None
    if PRELOAD_DOSE_GRIDS_IN_MEMORY:
        print("Pre-loading all spot dose grids into memory...")
        dose_grids = {}
        for be_name in tqdm(spot_timeline['beaml_nme'], desc="Loading spot doses"):
            dose_path = os.path.join(spot_dose_folder, f"D_{be_name}.dcm")
            if os.path.exists(dose_path):
                ds = dicom.dcmread(dose_path)
                dose_grids[be_name] = ds.pixel_array * ds.DoseGridScaling

    reference_dicom = dicom.dcmread(os.path.join(spot_dose_folder, f"D_{spot_timeline['beaml_nme'].iloc[0]}.dcm"))
    grid_shape = reference_dicom.pixel_array.shape
    total_delivery_time = spot_timeline['end_time'].max()
    
    for interval_ms in intervals:
        print(f"\n  Processing VWMDR TI for interval: {interval_ms} ms")
        interval_s = interval_ms / 1000.0
        global_max_dose_rate_grid = np.zeros(grid_shape)
        
        for t_start in tqdm(np.arange(0, total_delivery_time, step), desc=f"Interval {interval_ms}ms"):
            t_end = t_start + interval_ms
            dose_in_window = np.zeros(grid_shape)
            overlapping_spots = spot_timeline[(spot_timeline['start_time'] < t_end) & (spot_timeline['end_time'] > t_start)]
            
            for index, spot in overlapping_spots.iterrows():
                be_name = spot['beaml_nme']
                overlap_duration = min(t_end, spot['end_time']) - max(t_start, spot['start_time'])
                if overlap_duration > 0 and spot['duration'] > 0:
                    dose_fraction = overlap_duration / spot['duration']
                    if PRELOAD_DOSE_GRIDS_IN_MEMORY and be_name in dose_grids:
                        dose_in_window += dose_grids[be_name] * dose_fraction
                    else:
                        path = os.path.join(spot_dose_folder, f"D_{be_name}.dcm")
                        if os.path.exists(path):
                            ds = dicom.dcmread(path)
                            dose_in_window += ds.pixel_array * ds.DoseGridScaling * dose_fraction
            
            dose_rate_in_window = dose_in_window / interval_s
            global_max_dose_rate_grid = np.maximum(global_max_dose_rate_grid, dose_rate_in_window)
            
        max_val = global_max_dose_rate_grid.max()
        scale = max_val / (2**16 - 1) if max_val > 0 else 1.0
        reference_dicom.PixelData = (global_max_dose_rate_grid / scale).astype(np.uint16).tobytes()
        reference_dicom.DoseGridScaling = scale
        reference_dicom.SOPInstanceUID = generate_uid()
        
        if 'ReferencedRTPlanSequence' in reference_dicom and reference_dicom.ReferencedRTPlanSequence:
            reference_dicom.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

        if not os.path.exists(output_folder): os.makedirs(output_folder)
        out_path = os.path.join(output_folder, f"Global_VWMDR_TI_{interval_ms}ms.dcm")
        reference_dicom.save_as(out_path)
        print(f"  Saved: {out_path}")

#******************Feature 6: vRBE Dose Above vRBE Rate (RESTORED Helpers)*****************#
def calculate_spot_vrbe_dose_and_rate(spots_folder, output_folder, spot_timeline, let_scaler):
    """ Helper: Pre-calculates spot-wise variable RBE dose and dose rate """
    print("\n  Helper: Calculating spot-wise variable RBE Dose and Dose Rate...")
    spot_dose_folder = os.path.join(spots_folder, "Spot_Dose")
    spot_let_folder = os.path.join(spots_folder, "Spot_LET")
    vrbe_dose_out = os.path.join(output_folder, "intermediate", "Spot_vRBEDose")
    vrbe_dr_out = os.path.join(output_folder, "intermediate", "Spot_vRBEDR")
    os.makedirs(vrbe_dose_out, exist_ok=True)
    os.makedirs(vrbe_dr_out, exist_ok=True)
    
    for index, spot in tqdm(spot_timeline.iterrows(), total=spot_timeline.shape[0], desc="Pre-calculating vRBE"):
        be_name, duration_ms = spot['beaml_nme'], spot['duration']
        d_path = os.path.join(spot_dose_folder, f"D_{be_name}.dcm")
        l_path = os.path.join(spot_let_folder, f"LET_{be_name}.dcm")
        
        if not os.path.exists(d_path) or not os.path.exists(l_path): continue
        
        d_ds = dicom.dcmread(d_path)
        l_ds = dicom.dcmread(l_path)
        
        phys_dose = (d_ds.pixel_array * d_ds.DoseGridScaling) / 1.1
        let = l_ds.pixel_array * l_ds.DoseGridScaling
        vrbe_dose = (1 + let_scaler * let) * phys_dose
        
        # Save vRBE Dose
        max_d = vrbe_dose.max()
        scale_d = max_d / (2**16 - 1) if max_d > 0 else 1.0
        d_ds.PixelData = (vrbe_dose / scale_d).astype(np.uint16).tobytes()
        d_ds.DoseGridScaling = scale_d
        
        if 'ReferencedRTPlanSequence' in d_ds and d_ds.ReferencedRTPlanSequence:
            d_ds.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

        d_ds.save_as(os.path.join(vrbe_dose_out, f"vRBEDose_{be_name}.dcm"))
        
        # Calculate & Save vRBE Rate
        vrbe_rate = (vrbe_dose / (duration_ms / 1000.0)) if duration_ms > 0 else np.zeros_like(vrbe_dose)
        max_r = vrbe_rate.max()
        scale_r = max_r / (2**16 - 1) if max_r > 0 else 1.0
        d_ds.PixelData = (vrbe_rate / scale_r).astype(np.uint16).tobytes()
        d_ds.DoseGridScaling = scale_r

        if 'ReferencedRTPlanSequence' in d_ds and d_ds.ReferencedRTPlanSequence:
            d_ds.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

        d_ds.save_as(os.path.join(vrbe_dr_out, f"vRBEDR_{be_name}.dcm"))
        
    return vrbe_dose_out, vrbe_dr_out

def calculate_feature_vrbe_dose_above_vrbe_dr(vrbe_dose_folder, vrbe_dr_folder, output_folder, thresholds):
    """ Main Feature: Accumulate vRBE dose above vRBE rate thresholds """
    print("\n  Accumulating vRBE dose above vRBE dose rate...")
    files = glob.glob(os.path.join(vrbe_dose_folder, 'vRBEDose_*.dcm'))
    if not files: return
    os.makedirs(output_folder, exist_ok=True)
    
    ref_ds = dicom.dcmread(files[0])
    
    for thresh in thresholds:
        print(f"\n    Processing threshold: {thresh} Gy(RBE)/s")
        acc_dose = np.zeros_like(ref_ds.pixel_array, dtype=np.float32)
        
        for path in tqdm(files, desc=f"Thresh {thresh}"):
            base = os.path.basename(path).replace('vRBEDose_', '')
            dr_path = os.path.join(vrbe_dr_folder, 'vRBEDR_' + base)
            if not os.path.exists(dr_path): continue
            
            d_ds = dicom.dcmread(path)
            dr_ds = dicom.dcmread(dr_path)
            
            dose = d_ds.pixel_array * d_ds.DoseGridScaling
            dr = dr_ds.pixel_array * dr_ds.DoseGridScaling
            
            acc_dose += (dose * (dr >= thresh))
            
        max_val = acc_dose.max()
        scale = max_val / (2**16 - 1) if max_val > 0 else 1.0
        ref_ds.PixelData = (acc_dose / scale).astype(np.uint16).tobytes()
        ref_ds.DoseGridScaling = scale
        ref_ds.SOPInstanceUID = generate_uid()

        if 'ReferencedRTPlanSequence' in ref_ds and ref_ds.ReferencedRTPlanSequence:
            ref_ds.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID = generate_uid()

        ref_ds.save_as(os.path.join(output_folder, f"vRBEDose_Above_vRBEDR_{thresh}_GysRBE.dcm"))

#******************Matching Utils**********************************************************#
def read_in_beamlet_infos(path):
    beamlet_info = pd.read_csv(path, skiprows=1, delimiter=' |,', header=None, engine='python', encoding='latin1')
    return {
        'beaml_nme': beamlet_info[0],
        'gantry_angle': beamlet_info[2].to_numpy().T,
        'couch_angle': beamlet_info[4].to_numpy().T,
        'energy': beamlet_info[6].to_numpy().T,
        'spot_x': beamlet_info[8].to_numpy().T * 10,
        'spot_y': beamlet_info[10].to_numpy().T * 10,
        'mu': beamlet_info[12].to_numpy().T
    }

def read_in_machine_logfiles(path_list):
    all_logs = []
    for file_path in path_list:
        log = pd.read_csv(file_path, skiprows=LOG_FILE_HEADER_ROWS, delimiter=',')
        match = re.search(r'G(\d+\.?\d*)_C(\d+\.?\d*)', file_path)
        if match:
            log['gantry_angle'] = float(match.group(1))
            log['couch_angle'] = float(match.group(2))
            all_logs.append(log)
    combined = pd.concat(all_logs, ignore_index=True)
    gmt_start = pd.to_datetime(combined[LOG_COLUMN_START_TIME], format=LOG_FILE_TIME_FORMAT)
    global_start = gmt_start.min()
    return {
        'log_x': combined[LOG_COLUMN_X].to_numpy(),
        'log_y': combined[LOG_COLUMN_Y].to_numpy(),
        'log_energy': combined[LOG_COLUMN_ENERGY].to_numpy(),
        'log_mu': combined[LOG_COLUMN_MU].to_numpy(),
        'log_start_time': (gmt_start - global_start).dt.total_seconds().to_numpy() * 1000,
        'log_duration': combined[LOG_COLUMN_DURATION].to_numpy(),
        'log_gantry_angle': combined['gantry_angle'].to_numpy(),
        'log_couch_angle': combined['couch_angle'].to_numpy()
    }

def get_matched_spot_timeline(spots_folder, logs_folder):
    beamlet_path = os.path.join(spots_folder, 'Beamlet_info.txt')
    log_files = glob.glob(os.path.join(logs_folder, '*.csv'))

    if not os.path.exists(beamlet_path) or not log_files:
        print("Error: Missing Beamlet_info.txt or Log CSVs.")
        return None
    print("Matching spots to logs...")
    plan = pd.DataFrame(read_in_beamlet_infos(beamlet_path))
    log_data = read_in_machine_logfiles(log_files)
    log = pd.DataFrame({k: v for k, v in log_data.items()})
    plan['plan_order'] = np.arange(len(plan))
    log['log_index'] = np.arange(len(log))
    for k in ['gantry_angle', 'couch_angle']:
        plan[f'{k}_rnd'] = np.round(plan[k].astype(float), 2)
        log[f'{k}_rnd'] = np.round(log[f'log_{k}'].astype(float), 2)
    
    ####################
    # BEGIN CHANGE - LW
    ####################
    merged = pd.merge(
        log, plan,
        left_on=['gantry_angle_rnd', 'couch_angle_rnd'],
        right_on=['gantry_angle_rnd', 'couch_angle_rnd'],
        how='left'
    )
    ##################
    # END CHANGE - LW
    ##################
    
    candidates = merged[
        ((merged['spot_x'] - merged['log_x']).abs() <= SPOT_POSITION_TOLERANCE_MM) &
        ((merged['spot_y'] - merged['log_y']).abs() <= SPOT_POSITION_TOLERANCE_MM) &
        ((merged['mu'] - merged['log_mu']).abs() <= MU_TOLERANCE) &
        ((merged['energy'] - merged['log_energy']).abs() <= ENERGY_TOLERANCE_MEV)
    ].copy()

    ####################
    # BEGIN CHANGE - LW
    ####################
    if len(candidates) == 0:
        print("ERROR: No log spots could be matched to any planned spot!")
        sys.exit()
    ##################
    # END CHANGE - LW
    ##################

    candidates['dist'] = np.sqrt(
        ((candidates['spot_x'] - candidates['log_x']) / SPOT_POSITION_TOLERANCE_MM)**2 +
        ((candidates['spot_y'] - candidates['log_y']) / SPOT_POSITION_TOLERANCE_MM)**2 +
        ((candidates['mu'] - candidates['log_mu']) / MU_TOLERANCE)**2 +
        ((candidates['energy'] - candidates['log_energy']) / ENERGY_TOLERANCE_MEV)**2
    )
    
    ####################
    # BEGIN CHANGE - LW
    ####################
    best = candidates.loc[
        candidates.groupby('log_index')['dist'].idxmin()
    ].sort_values('log_start_time')

    # Warn if some logs could not be matched at all
    unmatched_logs = len(log) - best['log_index'].nunique()
    if unmatched_logs > 0:
        print(f"[WARNING] {unmatched_logs} log spots could not be matched to any planned spot and were ignored.")
    ##################
    # END CHANGE - LW
    ##################

    return pd.DataFrame({
        'beaml_nme': best['beaml_nme'],
        'start_time': best['log_start_time'],
        'duration': best['log_duration'],
        'end_time': best['log_start_time'] + best['log_duration']
    })
#******************************************************************************************#
####################################End definition functions################################


####################################Start main program######################################
if __name__ == '__main__':
    print("Starting Feature Calculator v6.0 (Safe Mode)...")
    
    # 1. Path Derivation
    print(f"Base Treatment: {PATH_TREATMENT}")
    spots_path = glob.glob(os.path.join(PATH_TREATMENT, '*_spots'))[0]
    logs_path = glob.glob(os.path.join(PATH_TREATMENT, '*_logs'))[0]
    plan_name = os.path.basename(spots_path).replace('_spots', '')
    plan_folder = os.path.join(PATH_TREATMENT, plan_name)
    features_folder = os.path.join(PATH_TREATMENT, "features")
    
    # Deriving Output Paths for "Smart Skip"
    timeline_out_path = os.path.join(spots_path, "Spot_Dose_Rate", "matched_spot_time_info.txt")
    dr_out_folder = os.path.join(spots_path, "Spot_Dose_Rate")
    
    # Automatic CT and Structure Path Derivation
    ct_folder_path = os.path.join(plan_folder, "CT")
    struct_folder_path = os.path.join(plan_folder, "Structure_set")
    
    struct_files = glob.glob(os.path.join(struct_folder_path, '*.dcm'))
    struct_file_path = struct_files[0] if struct_files else None

    # 2. Spot Matching (Common Prerequisite)
    requires_timeline = (
        FEATURES_TO_CALCULATE.get("Export_Matched_Timeline") or
        FEATURES_TO_CALCULATE.get("Calculate_Spot_Dose_Rates") or
        FEATURES_TO_CALCULATE.get("Export_Organ_Physical_Dose_and_LET_CSV") or
        FEATURES_TO_CALCULATE.get("Global_VWMDR_TI") or
        FEATURES_TO_CALCULATE.get("Dose_Above_Dose_Rate_TI")
    )

    spot_timeline = None
    if requires_timeline:
        # We always perform matching in memory to ensure data integrity for downstream features
        spot_timeline = get_matched_spot_timeline(spots_path, logs_path)

    # 3. Execution Loop with "Smart Skip"
    
    # A. Export Timeline
    if FEATURES_TO_CALCULATE.get("Export_Matched_Timeline"):
        if os.path.exists(timeline_out_path):
            print(f"\n[SKIP] Timeline output already exists: {timeline_out_path}")
        else:
            export_matched_timeline_file(dr_out_folder, spot_timeline)

    # B. Generate Spot Dose Rates
    if FEATURES_TO_CALCULATE.get("Calculate_Spot_Dose_Rates"):
        # Check if folder exists and has content
        dr_files_exist = False
        if os.path.exists(dr_out_folder):
            # Fast check: Are there roughly enough files?
            existing_count = len(glob.glob(os.path.join(dr_out_folder, "DR_*.dcm")))
            expected_count = len(spot_timeline)
            
            if existing_count >= expected_count:
                dr_files_exist = True
                print(f"\n[SKIP] Spot Dose Rates already generated.")
                print(f"       Found {existing_count} DR files (Expected: {expected_count}).")
            elif existing_count > 0:
                print(f"\n[WARNING] Found partial Spot Dose Rates ({existing_count}/{expected_count}).")
                print("          Re-calculating to ensure completeness...")

        if not dr_files_exist:
            calculate_feature_spot_dose_rates(spots_path, spot_timeline)

# C. Organ Exports (Uses Multiprocessing)
    if FEATURES_TO_CALCULATE.get("Export_Organ_Physical_Dose_and_LET_CSV"):
        if struct_file_path:
            # Create a dedicated output folder for these CSVs
            organ_out_path = os.path.join(features_folder, "Organ_Dose_LET_Export")
            
            # --- Get Number of Fractions ---
            num_fractions = get_number_of_fractions(plan_folder)
            # ------------------------------------

            # Run Physical Dose Export
            calculate_feature_organ_export(
                "PhysicalDose", spots_path, organ_out_path, spot_timeline, 
                ct_folder_path, struct_file_path, STRUCTURES_TO_EXPORT, NUMBER_CPUS, num_fractions
            )
            # Run LET Export
            calculate_feature_organ_export(
                "LET", spots_path, organ_out_path, spot_timeline, 
                ct_folder_path, struct_file_path, STRUCTURES_TO_EXPORT, NUMBER_CPUS, num_fractions
            )

    # D. Standard 3D Map Features
    if FEATURES_TO_CALCULATE.get("GLOBAL_VWMDR"):
        calculate_feature_global_vwmdr(dr_out_folder, os.path.join(features_folder, "VWMDR"))

    if FEATURES_TO_CALCULATE.get("Variable_RBE_Plan_Dose"):
        calculate_feature_variable_rbe_dose(plan_folder, os.path.join(features_folder, "vRBEdose"), LET_SCALER)

    if FEATURES_TO_CALCULATE.get("Dose_Above_Dose_Rate"):
        calculate_feature_dose_above_dose_rate(spots_path, os.path.join(features_folder, "DoseAboveDoseRate"), DOSE_RATE_THRESHOLDS)

    if FEATURES_TO_CALCULATE.get("Dose_Above_LET"):
        out_folder = os.path.join(features_folder, "DoseAboveLET")
        calculate_feature_dose_above_let(spots_path, out_folder, LET_THRESHOLDS)
        
    if FEATURES_TO_CALCULATE.get("Dose_Above_Dose_Rate_TI"):
        out_folder = os.path.join(features_folder, "DoseAboveDoseRate_TI")
        calculate_feature_dose_above_dose_rate_ti(spots_path, out_folder, DOSE_RATE_THRESHOLDS, TIME_INTERVALS_MS, TIME_STEP_MS, spot_timeline)

    if FEATURES_TO_CALCULATE.get("Global_VWMDR_TI"):
        out_folder = os.path.join(features_folder, "VWMDR_TI")
        calculate_feature_global_vwmdr_ti(spots_path, out_folder, TIME_INTERVALS_MS, TIME_STEP_MS, spot_timeline)
    
    if FEATURES_TO_CALCULATE.get("VRBE_Dose_Above_VRBE_Dose_Rate"):
        print("\n--- Calculating: Variable RBE Dose Above Variable RBE Dose Rate ---")
        final_output_folder = os.path.join(features_folder, "vRBEDoseAboveVRBEDR")
        # Step 1: Generate intermediate files
        vrbe_dose_folder, vrbe_dr_folder = calculate_spot_vrbe_dose_and_rate(spots_path, features_folder, spot_timeline, LET_SCALER)
        # Step 2: Perform the final calculation using intermediate files
        calculate_feature_vrbe_dose_above_vrbe_dr(vrbe_dose_folder, vrbe_dr_folder, final_output_folder, VRBE_DOSE_RATE_THRESHOLDS)

    print("\nProcessing complete.")
####################################End main program########################################
