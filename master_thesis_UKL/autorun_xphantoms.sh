#!/bin/bash
# © 2021, LUKAS C. WOLTER
# Run One BEAMnrc Source on Multiple DOSXYZnrc Phantoms in Succession

# directories
# HOME_DIR=/home/luke/EGS_HOME
HOME_DIR=/home/egs-user/EGSnrc/egs_home
# DOSXYZ_DIR=/home/luke/EGS_HOME/dosxyznrc
DOSXYZ_DIR=/home/egs-user/EGSnrc/egs_home/dosxyznrc
# EXTERNAL_DIR=/media/luke/STR1_WOLTER
EXTERNAL_DIR=/media/egs-user/WD_ELEMENTS

# colours
NONE='\033[0m'
CYAN='\033[0;36m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
FAT_YELLOW='\033[1;33m'
BLUE='\033[0;34m'

cd $HOME_DIR

###############################
# CHOOSE BEAMnrc SIMULATION(s)
###############################
BEAM_SIMS=$(find -L . -maxdepth 1 -name '*BEAM*' -type d | sort -n)

echo "__________________________________"
echo
echo "> Select accelerator (BEAMnrc)"
echo "__________________________________"
echo
select SIM in $BEAM_SIMS ; do
	CURRENT_SIM=${SIM##*/}
	break
done
echo "Selected accelerator source:"
echo -e "  >> ${BLUE}$SIM${NONE}"

###############################
# SELECT PEGS4 DATA FILE
###############################
echo "_________________________"
echo
echo "> Select PEGS4 data file"
echo "_________________________"
echo
select PEGS in 521icru 700icru 700icru_mod ; do
	if [[ $PEGS=="521icru" || $PEGS=="700icru" || $PEGS=="700icru_mod" ]] ; then
		break
	fi
done

echo "PEGS4 file is:"
echo -e "  >> ${BLUE}$PEGS${NONE}"

###############################
# CHOOSE NUMBER OF THREADS
###############################
echo "___________________________"
echo
echo "> Choose number of threads"
echo "___________________________"
echo
read -p "  >> Number of logical threads (1...32): " N_THREAD
if [[ $N_THREAD -gt 32 ]] ; then
	echo -e "  >> Chosen number ${RED}$N_THREAD too high${NONE}, continuing with ${BLUE}32 threads${NONE}"
	let N_THREAD=32
	
fi


###############################
# INITIALIZATION MAIN LOOP
###############################

INIT_STEP=0
let INIT_STEP++
echo
echo -e "  >> Entering directory ${BLUE}$HOME_DIR/$CURRENT_SIM${NONE}..."
cd $HOME_DIR/$CURRENT_SIM

INPUT_FILES=$(find -L . -maxdepth 1 -name "*.egsinp*" -type f | sort -n)
RUN_FILES=$(find -L . -name '*_w*' -type f)

###############################
# DELETE PARALLEL RUN FILES
###############################
COUNTER=0
for RUN_FILE in $RUN_FILES ; do
	if [[ $RUN_FILE != *"_write"* && $RUN_FILE != "script" ]]  ; then
		rm -f $RUN_FILE
		let COUNTER++
	fi
done
if [[ $COUNTER != 0 ]] ; then
	echo -e "  >> Removed ${BLUE}$COUNTER${NONE} parallel run files"
fi

###############################
# CHOOSE INPUT FILE (BEAMnrc)
###############################

echo "________________________________________________________________"
echo
echo "> Choose BEAM input for simulation ($CURRENT_SIM)"
echo "________________________________________________________________"
echo
select FILE in $INPUT_FILES ; do
	TO_DO_FILE=${FILE##*/}
	break
done

echo "Selected input file:"
echo -e "  >> ${BLUE}$TO_DO_FILE${NONE}"

###############################
# CHOOSE PHANTOMS (DOSXYZnrc)
###############################
cd $DOSXYZ_DIR
PHANTOMS=$(find -L . -maxdepth 1 -name '*egsinp*' -type f)
TO_DO_PHANTOMS=()
echo "__________________________________________________________________"
echo
echo "> Choose phantom file(s) for simulation $INIT_STEP ($CURRENT_SIM)"
echo "__________________________________________________________________"
echo
select PHANT in $PHANTOMS DONE ; do
	if [[ $PHANT == "DONE" ]] ; then
		break
	fi
	TO_DO_PHANTOMS+=(${PHANT##*/})
done
echo "Chosen phantom file(s):"
for FILE in ${TO_DO_PHANTOMS[@]} ; do
	echo -e "  >> ${BLUE}$FILE${NONE}"
done

###############################
# SUMMARY PROMPT
###############################
clear
echo "________________"
echo
echo "> S U M M A R Y"
echo "________________"
echo
echo -e "  >> Current simulation: \n\t ${BLUE}$CURRENT_SIM${NONE}"
echo -e "  >> PEGS4 data file: \n\t ${BLUE}$PEGS${NONE}"
echo -e "  >> Number of threads (cores): \n\t ${BLUE}$N_THREAD${NONE}"
echo -e "  >> BEAMnrc input file: \n\t ${BLUE}$TO_DO_FILE${NONE}"
echo -e "  >> DOSXYZnrc input file(s):"
for FILE in ${TO_DO_PHANTOMS[@]} ; do
	echo -e "\t ${BLUE}$FILE${NONE}"
done
echo
echo -e "  >> Press ENTER to start simulation(s), press CTRL+C to exit..."
read -p " " START

###############################
# MKDIR FOR OUTPUT MIGRATION
###############################
DATE=$(date "+%F_%H.%M.%S")
OUTPUT_FOLDER="EGS_autorun_xphantoms_${CURRENT_SIM}_N=${N_THREAD}_${DATE}"
if [[ ! -d "$EXTERNAL_DIR/$OUTPUT_FOLDER" ]] ; then
	mkdir $EXTERNAL_DIR/$OUTPUT_FOLDER
fi 

###############################
# MAIN LEVEL 1 : BEAMnrc
###############################
cd $HOME_DIR/$CURRENT_SIM

SECONDS=0

###############################
# BEGIN MULTI-THREADED RUN
###############################
echo "__________________________________________________________________________________________________________________________"
echo
echo -e " ${YELLOW}BEGIN BEAMnrc (1/1) ${CYAN}[INFILE]${NONE}$TO_DO_FILE ${CYAN}[PEGS4]${NONE}$PEGS ${CYAN}[NTHREAD]${NONE}30"
echo "__________________________________________________________________________________________________________________________"

egs-parallel -n 30 -c "${PWD##*/} -i $TO_DO_FILE -p $PEGS" -f  # $N_THREAD overwritten to enable single-threaded IWATCH run

###############################
# CONCATENATE PHSP-FILES
###############################
ADDPHSP_TARGET="${TO_DO_FILE%.*}_fusion"
echo
if [[ -f "$ADDPHSP_TARGET.egsphsp1" ]] ; then
	echo -e "  >> Target file ${BLUE}$ADDPHSP_TARGET.egsphsp1 ${NONE}exists, removing it"
	rm -f $ADDPHSP_TARGET.egsphsp1
fi
echo -e "  >> Concatenating ${BLUE}$N_THREAD${NONE} phsp-files"

addphsp ${TO_DO_FILE%.*} $ADDPHSP_TARGET $N_THREAD > /dev/null

###############################
# DELETE PARALLEL RUN FILES
###############################
COUNTER=0
RUN_FILES=$(find -L . -name '*_w*' -type f)
for RUN_FILE in $RUN_FILES ; do
	if [[ $RUN_FILE != *"_write"* && $RUN_FILE != "script" ]]  ; then
		rm -f $RUN_FILE
		let COUNTER++
	fi
done
echo -e "  >> Removed ${BLUE}$COUNTER${NONE} parallel run files"

###############################
# MIGRATE OUTPUT TO DRIVE
###############################
if [[ -d "$EXTERNAL_DIR" ]] ; then
	echo -e "  >> Migrating BEAMnrc phsp-output ${BLUE}$ADDPHSP_TARGET.egsphsp1 ${NONE}to external drive"
	mv -f $HOME_DIR/$CURRENT_SIM/$ADDPHSP_TARGET.egsphsp1 $EXTERNAL_DIR/$OUTPUT_FOLDER/${ADDPHSP_TARGET}.egsphsp1
fi

###############################
# TIMER
###############################
if (( $SECONDS >= 0 )) ; then
	let HOURS=SECONDS/3600
	HOURS=$(printf "%02d" $HOURS)
  	let MINUTES=(SECONDS%3600)/60
  	MINUTES=$(printf "%02d" $MINUTES)
  	let SECS=(SECONDS%3600)%60
  	SECS=$(printf "%02d" $SECS)
	echo -e "  >> ${GREEN}COMPLETE${NONE} on `date`. Total duration [hh:mm:ss]: $HOURS:$MINUTES:$SECS" 
fi		
echo

SUB_STEP=0

###############################
# MAIN LEVEL 2 : DOSXYZnrc
###############################
cd $DOSXYZ_DIR
for PHANTOM in ${TO_DO_PHANTOMS[@]} ; do
	let SUB_STEP++
	SECONDS=0
	
	###############################
	# GENERATE PHANTOM COPY (TEMP)
	###############################
	MY_PHANTOM="${PHANTOM%.*}_temp.egsinp"
	cp $PHANTOM ./$MY_PHANTOM
	echo -e "  >> Creating temporal copy ${BLUE}$MY_PHANTOM${NONE} of phantom file"
	
	###############################
	# REPLACE PHSP-SOURCE IN INPUT
	###############################
	echo -e "  >> Replacing phsp-source in ${BLUE}$MY_PHANTOM${NONE} with ${BLUE}$ADDPHSP_TARGET.egsphsp1${NONE}"
	NEW_PATH_TO_PHSP="$EXTERNAL_DIR/$OUTPUT_FOLDER/$ADDPHSP_TARGET.egsphsp1"
	OLD_PATH_TO_PHSP=$(grep "home" $MY_PHANTOM)
	sed -i --expression "s|${OLD_PATH_TO_PHSP}|${NEW_PATH_TO_PHSP}|" ./$MY_PHANTOM
	
	###############################
	# BEGIN MULTI-THREADED RUN
	###############################
	echo "__________________________________________________________________________________________________________________________"
	echo
	echo -e " ${YELLOW}BEGIN DOSXYZnrc ($SUB_STEP/${#TO_DO_PHANTOMS[@]}) ${CYAN}[PHSP]${NONE}$ADDPHSP_TARGET.egsphsp1 ${CYAN}[PHANTOM]${NONE}$PHANTOM ${CYAN}[NTHREAD]${NONE}$N_THREAD"
	echo "__________________________________________________________________________________________________________________________"
	
	FIELD_NAME=${TO_DO_FILE%.*}
	
	egs-parallel -n $N_THREAD -c "dosxyznrc -i ${MY_PHANTOM%.*} -o ${PHANTOM%.*}_${FIELD_NAME} -p $PEGS" -f

	###############################
	# DELETE TEMPORAL PHANTOM FILE
	###############################
	echo
	echo -e "  >> Removing temporal phantom file ${BLUE}$MY_PHANTOM${NONE}"
	rm -f $MY_PHANTOM
	
	###############################
	# DELETE PARALLEL RUN FILES
	###############################
	COUNTER=0
	RUN_FILES=$(find -L . -name '*_w*' -type f)
	for RUN_FILE in $RUN_FILES ; do
		if [[ $RUN_FILE != *"_write"* && $RUN_FILE != "script" ]]  ; then
			rm -f $RUN_FILE
			let COUNTER++
		fi
	done
	echo -e "  >> Removed ${BLUE}$COUNTER${NONE} parallel run files"
	
	###############################
	# MIGRATE OUTPUT TO DRIVE
	###############################
	if [[ -d "$EXTERNAL_DIR" ]] ; then
		echo -e "  >> Migrating DOSXYZnrc 3ddose-output ${BLUE}${PHANTOM%.*}_${FIELD_NAME}.3ddose ${NONE}to external drive"
		mv -f $DOSXYZ_DIR/${PHANTOM%.*}_${FIELD_NAME}.3ddose $EXTERNAL_DIR/$OUTPUT_FOLDER/${PHANTOM%.*}_${FIELD_NAME}.3ddose
	fi
	
	###############################
	# TIMER
	###############################
	if (( $SECONDS > 0 )) ; then
		let HOURS=SECONDS/3600
		HOURS=$(printf "%02d" $HOURS)
	  	let MINUTES=(SECONDS%3600)/60
	  	MINUTES=$(printf "%02d" $MINUTES)
	  	let SECS=(SECONDS%3600)%60
	  	SECS=$(printf "%02d" $SECS)
			echo -e "  >> ${GREEN}COMPLETE${NONE} on `date`. Total duration [hh:mm:ss]: $HOURS:$MINUTES:$SECS" 
	fi
echo
done
