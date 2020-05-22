
"""
Created on Wed Jan 15 10:10:45 2020

@author: simsh
"""

#names of TACLeBench tasks in use

benchmarkNames=['adpcm_dec',
                'adpcm_enc',
                'ammunition',
                'cjpeg_transupp',
                'cjpeg_wrbmp',
                'dijkstra',
                'epic',
                'fmref',
                'gsm_dec',
                'gsm_enc',
                'huff_enc',
                'mpeg2',
                'ndes',
                'petrinet',
                'rijndael_dec',
                'rijndael_enc',
                'statemate',
                'susan']

#constants giving columns of input data
TASK1=0
TASK2=1
CORE1=2
CORE3=3
TOTAL_TRIALS=4
TIME=5
TEST_ID=6
TRIAL_NUM=7

import pandas as pd
from statistics import mean, stdev

shortMaxValues={}

shortSampleLength=1000
mediumSampleLength=1500
baselineFile="runID.txt"

SMT_file1="runID-B.txt"
SMT_file2="runID-A.txt"


baselineOUT="customBaseline.csv"
allPairsOUT="customAllPairs.csv"

#readFile
def readFile(file1, file2, SMT):
    execTimesTemp=({'task1' :  [],
                            'task2' :  [],
                            'time'  :  []})
    if SMT:
        with open(file1) as f1, open(file2) as f2:
            for line1, line2 in zip (f1, f2):
                data1=line1.split(" ")
                data2=line2.split(" ")
                execTimesTemp['task1'].append(data1[TASK1])
                execTimesTemp['task2'].append(data1[TASK2])
                execTimesTemp['time'].append(getExecTimeSMT(data1, data2))
    else:
        with open(file1) as f:
            for line in f:
                data=line.split(" ")
                execTimesTemp['task1'].append(data[TASK1])
                execTimesTemp['task2'].append('none')
                execTimesTemp['time'].append(int(data[TIME]))
    execTimes=pd.DataFrame(execTimesTemp)
                
    return execTimes
        
        
def getExecTimeSMT(data1, data2):
    
    #constants indexing data columns
    START_S=5
    START_N=6
    END_S=7
    END_N=8
    
    start1=int(data1[START_S]) * 10**9 + int(data1[START_N])
    start2=int(data2[START_S]) * 10**9 + int(data2[START_N])
    minStart=min(start1, start2)
    
    end1=int(data1[END_S]) * 10**9 + int(data1[END_N])
    end2=int(data2[END_S]) * 10**9 + int(data2[END_N])
    maxEnd=max(end1, end2)
    
    #do I care about this?
    #offset=start2-start1
    return maxEnd-minStart


#rework to accomadate changes in evaluate
def getInflationFactor(execTimesPop, sampleLength, targetQ, observedQ):
    #how close to the expectedQ do we want to be?
    #threshold=1.007 will get values into same range as baseline
    
    #constancts giving position of needed values w/n tuple returned by evaluate
    
    threshold=1.001
    infFactor=1
    inflatedQ=observedQ

    #while observedQ<expected
    while inflatedQ<targetQ:
        infFactor=infFactor*2
        #need to keep inflateMax from growing too large
        inflatedQ=getQ(execTimesPop, sampleLength*infFactor)


    #we've found an upper bound on inflation; now use binary search
    inflateMax=infFactor    
    inflateMin=1
    inflateCur=(inflateMax+inflateMin)/2
    
    i=0
    while (inflatedQ < targetQ or inflatedQ > targetQ*threshold) and i<100:
        if inflatedQ < targetQ:
            inflateMin=inflateCur
            inflateCur=(inflateCur+inflateMax)/2
        else:
            inflateMax=inflateCur
            inflateCur=(inflateCur+inflateMin)/2
        inflatedQ=getQ(execTimesPop, int(sampleLength*inflateCur))
        i+=1
    
    return (inflatedQ, inflateCur)

