#!/bin/bash

# command line parsing
n=$1
shift
command="$@"

# launch EGSnrc jobs in parallel, in the background
echo
echo "egs-parallel.sh ($n jobs): $command"
echo --------------------------------------------------------------------------------

for j in `seq $n`; do
    $command -b -P $n -j $j >/dev/null 2>&1 &
    processid=`printf %5d $!`
    echo "LAUNCHED $processid: $command -b -P $n -j $j &"
done

# wait for completion and report
wait
echo --------------------------------------------------------------------------------
echo "SIMULATION COMPLETED ($command)"
echo