import sys, re, os.path, math

if (len(sys.argv) < 2):
    print('''\nusage:
    filenames
    filenames   space separated list of files to plot
    examples:   egs-sum-3ddose.py *.3ddose > sum.3ddose
                (add dose for all .3ddose files and write the result to file sum.3ddose)
    ''')
    os.path.basename(sys.argv[0])
    sys.exit(1)

files = sys.argv[1:]                                     

# loop over all files
count = 0
for file in files:

    # open 3ddose file
    dosefile = open(file, 'r')

    # get voxel counts on first line
    nx, ny, nz = map(int,dosefile.readline().split())    
    Ng = (nx+1) + (ny+1) + (nz+1)                        
    Nd = nx*ny*nz                                       

    # get voxel grid, dose and relative errors
    data  = map(float,dosefile.read().split())
    data = list(data)           
    xgrid = data[:nx+1]                                  
    ygrid = data[nx+1:nx+1+ny+1]                         
    zgrid = data[nx+1+ny+1:Ng]                           
    dose  = data[Ng:Nd+Ng]                               
    errs  = data[Nd+Ng:]                                 
    del data                                             

    # close 3ddose file
    dosefile.close()

    # declare or check accumulation arrays of size Nd
    if (count == 0):
        sumNd   = Nd
        sumdose = [0] * Nd
        sumerrs = [0] * Nd
    else:
        if (Nd != sumNd):
            print("ERROR: non-matching grid size in file %s (%d, but expected %d)", file, Nd, sumNd)
            sys.exit(1)

    sumdose = [a+b for (a,b) in zip(sumdose,dose)]
    sumerrs = [a+b**2 for (a,b) in zip(sumerrs,errs)]

    count += 1

# compute average and its uncertainty
avgdose = [x/count for x in sumdose]                    
sumerrs[:] = [math.sqrt(x)/count for x in sumerrs]

# print result in .3ddose format
print(str(nx).rjust(12) + str(ny).rjust(12) + str(nz).rjust(12))
print(" ".join(map(str,xgrid)))
print(" ".join(map(str,ygrid)))
print(" ".join(map(str,zgrid)))
print(" ".join(map(str,sumdose)))
print(" ".join(map(str,sumerrs)))