#returns ([all observedQ], [allObservedQIdeal])
def evaluate(execTimes, shortSampleLength, mediumSampleLength, task1, task2, SMT):
    if SMT:
        execTimesPop=execTimes[ ( (execTimes['task1']==task1) & (execTimes['task2']==task2)  ) | 
                              ( (execTimes['task1']==task2) & (execTimes['task2']==task1)  ) ]
    else:
        execTimesPop=execTimes[(execTimes['task1']==task1)]
    #TwoQ=testSamples(execTimesPop['time'].tolist(), sampleLength, numSamples)
    execTimesPop=execTimesPop['time'].tolist()
    


    execTimesShort=execTimesPop[0: shortSampleLength]
    #execTimesLong=execTimesPop
    shortMax=max(execTimesShort)
    if not SMT:
        shortMaxValues[task1]=shortMax
    shortMean=mean(execTimesShort)
    shortSD=stdev(execTimesShort)
    
    if SMT:
        execTimesMedium=execTimesPop[0: mediumSampleLength]
        medMax=max(execTimesMedium)
        medMean=mean(execTimesMedium)
        medSD=stdev(execTimesMedium)
        costLongTask=max(shortMaxValues[task1], shortMaxValues[task2])
        costShortTask=min(shortMaxValues[task1], shortMaxValues[task2])
        costRatio=costLongTask/costShortTask
        score=(medMax-costLongTask)/costShortTask
    
    longMax=max(execTimesPop)
    longMean=mean(execTimesPop)
    longSD=stdev(execTimesPop)

    #qThisTrace=[]
    #execTimesLong=list(execTimesPop)
    #population=len(execTimesPop)
    
    observedQ=getQ(execTimesPop, shortSampleLength)

    expectedQ=((1/(shortSampleLength+1))**(1/shortSampleLength)) * (1-(1/(shortSampleLength+1)))
    
    if observedQ < expectedQ:
        #initial infFactor=1
        #initial inflactedQ=expectedQ
        inflatedQ, infFactor=getInflationFactor(execTimesPop, shortSampleLength, expectedQ, observedQ)
    else:
        inflatedQ=observedQ
        infFactor=1
        
    if not SMT:
        return (shortMax, shortMean, shortSD, longMax, longMean, longSD, observedQ, infFactor, inflatedQ)
    else:
        return (shortMax, shortMean, shortSD, longMax, longMean, longSD, observedQ, infFactor, inflatedQ, medMax, medMean, medSD, costRatio, score)


def getQ(execTimesPop, sampleLength):
    popSize=len(execTimesPop)
    qThisTrace=[]
    i=0
    #execTimesLong needs to be seperate to avoid problems caused by sorting
    while i<popSize-sampleLength-1:
        execTimesShort=execTimesPop[i:i+sampleLength]
        shortMax=max(execTimesShort)
        overages=countOverages(execTimesPop, shortMax)
        qThisTrace.append(float((popSize-overages)/popSize))
        for j in range(i, popSize-sampleLength-1):
                if shortMax!=execTimesPop[j] and shortMax>=execTimesPop[j+sampleLength]:
                    '''
                    if shortMax is not the first element of the trace
                    and shortMax is not exceeded by the first element of the next trace,
                    then shortMax remains constant;
                    we don't have to recount overages
                    '''
                    qThisTrace.append(float((popSize-overages)/popSize))
                else:
                    #continue with the outer loop
                    i=j+1
                    break #out of the j loop
        i=j+1

    return mean(qThisTrace)
    
    

def countOverages(execTimesPop, shortMax):
    execTimesSorted=sorted(execTimesPop)
    #print (execTimesLong)
    i=len(execTimesSorted)-1
    numGreater=0
    while i>=0:
        if execTimesSorted[i]>shortMax:
            numGreater+=1
            i-=1
        else:
            break
    #print ("numGreater: ", numGreater)
    return numGreater
    #return 1-float((numGreater/len(execTimesLong)))
   

def main():


    execTimes=readFile(baselineFile, "none", SMT=False)

    
    print("task1, task2, shortMax, shortMean, shortSD, longMax, longMean, longSD, qComputed, infFactor, inflatedQ", file=open(baselineOUT, "a"))
    for a in benchmarkNames:
        print(a, "none", sep=',', end=',', file=open(baselineOUT, "a"))
        taskResults=evaluate(execTimes, shortSampleLength, mediumSampleLength, a, "none", SMT=False)
        #return statement for evaluate
        #return shortMax, shortMean, shortSD, longMax, longMean, longSD, observedQ, expectedQ
        for result in taskResults:
            print (result, end=',', file=open(baselineOUT, "a"))
        print(file=open(baselineOUT, "a"))



    #get SMT data
    
    #print headers
    print("task1, task2, shortMax, shortMean, shortSD, longMax, longMean, longSD, qComputed, infFactor, inflatedQ, medMax, medMean, medSD, costRatio, score",
          file=open(allPairsOUT, "a"))
    #done this way to accomadate data being split in two files
    execTimes=readFile(SMT_file1, SMT_file2, SMT=True)
    #file Dec14 only has the first three benchmarks as task i
    for i in range(0, len(benchmarkNames)):
        for j in range(i, len(benchmarkNames)):
            task1=benchmarkNames[i]
            task2=benchmarkNames[j]
            print(task1, task2, sep=',', end=',', file=open(allPairsOUT, "a"))
            taskResults=evaluate(execTimes, shortSampleLength, mediumSampleLength, task1, task2, SMT=True)
            for result in taskResults:
                print (result, end=',', file=open(allPairsOUT, "a"))
            print(file=open(allPairsOUT, "a"))

if __name__== "__main__":
  main()        