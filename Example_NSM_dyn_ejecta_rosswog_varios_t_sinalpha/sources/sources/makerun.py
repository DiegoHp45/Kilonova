#!/usr/bin/env python
##############################################################################
# Script to run nuclear reaction network
# Rename it to makerun.py, modify and use on your own risk.
#
# 2013 M. Ugliano, O. Korobkin
# Edited: - 27.12.20 - M. Reichert
#         - 08.07.22 - M. Reichert
#         - 21.07.23 - M. Reichert
##############################################################################

import os
import sys
import glob
import optparse
import multiprocessing
import subprocess
import threading
import numpy  as np
from builtins import input
from bin.examplecase_class import examplecase
from tqdm import tqdm
# Get amount of available cpus for the --many option
cpus = multiprocessing.cpu_count()

# Use 3./4. of all cpus per default
default_cpus =max(1,int((3./4.)*cpus))

#--- define options ----------------------------------------------------------
p = optparse.OptionParser()
p.add_option("-r", action="store", dest="rundir",  default='',  \
  help="simulation directory. By default, it is relative to "
       "$WINNET/runs, but you can redefine it in the makerun.py "
       "script (see the basedir variable)")
p.add_option("-p", action="store", dest="parfile",  default='', \
  help="parameter file for the simulation (see $WINNET/par)")
p.add_option("--many", action="store_true", dest="many_runs", default=False, \
  help="Flag for creating several (non parametric) runs at the same time.\n"
       "The trajectories must have a common base name followed by a label, "
       "e.g. traj001.dat traj002.dat etc. Only the common base name must be "
       "used in template.par, in this case 'traj'. Each trajectory is run in "
       "one subfolder of <rundir> called <rundir>_<label>. "
       "WARNING: files providing initial composition must have the same label "
       "as the corresponding trajectory!")
p.add_option("--examples", action="store_true", dest="listexamples", default=False, \
  help="List all possible example cases with a brief describtion.")
p.add_option("--cpus", action="store", dest="cpus", default=str(default_cpus), \
  help="Amount of cpus that are used for several runs at the same time.")
p.add_option("--val_min", action="store", dest="val_min", default="", \
  help="Minimum value for iteration in case of an analytic run.")
p.add_option("--val_max", action="store", dest="val_max", default="", \
  help="Maximum value for iteration in case of an analytic run.")
p.add_option("--val_it", action="store", dest="val_it", default="", \
  help="Iteration in case of an analytic run.")
p.add_option("--val", action="store", dest="val_values", default="", \
  help="Comma separated values for an analytic run.")
p.add_option("--force", action="store_true", dest="force_run", default=False, \
  help="Force to start the run without asking.")
p.add_option("--prepare", action="store_true", dest="prepare", default=False, \
  help="Prepare the network data in reasonable format. Only works when --many flag is enabled.")
p.set_usage("""
  Setup and launch (optional) a winnet simulation.
  Usage:   ./makerun.py -r <rundir> -p <parfile>
  Example: ./makerun.py -r test -p template.par""")


# Create an example case instance
example = examplecase()


# Parse the obtions
(options,args) = p.parse_args()
if options.listexamples:
    ex_str = str(example)
    os.system("echo -e "+ex_str)
    sys.exit(0)
if len(sys.argv) < 2:
    print("ERROR: Not enough parameters")
    p.print_help()
    sys.exit(1)
if options.rundir=='':
    print("ERROR: no simulation directory specified.")
    p.print_help()
    sys.exit(1)
if options.parfile=='':
    print("ERROR: no parameter file specified.")
    p.print_help()
    sys.exit(1)
if int(options.cpus)<=0:
    print("ERROR: The amount of cpus that are used should be more than 0.")
    p.print_help()
    sys.exit(1)
if (options.val_min != "") or (options.val_max != "") or (options.val_it != "") or (options.val_values != ""):
    try:
        if options.val_values != "":
            val_values = np.array(options.val_values.split(","))
            ana_vals = True
        else:
            val_min = float(options.val_min)
            val_max = float(options.val_max)
            val_it  = float(options.val_it)
            ana_vals = False
        analytic_iteration = True
    except:
        print("ERROR: Could not convert val_min ('"+str(options.val_min)+"'), val_max ('"+\
              str(options.val_max)+"'), or val_it ('"+str(options.val_it)+"') to float!")
        p.print_help()
        sys.exit(1)
else:
    analytic_iteration = False

#--- source and base directories  --------------------------------------------
maindir = os.getcwd()
exename = "winnet"
program = maindir+"/bin/" + exename

# This is the default directory for all Winnet runs: redefine if necessary!
# (redefine if necessary)
basedir = maindir+"/runs"

