""" 
This is the first step of the data pre-processing, delete the adapter and UMIs from the reads and trim by quality scores.

    Args:
        -I, --input_dir (str): Input directory.
        -A, --adapter (str): Adapter sequence to remove. Default is the Illumina universal adapter.
        -S, --slow (str): Flag that activates slow mode. It only uses one thread. Use in case the memory use exceeds the system capabilities.
        -T, --threads (int): The number of threads to use in applications that allow multithreading. Default is the number of CPU threads.
        -P, --processes (str): The number of cpu threads to use. Default is 4. If 0 is specified, use the number of samples to maximize parallelization.
        -a, --append_sample_dict (str): If specified, appends an existing sample dictionary to the new one.
        -R, --run (str): Run control variable (True to run).
"""

import argparse
import json
from functions.libs import (
    create_sample_dict,
    mkdir,
    eval_fastq_files,
    trimming_files,
    get_stats_fastq_files,
    trimming_files_slow,
)
from multiprocessing import cpu_count

# Gets the command line arguments with argparse.
parser = argparse.ArgumentParser()
parser.add_argument("-I", "--input_dir", type=str)
parser.add_argument("-A", "--adapter", type=str, default="AGATCGGAAGAG")
parser.add_argument("-T", "--threads", type=int, default=cpu_count())
parser.add_argument("-P", "--processes", type=int, default=4)
parser.add_argument(
    "-S", "--slow", action="store_true"
)  # Much slower processing, but less memory-intensive.
parser.add_argument("-a", "--append_sample_dict", action="store_true")
parser.add_argument("-R", "--run", type=bool, default=False)
args = vars(parser.parse_args())

# Assign the command line arguments to variables.
input_dir, adapter, slow, append, threads, processes, run = (
    args["input_dir"],
    args["adapter"],
    args["slow"],
    args["append_sample_dict"],
    args["threads"],
    args["processes"],
    args["run"],
)

# Build sample dict. Key is sample name, value is fastq file path. This is what we use to localize the appropriate files for each step.
# When a processing step is performed over the samples, their file name is changed to indicate the process performed.
# The sample dict is stored as a json file that is updated on each step to keep track of the transformed samples' fastq files.
sample_dict = create_sample_dict(input_dir, "_R1_", ".fastq.gz")

# Creates necessary directories for the analysis.
mkdir("FastQC/")
mkdir("FastQC/Raw/")
mkdir("FastQC/Trim/")
mkdir("00_log/")

# The number indicates the script that has generated the file (except for 00_log).
mkdir("02_trim/")

# Run the fastqc and trimming steps.
if slow:
    # Much lower, but less memory intensive.
    sample_dict = trimming_files_slow(sample_dict, adapter, threads, run)
else:
    eval_fastq_files(sample_dict, "FastQC/Raw", adapter, threads, processes, run)
    sample_dict = trimming_files(sample_dict, adapter, threads, processes, run)
    eval_fastq_files(sample_dict, "FastQC/Trim", None, threads, processes, run)
    get_stats_fastq_files(sample_dict, processes, run)

# If we want to operate over files stored in different folders, it is necessary to run this script on each folder separately.
# The append option allows us to append the sample dict of the new samples to the previous one.
if append:
    with open("00_log/1_2_fastq.json", "r") as jsonfile:
        appendix = sample_dict
        sample_dict = json.load(jsonfile)
        sample_dict.update(appendix)

# Writes out the sample dict as a json file in order to be exchangeable with the other scripts.
with open("00_log/1_2_fastq.json", "w") as jsonfile:
    json.dump(sample_dict, jsonfile, indent=4)
