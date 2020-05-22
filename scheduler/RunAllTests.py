# -*- coding: utf-8 -*-
"""
Created on Sat Oct 19 09:54:23 2019

@author: shosborn
"""

#!/usr/bin/python3

import numpy
import CERTMT_runScenario as scenario
import sys
import csv
import os.path
from multiprocessing.pool import ThreadPool
import datetime



M = int(sys.argv[1])
MIN_SAMPLES=int(sys.argv[2])
SYM_DISTRIB=int(sys.argv[3])
SYM_PARAM1=float(sys.argv[4])
SYM_PARAM2=float(sys.argv[5])
SYM_PARAM3=float(sys.argv[6])
PERIOD_COUNT=int(sys.argv[7])
FILE_OUT = sys.argv[8]



if os.path.isfile(FILE_OUT):
    print("Output file " + FILE_OUT + " already exists. Aborting...")
    exit(1)

UNIFORM=scenario.UNIFORM
SPLIT_UNIFORM=scenario.SPLIT_UNIFORM
NORMAL=scenario.NORMAL
SPLIT_NORMAL=scenario.SPLIT_NORMAL


# Superseded by command line parameter
#CORE_COUNT=[4, 6, 8]

#Testing
'''
MIN_TOTAL_UTIL=3
MAX_TOTAL_UTIL=5
BIN_SIZE=.5
UTIL_RANGES=[(.3, .7)]
PERIOD_MIN=10
'''


MAX_TOTAL_UTIL=2*M
BIN_SIZE=.25
MIN_TOTAL_UTIL=3*M/4-BIN_SIZE
UTIL_RANGES=[(0, .4), (.3, .7), (.6, 1), (0, 1)] #low, medium, high, wide
PERIOD_MIN=10
FILE_STATUS="status.txt"




#runParamTest(minTotalUtil, maxTotalUtil, bin_size, min_samples, minTaskUtil, maxTaskUtil, periodMin, periodCount, symMean, symDev, symDistrib, coreCount, timeout)

#match whatever I'm doing
configurations = []
for util_range in UTIL_RANGES:
       	config = {}
        config["minTotalUtil"] = MIN_TOTAL_UTIL
        config["maxTotalUtil"] = MAX_TOTAL_UTIL
        config["bin_size"] = BIN_SIZE
        config["min_samples"] = MIN_SAMPLES
        config["minTaskUtil"] = util_range[0]
        config["maxTaskUtil"] = util_range[1]
        config["periodMin"] = PERIOD_MIN
        config["periodCount"] = PERIOD_COUNT
        config["symParam1"] = SYM_PARAM1
        config["symParam2"] = SYM_PARAM2
        config["symParam3"]=SYM_PARAM3
        config["symDistrib"] = SYM_DISTRIB
        config["coreCount"] = M
        config["timeout"] = 60
        configurations.append(config)

# Run mode configuration
SYNC = False


#change to match my parameters
def run_test(configuration):
    #gets some results and some timing data
    #res, timing = ModTestParameters.runParamTest(**configuration)
    results=scenario.runParamTest(**configuration)
    # User-visible status
    with open(FILE_STATUS, "a") as f:
        print(datetime.datetime.now(), FILE_STATUS, (configuration["minTotalUtil"], 
            configuration["maxTotalUtil"], configuration["periodCount"], 
            configuration["symParam1"], configuration["symParam2"], configuration["symParam3"], configuration["symDistrib"]), file=f)
    #return (res, timing, configuration)
    return(results, configuration)

#change to match my parameters
def save_results(paramResults, minTotalUtil, maxTotalUtil, bin_size, min_samples, minTaskUtil, maxTaskUtil, periodMin, periodCount, symParam1, symParam2, symParam3, symDistrib, coreCount, timeout):
#def save_results(paramResults, m_floor, m, bin_size, min_samples, util_ranges, period_min, period_max, strength_stdev, friend_stdev, strength_mean, friend_mean, period_count):
    with open(FILE_OUT, "a") as f:
        print("*****", file=f) # Delimiter between samples
        csvWriter = csv.writer(f)
        csvWriter.writerow([coreCount, bin_size, min_samples, str((minTotalUtil, maxTotalUtil)).replace(',',':'), symParam1, symParam2, symParam3, symDistrib, minTaskUtil, maxTaskUtil, periodCount, timeout])
        #binMedian=minTotalUtil+bin_size/2
        binMax=minTotalUtil+bin_size
        for innerBin in paramResults:
            innerBin.insert(0, binMax)
            csvWriter.writerow(innerBin)
            binMax += bin_size

# We need this protected so that subprocesses do not run it
if __name__ == '__main__':
    #timings = [0] * 3
    # Use multithreading
    with ThreadPool(processes=len(configurations)) as pool:
        # If we do not need the results to be in order, save things whenever we get them
        for res_tup in pool.imap_unordered(run_test, configurations):
            #each result gives data corresponding to one graph
            save_results(res_tup[0], **(res_tup[1]))
            #for i in range(len(res_tup[1])):
            #    timings[i] += res_tup[1][i]


    #print(datetime.datetime.now(), FILE_OUT, "Complete!\nTimings:")
    #print("\tBaseline:", timings[0]/len(configurations))
    #print("\tSMT 1-Frame:", timings[1]/len(configurations))
    #print("\tCERT-MT:", timings[2]/len(configurations))
    #print("\tFully Preemptive:", timings[3]/len(configurations))
