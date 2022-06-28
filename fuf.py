#!/usr/bin/python3

import glob
import os
import subprocess
import re
import getopt
import sys

# Definitions
# Key for obj directories array
ARGS_OBJ_DIRS = 'o'
# Key for obj files array
ARGS_OBJ_FILES = 'O'
# Key for source files array
ARGS_SRC_FILES = 's'
# Key for source directories array
ARGS_SRC_DIRS = 'S'
# Key for mode: scan all, scan single file
ARGS_MODE = 'F'

# Keep usage count of functions
db_hash = {}

# Keep filename where the function is defined
# It is OK if several function with the same name defined in different files.
# After all,we need only functions defined in one file, and not used in any other file.
db_filenames = {}

# Accepted args: symbol, type (in nm output), file name
def db_add(symbol, tp, filename):

    # r, R, t, T are definition of symbols;
    # for these, we save the filename (object file) where they are defined
    if (tp == 'r') or (tp == 'r') or (tp == 't') or (tp == 'T'):
        db_filenames[symbol] = filename
        return

    # Now, we need only 'u' and 'U' symbols:
    # these are 'undefined' in this object file, means
    # it is a usage of external symbol
    if (tp != 'u') and (tp != 'U'):
        return

    if symbol in db_hash:
        db_hash[symbol] += 1
    else:
        db_hash[symbol] = 0

def db_find_unused():
    counter = 0
    for key in db_hash:
        if db_hash[key] < 1:
            filename="Unknown"
            if key in db_filenames:
                filename = db_filenames[key]
            print("Unused: [", counter, "]", key, " :: ", filename)
            counter += 1

# This function runs on all unused symbols,
# and validates that them not used inside
# the file, where they are defined.
def db_unused_second_round():
    return