#--- simulation directory ----------------------------------------------------
if options.rundir[0]=='/':
  rundir = options.rundir # if an absolute path is given, use it
else:
  rundir = basedir +"/"+ options.rundir # path is relative to basedir

# create the base directory for all runs, if necessary
if not os.path.isdir(basedir):
    print("WARNING: base directory for your runs does not exist!")
    ###ans = raw_input("Create "+basedir+"? (Y/n): ")
    ###if (ans == "N" or ans == "n"): sys.exit(0)
    os.mkdir(basedir)

# create the directory for the run
if os.path.isdir(rundir):
    print("WARNING: simulation directory "+rundir+" already exists.")
    if not options.force_run:
        ans = input("Overwrite? (Y/n): ")
        if (ans == "N" or ans == "n"): sys.exit(0)
    subprocess.call(["rm","-rf",rundir])
os.mkdir(rundir)

#--- parameter file ---------------------------------------------------------
if options.parfile[0]=='/': # if an absolute path is given, use it as is
   parfile = options.parfile
else:                       # assume a parfile name relative to $WINNET/par
   parfile = maindir+"/par/"+options.parfile
parfile_name = os.path.basename(parfile)

# check if the parfile exists
if not os.path.exists(parfile):
    print("ERROR: "+parfile+" does not exist. Exiting...")
    sys.exit(1)

#--- initialize examples -----------------------------------------------------
example.prepare_examples(parfile_name)

#--- compile code  -----------------------------------------------------------
os.chdir(maindir)
# subprocess.call(["make", "clean"])
subprocess.call(["make", "-j4"])

#--- single run mode  --------------------------------------------------------
if not options.many_runs:
# copy executable and parameter file to rundir with template substitution:
# substitute @WINNET@ -> maindir using the 'sed' command
    command = "sed 's%@WINNET@%"+maindir+"%g' "+parfile+" > " \
        + rundir + "/" + parfile_name

    subprocess.call(command,shell=True)
    subprocess.call(["mv",program,rundir])

# create directories for snapshots and flow files
    os.chdir(rundir)
    os.mkdir("snaps")
    os.mkdir("flow")

