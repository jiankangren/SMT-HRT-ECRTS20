#!/usr/bin/python3


import sys
import os
import matplotlib.pyplot as plt
import numpy



#edited
#Called by plot_util_quad_from_file
def setup_figure(fig, header):
    #fig.legend(["Baseline","CERT-MT"])
    fig.set_ylim(0,1.02)
    fig.set_xlim(6, 16)
    fig.set_xlabel('Utilization')
    fig.set_ylabel('Schedulability Ratio')
    fig.set_title(header)


#this is the key
#called by plot_util_quad_from_file
def add_plot(target, util, baseline, cert):
    #target.plot(util, baseline, linestyle='--')
    target.plot(util, cert)
    #target.xaxis.set_major_locator(MaxNLocator(integer=True))
    minUtil=int(numpy.floor(min(util)))
    maxUtil=int(numpy.ceil(max(util)))
    ticks=[]
    for j in range(minUtil, maxUtil+1):
        ticks.append(j)
    target.set_xticks(ticks)


def plot_util_quad_from_file(path, core, distrib, split, save):
    firstLine=True
    utilBins=[]
    baseline=[]
    certMT=[]
    fourBaselines=[]
    fourCerts=[]
    fourUtilBins=[]
    headers=[]
    with open(path) as f:
        for line in f:
            #print(line)
            if line.strip()=='*****':
                header=True
                data=False
                if not firstLine:
                    fourBaselines.append(list(baseline))
                    fourCerts.append(list(certMT))
                    fourUtilBins.append(list(utilBins))
                    baseline=[]
                    certMT=[]
                    utilBins=[]
                firstLine=False
            elif header==True:
                headers.append(line.split(','))
                data=True
                header=False
            elif data==True:
                thisLine=line.split(',')
                utilBins.append(float(thisLine[0]))
                if int(thisLine[1])==0:
                    baseline.append(0)
                    certMT.append(0)
                else:
                    baseline.append(float(thisLine[2])/float(thisLine[1]))
                    certMT.append(float(thisLine[3])/float(thisLine[1]))
                
        #end of for line in f
        fourUtilBins.append(list(utilBins))
        fourBaselines.append(list(baseline))
        fourCerts.append(list(certMT))
        baseline=[]
        certMT=[]
        utilBins=[]

    coreHeader=core + " Cores, "
    dashIndex=distrib.find('-')
    if distrib[0:1]=="U":
        #Special Case for U-27-63
        #distribHeader="U~(0.27, 0.63), "
        distribHeader="U~(0." + distrib[2:3] + ", 0." + distrib[4:5] + "), "
    else:  
        distribHeader="N~(0." + distrib[1:dashIndex] + ", 0." + distrib[dashIndex+1:len(distrib)] + "), "
    splitHeader="Split=0." + split
    fig = plt.figure()
    #I think this iterates over the four util ranges
    #for i in range(1, 2):
    for i in range(1,5):
        #calculate area
        intM=int(core)
        area=fourUtilBins[i-1][0]*fourCerts[i-1][0]
        j=1
        while True:
            area +=(fourCerts[i-1][j])*.25
            if fourCerts[i-1][j]==0:
                break
            j+=1
        relArea=area/intM
        etc = fig.add_subplot(2,2,i)
        add_plot(etc, fourUtilBins[i-1], fourBaselines[i-1], fourCerts[i-1])
        
        '''
        if fullHeader==True:
            graphHeader=(coreHeader + distribHeader + splitHeader +
            "\n Task Util~Uni. ("+headers[i-1][8] +", "+ headers[i-1][9] +
            ")\n Relative Schedulable Area " + "{0:.2f}".format(relArea)
            )
        else:
        '''
        graphHeader="Task Util~Uni. ("+headers[i-1][8] +", "+ headers[i-1][9] + ")"
        
        setup_figure(etc, graphHeader)
    
    #fig.suptitle(format_header(cached_header, util_on=False), fontsize=18)
    fig.suptitle(coreHeader+distribHeader+splitHeader, fontsize=18)
    fig.tight_layout(rect=[0, 0.03, 1, 0.90])
    
    if not save:
        plt.show()
    else:
        #plt.savefig(sdir +"graphsFeb-4-1000.pdf")
        #fileOut.savefig(fig)
        plt.savefig(sdir + coreHeader+distribHeader+splitHeader + ".pdf")
    plt.close(fig)
    


plt.rcParams['figure.figsize'] = [12, 9]

if len(sys.argv) < 2:
    print("Usage: " + sys.argv[0] + " <sample count in set to plot>")
    exit()
else:
    pass
    #sample_size_to_scan = int(sys.argv[1])

wdir = "results/"
sdir = "results/graphsDup/"
if not os.path.exists(sdir):
    os.mkdir(sdir)
    
core="4"
for distrib in ["N6-07", "N45-06", "U-1-8", "U-4-8", "U-27-63"]:
    for split in ["0", "1", "2"]:
        plot_util_quad_from_file(wdir + core + "Cores_" + distrib + "-" +split + "_50Trials_4Per",save=True, 
                                     core=core, distrib=distrib, split=split)
        
core="8"
for distrib in ["U-1-8", "U-4-8"]:
    for split in ["0", "1", "2"]:
       plot_util_quad_from_file(wdir + core + "Cores_" + distrib + "-" +split + "_50Trials_4Per",save=True, 
                                     core=core, distrib=distrib, split=split)
distrib="N45-12"
for split in ["0", "1"]:
    plot_util_quad_from_file(wdir + core + "Cores_" + distrib + "-" +split + "_50Trials_4Per",save=True, 
                                     core=core, distrib=distrib, split=split)


print("Done.")