# This function reads all function names from the object file,
# and return array of strings, like this:
# 7 00000000  WriteBitsInRegsAndWrapAround
# 169 00000216  WriteBitsInRegs
# 283 00000383  ReadBitsInRegs
# 360 0000046d  ReadBitsInArrray
#
# The first column is number of line in the objdump output
# the second is the offset in the object file, we do not need it
# The last one is the func name
def read_functions_from_obj_file(filename):
    # Objdump: dump content of file as ASM code;
    # egrep: filter out only function start
    # sed: replaces '<', '>', ':' with spaces
    # objdump -D -z filename |  egrep -n '^[a-z0-9]+ <[a-zA-Z]+[a-zA-Z0-9_]*>:' | sed 's/[:<>]/ /g'
    pass_args = ['objdump',
                 '-D',
                 '-z',
                 filename,
                 '|',
                 'egrep -n "^[a-z0-9]+ <[a-zA-Z]+[a-zA-Z0-9_]*>:"',
                 'sed "s/[:<>]/ /g"']
    pipe = subprocess.Popen(pass_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, _ = pipe.communicate()
    # print(stdout)
    sbytes = stdout.decode()
    return sbytes.split("\n")

# Accept an array with symbols
# Creates and returns a new array with demangled symbols
def demangle(symbols):
    dem_arr = []
    for s in symbols:
        args = ['c++filt']
        args.extend(s)
        pipe = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, _ = pipe.communicate()
        demangled = stdout.split("\n")
        dem_arr.append(demangled)
    return dem_arr


# Run 'nm' command in shell, read output and return it
# as array of strings. No analysis on the line level
def run_nm_for_a_file(filename):
    pass_args = ['nm', '-C', filename]
    pipe = subprocess.Popen(pass_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, _ = pipe.communicate()
    # print(stdout)
    sbytes = stdout.decode()
    return sbytes.split("\n")

# stdout.split("\n")

# This function accepts strings array,
# where a string is one line of 'nm' output,
# and parses it.
def parse_symbols_array(syms):
    output_arr = []
    for line in syms:
        res = re.split('\W+', line)
        # Now in the res[] we have the string split into words
        # Here is the example of the 'nm' output:

        #                U iprs_kutils_short_path
        # 				 U mcount
        # 000000000000003f r __mod_author65
        # 0000000000000000 r __mod_author72
        # 000000000000001f r __mod_description66
        # 0000000000000052 r __mod_license64
        # 0000000000000013 r __mod_license71

        # As you see, some strings have 3 fields (include address),
        # some have 2.
        # We ignore the addresses, we need the symbol name and type only.

        if len(res) > 3 or len(res) < 2:
            continue

        if len(res) == 3:
            del res[0]
        if len(res) == 2:
            output_arr.append(res)

    return output_arr

# this function parses array of strings,
# and creates a new array.
# Every
def parse_strings_array(syms, col1, col2):
    output_arr = []
    for line in syms:
        res = re.split('\W+', line)
        if len(res) > 3 or len(res) < 2:
            continue
        comb = (res[col1], res[col2])
        output_arr.append(comb)
    return output_arr

def scan_obj_file(filename):
    print("Reading file ", filename)
    # Read symbol from object file
    syms1 = run_nm_for_a_file(filename)
    # Parse all symbols
    syms2 = parse_symbols_array(syms1)
    # Now, add all symbols to the DB
    for s in syms2:
        db_add(s[1], s[0], filename)

# Find files in "directory" with given "extension"
# If "output_arr" is not defined, this function will create it.
def find_files(result_arr, directory, ext):
    # Init files array
    files_arr = []

    # If we received the result array, we use it
    if result_arr is not None:
        files_arr = result_arr

    # Search directory for files with given extension
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith(ext):
                files_arr.append(os.path.join(root, f))
        # print(os.path.join(root, f))
    return files_arr


# Find all objects in the given 'directory'
# Returns array of files
def find_objects_old(directory):
    files_arr = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.o'):
                files_arr.append(os.path.join(root, f))
        # print(os.path.join(root, f))

    return files_arr

# Find object files in given directories (given as a list)
def find_objects(result_arr, directories):
    if directories is None or len(directories) == 0:
        return None

    for d in directories:
        result_arr = find_files(result_arr, d, ".o")
    return result_arr

# Find source files in directories (given as a list)
def find_sources(result_arr, directories):
    if directories is not None or len(directories) == 0:
        return None

    exts = (".c", ".C", ".cpp", "CPP")
    for d in directories:
        result_arr = find_files(result_arr, d, exts)
    return result_arr

# Print usage help
def usage():
    print("""Usage:
    ----+----------------------------------------------------
    -o  |  Add a directory containing object files
    -s  |  [Optional] Add a directory containing source files
    -O  |  [Optional] Add a single object file
    -S  |  [Optional] Add a single source file
    -f  |  + filename: scan a single file
    -h  |  Show this help
    """)

# Parse arguments
def parse_args():
    # This array contains directory to search object files
    obj_dirs = []
    # This array contains directories to search source files
    src_dirs = []
    # This array contains manually added object files
    obj_files = []
    # This array contains manually added source files
    src_files = []

    # Hash to return to caller
    args_dict = {}

    short_arguments='s:S:o:O:hf:'
    try:
        #opts, args = getopt.getopt(sys.argv[1:], short_arguments, long_arguments)
        opts, args = getopt.getopt(sys.argv[1:], short_arguments)
    except getopt.GetoptError as err:
        # print help information and exit:
        uprint(3, "%s\n", str(err))  # will print something like "option -a not recognized"
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        # Object files directory
        elif opt in '-o':
            obj_dirs.append(arg)
        # Source files directory
        elif opt in '-s':
            src_dirs.append(arg)
        # Single object files
        elif opt in '-O':
            obj_files.append(arg)
        # Single source files
        elif opt in '-S':
            src_files.append(arg)
        # Scan and print a single files symbols
        elif opt in '-f':
            args_dict[ARGS_MODE] = 'YES'
            obj_files.append(arg)
        else:
            print("Unknown argument : ", opt)
            sys.exit(1)
    # Now assemble all together and return
    if len(obj_dirs) > 0:
        args_dict[ARGS_OBJ_DIRS] = obj_dirs
    if len(src_dirs) > 0:
        args_dict[ARGS_SRC_DIRS] = src_dirs
    if len(obj_files) > 0:
        print("Adding obj files")
        args_dict[ARGS_OBJ_FILES] = obj_files
    if len(src_files) > 0:
        args_dict[ARGS_SRC_DIRS] = src_files

    # If the dictionary is empty, print help and exit
    if len(args_dict) < 1:
        print("Returning None")
        return None
    # Return the dictionary
    return args_dict

def scan_single_file(args_dict):
    files = args_dict.get(ARGS_OBJ_FILES)
    if files is None:
        print("One file must be specified")
        sys.exit(1)
    for filename in files:
        if filename is not None:
            scan_obj_file(filename)

    # Print all symbols
    for key in db_hash:
        count = db_hash[key]
        if key in db_filenames:
            filename = db_filenames[key]
        else:
            filename = "Unknown"
        # print(key, "::", sym, "::", db_filenames[sym])
        print(key, "::", count, "::", filename)

# This function accepts the array
# of *.o files.
# Is scans the "sourcedir" directory,
# and matches a source file to source file.
# Returns list of source files without object file.
# These source files are probably are not in use.
# def find_not_compiled_sources(sourcedir, obj_files)

def main():
    args_dict = parse_args()
    #print("args_dict: ", args_dict)

    if args_dict is None:
        usage()
        sys.exit(0)

    # Find all source files
    source_files = None
    obj_files = None

    if ARGS_SRC_DIRS in args_dict:
        src_dirs = args_dict.get(ARGS_SRC_DIRS)
        source_files = find_objects(source_files, src_dirs)

    # Find all source files
    # src = find_sources(None, "./src")
    # symbs=run_nm_for_a_file(objs[12])

    # Iterate all object files
    if ARGS_OBJ_DIRS in args_dict:
        obj_dirs = args_dict.get(ARGS_OBJ_DIRS)

    # If the mode is to scan one single file:
    if ARGS_MODE in args_dict and args_dict.get(ARGS_MODE) == 'YES':
        scan_single_file(args_dict)
        sys.exit(0)

    if obj_dirs is None:
        print("You must give at least one Object dir")
        sys.exit(1)

    # Search all directories of Object Files
    obj_files = find_objects(obj_files, obj_dirs)
    if obj_files is None or len(obj_files) == 0:
        print("No object files found in given directories:")
        print(obj_dirs)
        sys.exit(0)

    print(len(obj_files), " files found in object directories")

    # Now let's scan all files

    for f in obj_files:
        scan_obj_file(f)

    db_find_unused()
    sys.exit(0)


if __name__ == "__main__":
    main()
