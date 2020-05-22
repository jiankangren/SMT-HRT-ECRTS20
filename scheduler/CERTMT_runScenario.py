'''
Given one set of parameters, run tests to fill one graph.

'''

import CERTMT_TaskSystem as cert
import numpy as np
from random import *


#constants corresponding to different schedulers
BASELINE=cert.BASELINE
CERT_MT=cert.CERT_MT

FAIL=cert.FAIL

NUM_METHODS=2

UNIFORM=cert.UNIFORM
SPLIT_UNIFORM=cert.SPLIT_UNIFORM
NORMAL=cert.NORMAL
SPLIT_NORMAL=cert.SPLIT_NORMAL


'''
this is a guess.  Don't know what's really the best thing here.
Probably more efficient to maximize graph parallelism, but I do have a strict 
time limit.
0 is the default, i.e. let Gurobi figure it out
'''
THREADS_PER_TEST=0


#pretty_print = {BASELINE: "baseline", SMT_ONE_FRAME: "SMT with One Frame Size", CERT_MT: "SMT with Multiple Frame Sizes", FULL_P_CERT_MT: "SMT with Full Premption"}


def runParamTest(minTotalUtil, maxTotalUtil, bin_size, min_samples, minTaskUtil, maxTaskUtil, periodMin, periodCount, symParam1, symParam2, symParam3, symDistrib, coreCount, timeout):
    threadsPerTest=THREADS_PER_TEST

    test_range = maxTotalUtil - minTotalUtil
    numBins = int(np.ceil(test_range/bin_size))
    # "theBins": index 0 is number of task sets in bin, following indicies are how many of those are schedulable for various algorithms
    theBins = []
    for i in range(0, numBins):
        theBins.append(0)
        theBins[i]=[0]*(NUM_METHODS+1)
        #theBins.append([0] * NUM_METHODS +1)

    # Iterate until we've tried at least 'min_samples' task sets at our base utilization
    coreCountBin=int(np.floor((coreCount-minTotalUtil)/bin_size))
    while theBins[coreCountBin][0] < min_samples:
        runBaseline=True
        runCertMT=True
        #create task set
        #targetUtil, util_min, utilMax, periodMin, periodCount, symMean, symDev, symDistrib, m, timeout, solutionLimit, lowerBound, upperBound, threadsPerTest
        myTaskSet = cert.CERTMT_TaskSystem(minTotalUtil, minTaskUtil, maxTaskUtil, periodMin, periodCount, symParam1, symParam2, symParam3, symDistrib, coreCount, timeout, 1000, 1, 1, threadsPerTest)
        # Loop until we reach a task set that nothing can schedule
        while True:
            # Depending on where our utilization fell as we added tasks, we choose a bin
            #this is the starting bin
            myBin = int(np.floor((myTaskSet.totalUtil - minTotalUtil) / bin_size))
            #break if we overshoot desired range
            if len(theBins)-1 < myBin:
                break #out of while TRUE
                
            result=myTaskSet.testSystem(runBaseline, runCertMT)
            theBins[myBin][0]+=1
            
            if result[BASELINE]:
                theBins[myBin][BASELINE]+=1
            else:
                runBaseline=False
                
            if result[CERT_MT]:
                theBins[myBin][CERT_MT]+=1
            else:
                runCertMT=False
            
            #for testing baseline only
            #runCertMT=False
                    
            if not(runBaseline or runCertMT):
                break #out of while True; we didn't have any success
            else:
                myTaskSet.addTaskAndUpdateCosts()

        # If we reach a task set that's unschedulable, assume it's unschedulable for higher utilizations.
        # (We could just simulate all the higher-utilization bins, but that's slow.)
        totalUtil = myTaskSet.totalUtil + uniform(minTaskUtil, maxTaskUtil)
        while totalUtil < maxTotalUtil:
            myBin=int(np.floor((totalUtil-minTotalUtil) /bin_size))
            #myBin = int(np.floor((myTaskSet.totalUtil - minTotalUtil) / bin_size))
            theBins[myBin][0]+=1
            totalUtil = totalUtil +uniform(minTaskUtil, maxTaskUtil)
        #print("utilMin, utilMax, symMean, symDev", minTaskUtil, maxTaskUtil, symMean, symDev)
        #print("theBins[0][0]=",theBins[0][0])
        #print("theBins=", theBins)
    #go back and start a new task set
    #print(theBins)
    return(theBins)

def main():
    #parameterrs for testing
    minTotalUtil=3
    maxTotalUtil=6
    bin_size=0.25
    min_samples=5
    minTaskUtil=.3
    maxTaskUtil=.7
    #need to prevents costs<1
    periodMin=10
    periodCount=4
    symDistrib=SPLIT_UNIFORM
    symParam1=.1
    symParam2=.8
    symParam3=.1
    coreCount=4
    timeout=30
    
    runParamTest(minTotalUtil, maxTotalUtil, bin_size, min_samples, minTaskUtil, maxTaskUtil, periodMin, periodCount, symParam1, symParam2, symParam3, symDistrib, coreCount, timeout)

if __name__== "__main__":
     main() 



#test=runParamTest(minTotalUtil, maxTotalUtil, binSize, minSamples, minTaskUtil, maxTaskUtil, periodMin, periodCount, symMean, symDev, symDistrib, coreCount, timeout)
