import numpy as np
from scipy import optimize
import os
import sys
import time
import matplotlib.pyplot as plt

program_dir = os.getcwd()
out_dir = program_dir + '/output'

try:
    os.chdir(out_dir)
    print('Found directory', out_dir)
except WindowsError or OSError:
    print('Directory', out_dir, 'does not exist, creating directory ...')
    os.mkdir(out_dir)
    os.chdir(out_dir)

'''____________________________________FUNCTIONS____________________________________'''


# score random (x,y)-tuples
def shoot():
    global min_x, min_y, max_x, max_y
    rand_x = np.random.uniform(min_x, max_x)
    rand_y = np.random.uniform(min_y, max_y)

    return rand_x, rand_y


# compute standard deviation of array
def stdev(array):
    if len(array) > 0:
        mu = np.average(array)
        std = np.sqrt((sum((x_i - mu) ** 2 for x_i in array)) / len(array))
    else:
        mu, std = 0, 0

    return mu, std


# monte carlo integration of a given function on 1d-domain [a,b]
def mc_integrate(func, a, b, mode, verbose=False, iterations=1000, uncert=0.01):
    global min_x, min_y, max_x, max_y, barwidth
    min_x = a
    max_x = b
    min_y = np.round(func(optimize.fminbound(lambda var: func(var), x1=a, x2=b, disp=1)), 5)
    max_y = np.round(func(optimize.fminbound(lambda var: -func(var), x1=a, x2=b, disp=1)), 5)
    outside, inside = 0, 0
    total_area = (max_y - min_y) * (max_x - min_x)
    results_array = []

    tic = time.perf_counter()

    if mode == 'iter':
        for n in range(1, iterations + 1):
            x, y = shoot()
            if abs(y) <= abs(func(x)):
                inside += 1
            else:
                outside += 1

            if verbose:
                results_array.append((inside / n) * total_area)

            sys.stdout.write('\rProgress ' + int(n / iterations * barwidth) * '█' +
                             int(barwidth - n / iterations * barwidth) * '░' + ' ' +
                             str(n) + '/' + str(iterations) + ' iterations')
            sys.stdout.flush()

        if verbose:
            result = results_array[-1]
            plt.plot(np.arange(1, iterations + 1, 1), results_array, '.', markevery=1000, markersize=1.5, color='black', label='integration progress')
            plt.axhline(results_array[-1], color='red', linewidth=.7,
                        label=f'result ({iterations} iterations): {results_array[-1]:.3f}')
            plt.xlabel('iterations')
            plt.ylabel('result')
            plt.ylim(1.9, 2.1)
            plt.xlim(0, iterations)
            # plt.xscale('log')
            plt.grid()
            plt.legend(loc='upper right')
            plt.savefig('MC_progress.pdf')
        else:
            result = (inside / n) * total_area

        toc = time.perf_counter()
        duration = toc - tic
        return result, n, duration

    if mode == 'uncty':  # here, uncertainty means stdev of the last subsequent results
        for n in range(1, 11):
            x, y = shoot()
            if abs(y) <= abs(func(x)):
                inside += 1
            else:
                outside += 1

            results_array.append((inside / n) * total_area)

        mean, dev = stdev(results_array[-10:])

        while dev / mean >= uncert:
            n += 1
            new_x, new_y = shoot()
            if abs(new_y) <= abs(func(new_x)):
                inside += 1
            else:
                outside += 1

            results_array.append((inside / n) * total_area)
            mean, dev = stdev(results_array[-10:])

            if verbose and n % 1E5 == 0:
                print(f'\r\tProgress of {n} iterations -> reached uncertainty {dev / mean * 100:.7f}% '
                      f'(goal {uncert * 100:.7f}%)\r')

        result = results_array[-1]

        toc = time.perf_counter()
        duration = toc - tic
        return result, n, duration

    print(f'''Error: No operation mode called '{mode}', exiting...''')


# illustrate law of large numbers
def uncert_vs_iters(log_goal, points, verbose, log_start=-2):
    fname = f'uncert_data_E{log_goal}_{points}.txt'

    with open(fname, 'w+') as file:
        uncties = np.logspace(log_start, log_goal, points)
        file.write('uncert [%]\titerations\ttime [s]\tresult\n')

        for i in range(len(uncties)):
            print(f'Processing step {i + 1}/{points} ...')
            result, iters, duration = mc_integrate(func=np.sin, a=0, b=np.pi, mode='uncty', uncert=uncties[i],
                                                   verbose=verbose)
            file.write(f'{uncties[i] * 100}\t{iters}\t{duration:.4f}\t{result:.4f}\n')
            print(f'Step: {i + 1}/{points}\tuncertainty: {uncties[i] * 100:.7f}%\titerations: {iters}')

        file.close()

    print(f'Produced file {fname}')


'''______________________________________MAIN_______________________________________'''

global min_x, min_y, max_x, max_y, barwidth
barwidth = 100

print(mc_integrate(func=np.sin, a=0, b=np.pi, mode='iter', iterations=int(5e5), verbose=True))
uncert_vs_iters(log_goal=-7, points=20, verbose=True)