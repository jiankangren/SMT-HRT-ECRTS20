/**
 * Copyright 2019 Sims Hill Osborne and Joshua Bakita
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 **/
#include <fcntl.h>
#include <limits.h>
#include <semaphore.h>
#include <signal.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

// Benchmarks use SET_UP, START_LOOP, STOP_LOOP, and WRITE_TO_FILE
// These are macros so that we can declare and maintain additional state inside
// the benchmark.
#define SET_UP if (argc < 8) {\
        printf("Usage: %s <name> <runs> <my core> <other core> <other program> <runID> <lockID>", argv[0]);\
        exit(1);\
    }\
    char * thisProgram = argv[1];\
    int maxJobs = atoi(argv[2]);\
    char * thisCore = argv[3];\
    char * otherCore = argv[4];\
    char * otherProgram = argv[5];\
    char * runID = argv[6];\
    int lockID = atoi(argv[7]);\
    struct timespec start, end;\
    int jobsComplete;\
    long * startS = malloc(sizeof(long) *maxJobs);\
    long * startN = malloc(sizeof(long) *maxJobs);\
    long * endS = malloc(sizeof(long) *maxJobs);\
    long * endN = malloc(sizeof(long) *maxJobs);\
    char * bigArray;\
    char fileName[strlen(runID) + 5];\
    strcpy(fileName, runID);\
    strcat(fileName, ".txt");\
    mlockall(MCL_CURRENT || MCL_FUTURE);\
    sem_t *firstSem=sem_open("/firstTacleSem", O_CREAT, 644, 0);\
    if (firstSem == SEM_FAILED) {\
        perror("Error opening/creating first semaphore");\
        exit(1);\
    }\
    sem_t *secondSem=sem_open("/secondTacleSem", O_CREAT, 644, 0);\
    if (secondSem == SEM_FAILED) {\
        perror("Error opening/creating second semaphore");\
        exit(1);\
    }\
    int barrier_file = shm_open("/TacleBarrier", O_CREAT | O_RDWR, 644);\
    if (barrier_file == -1) {\
        perror("Error creating shared memory");\
        exit(1);\
    }\
    /* This sets our shared file to be one byte of '\0'*/ \
    if (ftruncate(barrier_file, 1) == -1) {\
        perror("Error setting size of shared memory");\
        exit(1);\
    }\
    char * barrier = mmap(NULL, 1, PROT_WRITE, MAP_SHARED, barrier_file, 0);\
    if (barrier == MAP_FAILED) {\
        perror("Error mapping shared memory");\
        exit(1);\
    }\
    int error;\
    int val;

#define SAVE_RESULTS if (jobsComplete > -1){\
            startS[jobsComplete]=start.tv_sec;\
            startN[jobsComplete]=start.tv_nsec;\
            endS[jobsComplete]=end.tv_sec;\
            endN[jobsComplete]=end.tv_nsec;}

#define WRITE_TO_FILE {\
    munlockall();\
    FILE *fp = fopen(fileName, "a");\
    if (fp == NULL) {\
        perror("Error opening file. \n");\
        exit(1);\
    }\
    for(jobsComplete=0; jobsComplete<maxJobs; jobsComplete++){\
        fprintf(fp, "%s %s %s %s %d %ld %ld %ld %ld %s %d \n",\
        thisProgram, otherProgram, thisCore, otherCore, maxJobs,\
        startS[jobsComplete], startN[jobsComplete], endS[jobsComplete], endN[jobsComplete],\
        runID, jobsComplete);\
    }\
    fclose(fp);\
    /* Clean up the barrier synchronization shared memory */\
    munmap(barrier, 1);\
    shm_unlink("/TacleBarrier");\
    free(startS);\
    free(startN);\
    free(endS);\
    free(endN);\
}

// Call the wbinvld instruction (it's in a kernel module due to it being ring-0)
#define FLUSH_CACHES FILE *fp = fopen("/proc/wbinvd", "r");\
    if (fp == NULL) {\
        perror("Cache flush module interface cannot be opened");\
        exit(1);\
    }\
    char dummy;\
    if (fread(&dummy, 1, 1, fp) == 0) {\
        perror("Unable to access cache flush module interface");\
        exit(1);\
    }\
    fclose(fp);

// These timers should just be aliases to the hardware counters w/ some small adjustments
#define START_TIMER clock_gettime(CLOCK_MONOTONIC, &start);
#define STOP_TIMER clock_gettime(CLOCK_MONOTONIC, &end);

//check value of sem
//if sem=0, unlock
//if sem=1, spin

#define SLEEP nanosleep((const struct timespec[]){{0, 1000000}}, NULL);

#define FIRST_UNLOCK if (lockID == 1) {\
        if (sem_post(secondSem) != 0) {\
            perror("Unable to unlock second semaphore");\
            exit(1);\
        }\
    } \
    else {\
        if (sem_post(firstSem) != 0) {\
            perror("Unable to unlock first semaphore");\
            exit(1);\
        }\
    } \

#define FIRST_LOCK if (lockID == 1) {\
        if (sem_wait(firstSem) != 0) {\
            perror("Unable to wait on first semaphore");\
            exit(1);\
        }\
    }\
    else {\
        if (sem_wait(secondSem) != 0) {\
            perror("Unable to wait on second semaphore");\
            exit(1);\
        }\
    }


#define SECOND_UNLOCK   if (lockID==1){sem_post(fourthSem) ; }\
            else {sem_post(thirdSem) ; }

#define SECOND_LOCK if (lockID==1){sem_wait(thirdSem); }\
            else {sem_wait(fourthSem); }

#define BARRIER_SYNC if (__sync_bool_compare_and_swap(barrier, 0, 1)) {\
        while (!__sync_bool_compare_and_swap(barrier, 0, 0)) {};\
    }\
    else {\
        __sync_bool_compare_and_swap(barrier, 1, 0);\
    }

#define START_LOOP FIRST_UNLOCK FIRST_LOCK FLUSH_CACHES BARRIER_SYNC START_TIMER
#define STOP_LOOP STOP_TIMER SAVE_RESULTS


/*
Intended structure

main
SET_UP
notice that STOP LOOP negates the ++ if outout=0
for (jobsComplete=-1; jobsComplete<maxJobs; jobsComplete++){
	START_LOOP
        tacleInit();
        tacleMain();
	STOP_LOOP
}
WRITE_TO_FILE
tacleReturn 
*/
