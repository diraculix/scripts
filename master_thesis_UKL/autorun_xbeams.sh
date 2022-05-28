#!/bin/bash

# directories
HOME_DIR=/home/egs-user/EGSnrc/egs_home
DOSXYZ_DIR=/home/egs-user/EGSnrc/egs_home/dosxyznrc
EXTERNAL_DIR=/media/egs-user/WD_ELEMENTS

cd $HOME_DIR

###############################
# CHOOSE BEAMnrc SIMULATION(s)
###############################
BEAM_SIMS=$(find -L . -maxdepth 1 -name '*BEAM*' -type d | sort -n)
TO_DO_SIMS=()

echo "_______________________________"
echo
echo "> Select accelerator (BEAMnrc)"
echo "_______________________________"
echo
select SIM in $BEAM_SIMS DONE ; do
	if [[ $SIM == "DONE" ]] ; then
		break
	fi
	TO_DO_SIMS+=(${SIM##*/})
done
echo "Selected accelerator simulation(s):"
for SIM in ${TO_DO_SIMS[@]} ; do
	echo -e "  >> $SIM"
done

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
echo -e "  >> $PEGS"

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
	echo -e "  >> Chosen number $N_THREAD too high, continuing with 32 threads"
	let N_THREAD=32
	
fi


###############################
# INITIALIZATION MAIN LOOP
###############################

INIT_STEP=0
for CURRENT_SIM in ${TO_DO_SIMS[@]} ; do
	let INIT_STEP++
	echo
	echo -e "  >> Entering directory $HOME_DIR/$CURRENT_SIM..."
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
		echo -e "  >> Removed $COUNTER parallel run files"
	fi

	###############################
	# CHOOSE INPUT FILES (BEAMnrc)
	###############################
	TO_DO_FILES=()
	
	###############################
	# INIT PHSP-INPUT (DOSXYZnrc)
	###############################
	TO_DO_PHSP=()

	echo "________________________________________________________________"
	echo
	echo "> Choose input file(s) for simulation $INIT_STEP ($CURRENT_SIM)"
	echo "________________________________________________________________"
	echo
	select FILE in $INPUT_FILES DONE ; do
		if [[ $FILE == "DONE" ]] ; then
			break
		fi
		TO_DO_FILES+=(${FILE##*/})
	done

	echo "Selected input files:"
	for FILE in ${TO_DO_FILES[@]} ; do
		echo -e "  >> $FILE"
	done
	
	###############################
	# CHOOSE PHANTOM (DOSXYZnrc)
	###############################
	cd $DOSXYZ_DIR
	PHANTOMS=$(find -L . -maxdepth 1 -name '*egsinp*' -type f)
	echo "_______________________________________________________________"
	echo
	echo "> Choose phantom file for simulation $INIT_STEP ($CURRENT_SIM)"
	echo "_______________________________________________________________"
	echo
	select PHANT in $PHANTOMS ; do
		if [[ "${PHANTOMS[@]}" =~ "$PHANT" ]] ; then
			PHANTOM="${PHANT##*/}"
			break
		fi
	done
	echo "Chosen phantom file:"
	echo -e "  >> $PHANTOM"
	
	###############################
	# SUMMARY PROMPT
	###############################
	clear
	echo "________________"
	echo
	echo "> S U M M A R Y"
	echo "________________"
	echo
	echo -e "  >> Current simulation ($INIT_STEP/${#TO_DO_SIMS[@]}): \n\t $CURRENT_SIM"
	echo -e "  >> PEGS4 data file: \n\t $PEGS"
	echo -e "  >> Number of threads (cores): \n\t $N_THREAD"
	echo -e "  >> BEAMnrc input file(s):"
	for FILE in ${TO_DO_FILES[@]} ; do
		echo -e "\t $FILE"
	done
	echo -e "  >> DOSXYZnrc phantom file: \n\t $PHANTOM"
	echo
	echo -e "  >> Press ENTER to start simulation(s), press CTRL+C to exit..."
	read -p " " START
	
	SUB_STEP=0
	
	###############################
	# MKDIR FOR OUTPUT MIGRATION
	###############################
	DATE=$(date "+%F_%H.%M.%S")
	OUTPUT_FOLDER="EGS_autorun_xbeams_${CURRENT_SIM}_N=${N_THREAD}_${DATE}"
	if [[ ! -d "$EXTERNAL_DIR/$OUTPUT_FOLDER" ]] ; then
		mkdir $EXTERNAL_DIR/$OUTPUT_FOLDER
	fi 
	
	###############################
	# MAIN LEVEL 1 : BEAMnrc
	###############################
	
	cd $HOME_DIR/$CURRENT_SIM
	
	for IN_FILE in ${TO_DO_FILES[@]} ; do
		let SUB_STEP++
		SECONDS=0
		
		###############################
		# BEGIN MULTI-THREADED RUN
		###############################
		
		egs-parallel -n $N_THREAD -c "${PWD##*/} -i $IN_FILE -p $PEGS" -f
		
		###############################
		# CONCATENATE PHSP-FILES
		###############################
		ADDPHSP_TARGET="${IN_FILE%.*}_fusion"
		TO_DO_PHSP+=("$ADDPHSP_TARGET.egsphsp1")
		echo
		if [[ -f "$ADDPHSP_TARGET.egsphsp1" ]] ; then
			echo -e "  >> Target file $ADDPHSP_TARGET.egsphsp1 exists, removing it"
			rm -f $ADDPHSP_TARGET.egsphsp1
		fi
		echo -e "  >> Concatenating $N_THREAD phsp-files"
		
		addphsp ${IN_FILE%.*} $ADDPHSP_TARGET $N_THREAD > /dev/null
		
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
		echo -e "  >> Removed $COUNTER parallel run files"
		
		###############################
		# MIGRATE OUTPUT TO DRIVE
		###############################
		if [[ -d "$EXTERNAL_DIR" ]] ; then
			echo -e "  >> Migrating BEAMnrc phsp-output $ADDPHSP_TARGET.egsphsp1 to external drive"
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
			echo -e "  >> COMPLETE on `date`. Total duration [hh:mm:ss]: $HOURS:$MINUTES:$SECS" 
		fi		
	done
	echo
	
	SUB_STEP=0
	
	###############################
	# MAIN LEVEL 2 : DOSXYZnrc
	###############################
	cd $DOSXYZ_DIR
	for PHSP in ${TO_DO_PHSP[@]} ; do
		let SUB_STEP++
		SECONDS=0
		
		###############################
		# GENERATE PHANTOM COPY (TEMP)
		###############################
		MY_PHANTOM="${PHANTOM%.*}_temp.egsinp"
		cp $PHANTOM ./$MY_PHANTOM
		echo -e "  >> Creating temporal copy $MY_PHANTOM of phantom file"
		
		###############################
		# REPLACE PHSP-SOURCE IN INPUT
		###############################
		echo -e "  >> Replacing phsp-source in $MY_PHANTOM with $PHSP"
		NEW_PATH_TO_PHSP="$EXTERNAL_DIR/$OUTPUT_FOLDER/$PHSP"
		OLD_PATH_TO_PHSP=$(grep "home" $MY_PHANTOM)
		sed -i --expression "s|${OLD_PATH_TO_PHSP}|${NEW_PATH_TO_PHSP}|" ./$MY_PHANTOM
		FIELD_NAME=${PHSP%.*}
		
		###############################
		# BEGIN MULTI-THREADED RUN
		###############################

		egs-parallel -n $N_THREAD -c "dosxyznrc -i ${MY_PHANTOM%.*} -o ${PHANTOM%.*}_$FIELD_NAME -p $PEGS" -f
	
		###############################
		# DELETE TEMPORAL PHANTOM FILE
		###############################
		echo
		echo -e "  >> Removing temporal phantom file $MY_PHANTOM"
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
		echo -e "  >> Removed $COUNTER parallel run files"
		
		###############################
		# MIGRATE OUTPUT TO DRIVE
		###############################
		if [[ -d "$EXTERNAL_DIR" ]] ; then
			echo -e "  >> Migrating DOSXYZnrc 3ddose-output ${PHANTOM%.*}_$FIELD_NAME.3ddose to external drive"
			mv -f $DOSXYZ_DIR/${PHANTOM%.*}_$FIELD_NAME.3ddose $EXTERNAL_DIR/$OUTPUT_FOLDER/${PHANTOM%.*}_${FIELD_NAME}.3ddose
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
				echo -e "  >> COMPLETE on `date`. Total duration [hh:mm:ss]: $HOURS:$MINUTES:$SECS" 
		fi
	done
	echo
done
