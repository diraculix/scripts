import os
import pydicom
from pydicom.data import get_testdata_file

# user input
parent_dir = '/home/egs-user/Desktop/CTCREATE'
ct_dir = '/home/egs-user/Desktop/CTCREATE/DCM'
beam_dir = '/home/egs-user/Desktop/CTCREATE/BEAM'


'''____________________________________FUNCTIONS____________________________________'''


# print overview of RT plan beams
def list_beams(plan_dataset):
    lines = ["{name:^13s} {num:^8s} {gantry:^8s} {ssd:^11s} {iso:^30s}".format(
        name="Beam name", num="Number", gantry="Gantry", ssd="SSD [cm]", iso="Isocenter (x,y,z) [cm]")]
    for beam in plan_dataset.BeamSequence:
        cp0 = beam.ControlPointSequence[0]
        SSD = float(cp0.SourceToSurfaceDistance / 10)
        iso_xyz = [float(coord) / 10 for coord in cp0.IsocenterPosition]

        lines.append("{b.BeamName:^13s} {b.BeamNumber:8d} "
                     "{gantry:8.1f} {ssd:8.1f} {iso}".format(b=beam,
                                                       gantry=cp0.GantryAngle,
                                                       ssd=SSD,
                                                       iso=iso_xyz))
    return "\n".join(lines)


# return jaw / mlc leaf parameters for every beam & write to file
def field_specs(plan_dataset):
    lines = 'Beam No.\tBeam name\t\tMLC index\tX jaws [cm]\t\t\t\t\tY jaws [cm]\t\t\t\t\tLeaf pos [cm]\n' + 118 * '_' + '\n'
    for index, beam in enumerate(plan_dataset.BeamSequence):
        cp0 = beam.ControlPointSequence[0]
        colli_params = cp0.BeamLimitingDevicePositionSequence
        jaw_X = [round(i/10, 6) for i in colli_params[0].LeafJawPositions]
        jaw_Y = [round(i/10, 6) for i in colli_params[1].LeafJawPositions]
        try:
            mlc = colli_params[2].LeafJawPositions
            mlc_X1 = [round(i/10, 6) for i in mlc[:int(len(mlc)/2)]]
            mlc_X2 = [round(i/10, 6) for i in mlc[int(len(mlc)/2):]]
            beam_inp_name = f'LWK3_{beam.BeamName}_MLCspecs_BEAM.egsinp'
            os.chdir(beam_dir)
            with open(beam_inp_name, 'w+') as beam_input:
                for number, leafpair in enumerate(mlc_X1):
                    leaf_X1_egs = round(mlc_X1[-number] * (50.98 + 0.5 * 5.95) / 100, 6)
                    leaf_X2_egs = round(mlc_X2[-number] * (50.98 + 0.5 * 5.95) / 100, 6)
                    beam_input.write(f'{leaf_X1_egs}, {leaf_X2_egs}, 1\n')
                beam_input.close()

        except IndexError:
            mlc_X1 = [None for i in range(60)]
            mlc_X2 = [None for i in range(60)]
        for leaf, pos in enumerate(mlc_X1):
            if leaf == 0:
                lines += f'\n[{index + 1}]\t\t\t{beam.BeamName}\t\t\t\t{leaf + 1}\t\t\t{jaw_X}\t\t{jaw_Y}\t\t[{mlc_X1[leaf]},{mlc_X2[leaf]}]'
            else:
                lines += f'\n\t\t\t\t\t\t\t{leaf + 1}\t\t\t{jaw_X}\t\t{jaw_Y}\t\t[{mlc_X1[leaf]},{mlc_X2[leaf]}]'
            
        lines += '\n' + 118 * '_' + '\n'

    patient = plan_dataset.PatientName
    os.chdir(parent_dir)
    os.chdir(ct_dir)
    with open(f'{patient}_planparams.txt', 'w+') as file:
        file.write(lines)
        file.close()


'''______________________________________MAIN_______________________________________'''


os.chdir(ct_dir)
# user input
filename = 'RP1.2.752.243.1.1.20220215124959921.9000.22650.dcm'
dataset = pydicom.dcmread(filename)
list_beams(dataset)
field_specs(dataset)