#--- multiple runs mode  -----------------------------------------------------
else:
    # check number of trajectories
    f = open(parfile,'r')
    seed_basename = ''
    initial_composition = ''
    calc_snaps=False
    use_prepared_network_line = -1
    prepared_network_line = -1

    analine = {}

    for it,line in enumerate(f):
        if line[0]=="#":
            continue
        if line.lower().find('trajectory_file') != -1:
            traj_basename = line.split()[2][1:-1]
        if line.lower().find('trajectory_mode') != -1:
            analytic = ("analytic" in line.lower())
        if line.lower().find('seed_file') != -1:
            seed_basename = line.split("=")[1].strip()
        if analytic_iteration:
            if "val" in line.lower():
                par = line.split("=")[0].strip()
                analine[par] = it
        if line.lower().find('snapshot_every') != -1:
            try:
                snaps_every = int(line.split("=")[1].strip())
            except:
                # Better create the flow and snaps folder in case
                # that something goes wrong
                snaps_every = 10
            if snaps_every!=0:
                calc_snaps=True
        if line.lower().find('flow_every') != -1:
            try:
                flow_every = int(line.split("=")[1].strip())
            except:
                # Better create the flow and snaps folder in case
                # that something goes wrong
                flow_every = 10
            if flow_every!=0:
                calc_snaps=True
        if (line.lower().find('read_initial_composition') != -1) and (line.find('=') != -1) \
           and (not line.find('#') != -1):
            initial_composition = line.replace("\n","").replace(" ","\\ ")
        if (line.lower().find('use_prepared_network') != -1) and (line.find('=') != -1) \
           and (not line.find('#') != -1):
            use_prepared_network_line = it
        if (line.lower().find('prepared_network_path') != -1) and (line.find('=') != -1) \
           and (not line.find('#') != -1):
            prepared_network_line = it


    f.close()

    # For from_file mode, check the amount of trajectories
    if not analytic:
        # Create runs based on the amount of trajectories
        traj_basename  = traj_basename.replace("@WINNET@",maindir)
        seed_basename  = seed_basename.replace("@WINNET@",maindir)
        trajectories   = glob.glob(traj_basename+'*')
        trajectories.sort()
        n_trajectories = len(trajectories)
        seeds          = glob.glob(seed_basename+'*')
        loop_count     = n_trajectories

        # Do stuff in case it is only one trajectory
        if n_trajectories == 1 and analytic_iteration:
            analytic = True
        elif n_trajectories >= 1 and analytic_iteration:
            print("ERROR: You cannot run multiple trajectories and an analytic iteration at the same time.")
            sys.exit(1)

    if analytic:
        if not analytic_iteration:
            # Create runs based on the seed files
            seed_basename  = seed_basename.replace("@WINNET@",maindir)
            seeds          = glob.glob(seed_basename+'*')
            n_seeds        = len(seeds)
            loop_count     = n_seeds
        else:
            if ana_vals == False:
                it_values  = np.arange(val_min,val_max+val_it/1000.,val_it)
            else:
                it_values  = val_values

            loop_count = len(it_values)
            seeds      = seed_basename
    # Check if "read_initial_composition" was contained in the parameterfile
    # If it is needed but not contained, append it to the end
    if (len(seeds)!=0) and (initial_composition==""):
        append_initial_composition =True
    else:
        append_initial_composition =False


    # create rundir subdirectories and copy executable and parameter file
    for i in tqdm(range(loop_count),desc="Creating trajectories..."):
        # Distinguish between analytic and trajectory mode
        if not analytic:
            label       = trajectories[i].split(traj_basename)[1]
            label_seed  = trajectories[i].split(traj_basename)[1]
            seed_name   = (seed_basename+label_seed).replace('"','')
            lab_tmp     = os.path.basename(os.path.normpath(trajectories[i]))
        else:
            if not analytic_iteration:
                label       = seeds[i].split(seed_basename)[1]
                lab_tmp     = os.path.basename(os.path.normpath(seeds[i]))
            else:
                label = str(it_values[i])
                lab_tmp = str(it_values[i])
        # Create the trajectories
        subdir = rundir + '/' + lab_tmp
        os.mkdir(subdir)
        if not analytic:
            # Check if the seed file exists and add it to the parameter file
            # Furthermore, add the correct trajectory path into it
            if os.path.isfile(seed_name.replace("@WINNET@",maindir))    :
                command = "sed 's%@WINNET@%" + maindir + "%g;"
                command+= "s%" + traj_basename + "%" + trajectories[i] + "%g;" + \
                    "s%" + seed_basename + "%" + seed_name + "%g;"
                # if read_initial_composition is already included replace it with yes
                if not append_initial_composition:
                    command+="s%" +initial_composition+"%" + "read_initial_composition=yes" + "%g"
                # Replace the @WINNET@ string and pipe everything to the local parameter file in the run folder
                command+="' "+ parfile + " > " + subdir + "/" + parfile_name
                # if read_initial_composition is not included append it to the file
                if append_initial_composition:
                    command+=" && "+"echo read_initial_composition=yes"+" >> "+ subdir + "/" + parfile_name
            else:
                command = "sed '"+\
                    "s%@WINNET@%" + maindir + "%g;"+\
                    "s%" + traj_basename + "%" + trajectories[i] + "%g;"
                if not append_initial_composition:
                    command +="s%" +initial_composition+"%" + "read_initial_composition=no" + "%g;"
                command =command[:-1]+"' "+ parfile + " > " + subdir + "/" + parfile_name

        else:
            if not analytic_iteration:
                # Replace seed label
                command ="sed 's%@WINNET@%" + maindir + "%g;"
                command+= "s%" + seed_basename + "%" + seeds[i] + "%g;"
                # if read_initial_composition is already included replace it with yes
                if not append_initial_composition:
                    command+="s%" +initial_composition+"%" + "read_initial_composition=yes" + "%g;"
                # Replace the @WINNET@ string and pipe everything to the local parameter file in the run folder
                command+="' "+ parfile + " > " + subdir + "/" + parfile_name
                # if read_initial_composition is not included append it to the file
                if append_initial_composition:
                    command+=" && "+"echo read_initial_composition=yes"+" >> "+ subdir + "/" + parfile_name
            else:
                command ="sed 's%@WINNET@%" + maindir + "%g;"
                for k in analine.keys():
                    command+= str(analine[k]+1)+"s%val%"+str(it_values[i])+"%g;"


                command = command[:-1] # Remove last ;
                command+="' "+ parfile + " > " + subdir + "/" + parfile_name


        # Check if the network has to be prepared
        if options.prepare:
            if use_prepared_network_line!=-1:
                # Replace the use_prepared_network line with yes
                command+=" && "+"sed -i '"+str(use_prepared_network_line+1)+"s%no%yes%g' "+subdir+"/"+parfile_name
            else:
                # Append the line to the end of the file
                command+=" && "+"echo use_prepared_network=yes"+" >> "+ subdir + "/" + parfile_name
            if prepared_network_line!=-1:
                # Replace the prepared_network_path line with the correct file
                command+=" && "+"sed -i '"+str(prepared_network_line+1)+"s%prepared_network_path=.*%prepared_network_path="+str(rundir)+"/network_data/%g' "+subdir+"/"+parfile_name
            else:
                # Append the line to the end of the file
                command+=" && "+"echo prepared_network_path="+str(rundir)+"/network_data/"+" >> "+ subdir + "/" + parfile_name


        # Create the folder and copy the executable
        subprocess.call(command,shell=True)

        # Link executable to the folders
        os.system("ln -s "+str(rundir)+"/"+str(exename)+" "+str(subdir))


        if calc_snaps:
            os.mkdir(subdir+"/snaps")
            os.mkdir(subdir+"/flow")

    # Copy executable to rundir only
    subprocess.call(["cp",program,rundir])
    # remove executable
    subprocess.call(["rm","-f",program])

