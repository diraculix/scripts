import sys

# thickness of ebt3-films [cm]
film_thickness=0.0278

# EGS phantom materials
material_dict = {
    "AIR700ICRU" :      1,
    "RW3SOLID" :        2,
    "MYLAR700ICRU" :    3,
    "AL700ICRU" :       4,
    "CU700ICRU" :       5,
    "PB700ICRU" :       6
}

material_dict_inv = {v: k for k, v in material_dict.items()}

density_dict = {
    "AIR700ICRU" :      0.000,
    "RW3SOLID" :        1.045,
    "MYLAR700ICRU" :    1.350,
    "AL700ICRU" :       2.700,
    "CU700ICRU" :       8.960,
    "PB700ICRU" :       11.34
}


'''____________________________________FUNCTIONS____________________________________'''


# input file header
def get_xy_shape(mode):
    if mode == 'native':
        standard_xy = """
-15
10.0, 1
2.5, 1
2.0, 1
1.0, 1
2.0, 1
2.5, 1
10.0, 1
-15
10.0, 1
2.5, 1
2.0, 1
1.0, 1
2.0, 1
2.5, 1
10.0, 1
        """

        film_min_xy, film_max_xy = 3, 5  # voxel numbers for film boundaries

    if mode == 'supersample':
        standard_xy = f"""
-15
1.0, 10
0.1, 49
{film_thickness / 2}, 1
{film_thickness}, 1
{film_thickness / 2}, 1
0.1, 49
1.0, 10
-15
1.0, 10
0.1, 49
{film_thickness / 2}, 1
{film_thickness}, 1
{film_thickness / 2}, 1
0.1, 49
1.0, 10
        """

        film_min_xy, film_max_xy = 36, 85

    else: 
        sys.exit('''Unknown operation mode '{mode}'. Insert 'native' or 'supersample'.. ''')

    return standard_xy, film_min_xy, film_max_xy


# interactive: construct slab phantom input file along z-axis
def make_z_voxels(mode, res=0.1):
    standard_xy, film_min_xy, film_max_xy = get_xy_shape(mode=mode)
    start_z  = float(input('Set start Z value [cm]: '))
    total_voxels = 1
    voxel_info = [start_z, f'{film_thickness}, 1']  # first film at starting position
    material_info = [f'{film_min_xy}, {film_max_xy}, {film_min_xy}, {film_max_xy}, 1, 1, {material_dict["MYLAR700ICRU"]}, 1.35']  # assign film material to first voxel

    break_loop = False

    print('______________________________')
    print()
    print('>> BEGIN voxel creation loop')
    print('______________________________')
    print()

    while not break_loop:
        group_space = float(input('Set voxel z spacing of next group [cm]: '))
        group_count = int(input('Set number of combined voxels (material + film) in this group: '))
        print()

        for index, entry in enumerate(list(material_dict)):
            print(f'\t{index + 1}: {entry}')
        print()

        if mode == 'native':
            group_material = int(input(f'Set material for voxels {total_voxels + 1} ... {int(total_voxels + 2 * group_count)}: '))
        if mode == 'supersample':
            group_material = int(input(f'Set material for voxels {total_voxels + 1} ... {int(total_voxels + group_count * group_space / res)}: '))

        if material_dict_inv[group_material] == "RW3SOLID":
            if mode == 'native':
                min_xy, max_xy = 1, 7
            if mode == 'supersample':
                min_xy, max_xy = 1, 121
        else:
            if mode == 'native':
                min_xy, max_xy = 2, 6
            if mode == 'supersample':
                min_xy, max_xy = 11, 111

        for i in range(group_count):
            if mode == 'native':
                total_voxels += 2
                voxel_info.append(f'{group_space}, 1')
                voxel_info.append(f'{film_thickness}, 1')
                material_info.append(f'{min_xy}, {max_xy}, {min_xy}, {max_xy}, {total_voxels - 1}, {total_voxels - 1}, {group_material}, {density_dict[material_dict_inv[group_material]]}')
                material_info.append(f'{film_min_xy}, {film_max_xy}, {film_min_xy}, {film_max_xy}, {total_voxels}, {total_voxels}, {material_dict["MYLAR700ICRU"]}, {density_dict["MYLAR700ICRU"]}')

            if mode == 'supersample':
                for n in range(int(group_space / res)):
                    total_voxels += 1
                    voxel_info.append(f'{res}, 1')
                    material_info.append(f'{min_xy}, {max_xy}, {min_xy}, {max_xy}, {total_voxels - 1}, {total_voxels - 1}, {group_material}, {density_dict[material_dict_inv[group_material]]}')
                
                total_voxels += 1
                voxel_info.append(f'{film_thickness}, 1')
                material_info.append(f'{film_min_xy}, {film_max_xy}, {film_min_xy}, {film_max_xy}, {total_voxels}, {total_voxels}, {material_dict["MYLAR700ICRU"]}, {density_dict["MYLAR700ICRU"]}')

        print()
        continue_prompt = input(f'Current number of voxels is <{total_voxels}>, create another group [y/n] (default=y)? ')
        if continue_prompt == 'n':
            if mode == 'native':
                total_voxels += 1
                voxel_info.append('1.0, 1')
                material_info.append(f'1, 7, 1, 7, {total_voxels}, {total_voxels}, {material_dict["RW3SOLID"]}, {density_dict["RW3SOLID"]}')  # terminal 1.0cm RW3 slab
            if mode == 'supersample':
                for i in range(int(1.0 / res)):
                    total_voxels += 1
                    voxel_info.append(f'{res}, 1')   
                    material_info.append(f'1, 121, 1, 121, {total_voxels}, {total_voxels}, 2, {density_dict["RW3SOLID"]}')        
            
            break
        else:
            pass

    print('______________________________')
    print()
    print('>> END voxel creation loop')
    print('______________________________')
    print()

    file_name = input('Enter target .txt-file name without ending: ')
    print(f"""Committing write to target '{file_name}.txt' ...""")

    with open(f'{file_name}.txt', 'w+') as target:
        target.write(f'-7, -7, -{total_voxels}, 1\r')
        target.write(f'{standard_xy}')
        for v_info in voxel_info:
            target.write(f'{v_info}\n')
        for m_info in material_info:
            target.write(f'{m_info}\n')
        for i in range(2):
            target.write(7 * '0, ' + '0\n')
        target.write(f'4, 4, 4, 4, 1, {total_voxels}, 1, 0\n')  # z-scan per page for all z-voxels   
        target.write(7 * '0, ' + '0\n')

        target.close()


'''______________________________________MAIN_______________________________________'''


choose_mode = int(input('''Select voxel sampling mode:\n\t1. Native\t...\tThe phantom geometry will be sampled with the real-life resolution
                                                \r\t2. Supersample\t...\tThe phantom will be sampled with a user-defined (higher) resolution '''))
if choose_mode == 1:
    make_z_voxels(mode='native')
if choose_mode == 2:
    make_z_voxels(mode='supersample')
else:
    sys.exit('No valid operation mode selected. Exiting..')