#--- backup all the sources and copy to rundir  ------------------------------
os.chdir(maindir)
os.mkdir("sources")
subprocess.call(["cp","-r","src","makerun.py","Makefile",parfile,"sources"])
subprocess.call("tar zcf sources.tgz sources",shell=True)
subprocess.call(["mv","sources.tgz",rundir])
subprocess.call(["rm","-rf", "sources"])

#--- Example runs ------------------------------------------------------------
# Copy also plot scripts to the folders
example.copy_scripts(parfile_name,rundir)

if options.many_runs and options.prepare:
    print("Preparing network data... This may take up to a few minutes.")
    os.system("cd "+str(subdir)+" "+" && ./winnet *.par ../network_data >../net_creation_log 2>../net_error_log && cd - >/dev/null 2>&1")

#--- run the program, save process ID  ---------------------------------------
# (the following assumes that the shell is bash; might not work in more
#  primitive shells; will not work with csh or tcsh)
if not options.force_run:
    ans = input("Launch the simulation? (y/N)")
    print(ans)
    if (ans=="" or ans=="n" or ans=="N" or ans=="No" or ans=="no"): sys.exit(0)

#--- single run mode ---------------------------------------------------------
if not options.many_runs:
    os.chdir(rundir)
    command= "./"+exename+" "+parfile_name+" >OUT 2>ERR &"
    print("running the command:")
    print(">>>---------------------------------------------")
    print(">>> " + command)
    print(">>>---------------------------------------------")
    subprocess.call("ulimit -s unlimited\n"  + command + \
      """echo $! > PID
         if [ $? -eq 0 ]; then
           echo "Your simulation with PID #`cat PID` has been launched successfully!"
           echo "Simulation directory: "
           echo """+rundir+"""
         else
           echo "Your simulation $program with PID #`cat PID` probably failed to launch."
           echo "Check """+rundir+"""/sim.err for errors"
         fi
         """,\
         shell=True)

    print("")
    if not options.force_run:
        ans = input("Do you want to monitor the simulation? (y/N)")
        if (ans=="" or ans=="n" or ans=="N" or ans=="No" or ans=="no"): sys.exit(0)
        os.system("tail -f OUT")
#--- multiple runs mode  ----------------------------------------------------
else:

    def execute(c,subdir):
        subprocess.call(c,shell=True)
    # Empty list of threads
    threads=[]

    subprocess.call("ulimit -s unlimited",shell=True)
    if os.fork():
        sys.exit()

    # Run all threads
    for i in range(loop_count):
        if not analytic:
            # Create the trajectories
            lab_tmp = os.path.basename(os.path.normpath(trajectories[i]))
        else:
            if not analytic_iteration:
                lab_tmp     = os.path.basename(os.path.normpath(seeds[i]))
            else:
                lab_tmp = str(it_values[i])

        subdir = rundir + '/' + lab_tmp

        command= "cd "+subdir+" && "+"./"+exename+" "+parfile_name+" >OUT 2>ERR"
        print("running trajectory:")
        print(">>>---------------------------------------------")
        print(">>> " + subdir)
        print(">>>---------------------------------------------")

        # Start a new thread
        threads.append( threading.Thread(target=execute, args=(command,subdir)) )
        threads[-1].daemon=True
        threads[-1].start()
        # Check how many threads are running
        run_check = [t.is_alive() for t in threads]
        # If there are too many threads alive you have to wait
        if int(sum(run_check))>=int(options.cpus):
            waiting=True
            # wait until one of the threads is finished
            while waiting:
                run_check = [t.is_alive() for t in threads]
                if int(sum(run_check))<int(options.cpus):
                    waiting = False

            # Filter out finished threads
            threads = [t for t in threads if t.is_alive()]

    # Wait for the last threads
    for t in threads:
        t.join()

    print('Done!')
