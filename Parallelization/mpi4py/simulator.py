from mpi4py import MPI
import os
import numpy as np
import json

def convert_value(value):
    r'''
    Maps  a binary value to 1 or -1, under the mapping
        x -> x - 1 + max(0, x)
    
    Inputs
    ------
    value: A value to be converted. Can be float or integer,
           or a numpy array containing floats or integers.
           To obtain expected behavior, value must be either 0 or 1
    
    Returns
    ---------
    converted_value: The value converted to 1 or -1, 
                    where value = 0 is converted to -1, and 
                    value = 1 is converted to 1. If input
                    is numpy array, then output is numpy array as well.
    '''   
    
    converted_value = value - 1 + np.maximum(0, value)

    return converted_value

def multiple_trajectories(p, Seed, T=10**4, numTrajectories=100):
    r'''
    Simulates multiple trajectories of a random walk
    
    Inputs
    ------
    p: The bias of the coin determining the random walk
    
    Seed: A seed for numpy's random number generator.

    T: The total number of timesteps. Must be an integer. Optional
    
    numTrajectories: The total number of trajectories to simulate. Must be an integer. Optional
    
    Returns
    ------
    trajectories: A numpy array of shape (numTrajectories,T) whose j^th row is the j^th simulated trajectory
                       (which is itself of length T)
    '''

    #Set the random seed
    np.random.seed(Seed)
    
    #Generate an array of binomially-distributed
    #random variables whose shape is numTrajectories
    #rows, and T columns
    rvs = np.random.binomial(1, p, size=(numTrajectories, T))
    
    #Vectorize these values
    steps = convert_value(rvs)
    
    #The displacements are again a cumulative sum
    #but when calling np.cumsum(), we need to compute
    #it over axis=1 (the columns)
    trajectories = np.cumsum(steps, axis=1)
    
    return trajectories

def write_trajectories(rank, index, p, trajectories):
    r'''Writes trajectories to disk

    Inputs
    --------

    rank: The rank of the process simulated the trajectory.
          Used as a unique identifier.

    index: An index to indicate which value of $p$ the process
           used in its simulation

    p: The value of $p$

    trajectories: A numpy array (or Python list) which holds the trajectories.
                  It's assumed trajectories has shape (numTrajectories, totalTime)

    Returns
    -----
    None. Writes the trajectory to a json file "rank-index.json" in the simulated_data
          directory
    '''

    filename = '{0}-{1}.json'.format(rank, index)

    trajectories = [[str(x) for x in trajectory] for trajectory in trajectories]

    d = {'p': p, 'trajectories' : trajectories}
    with open(os.path.join('simulated_data', filename), 'w') as f:
        json.dump(d, f)

def data_gen(ps):
    r'''Generates trajectory data, and writes it to disk

    Inputs
    ----
    ps: A numpy array or Python list of the values of $p$ to be iterated over

    Returns
    ------
    None. Writes the simulated trajectories to disk.
    '''

    comm = MPI.COMM_WORLD

    rank = comm.Get_rank()

    index = 0
    for p in ps:
        trajectories = multiple_trajectories(p, rank)
        write_trajectories(rank, index, p, trajectories)
        index += 1

def chunks(l, numChunks):
    r"""Yield numChunks chunks from l.

    Inputs
    ------
    l: A list or numpy array to chunk

    numChunks: The number of chunks to make

    Returns
    --------
    A generator object which yields chunks from l.
    """
    chunkSize = int(np.floor(len(l) / numChunks))

    if len(l) % numChunks == 0:
        for i in range(0, len(l), chunkSize):
            yield l[i:i + chunkSize]
    else:
        for i in range(0, numChunks):
            if i < numChunks - 1:
                yield l[i * chunkSize :(i + 1) * chunkSize]
            else:
                yield l[i * chunkSize:]

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    if rank == 0:
        if not os.path.isdir('simulated_data'): os.mkdir('simulated_data')
        print('Starting simulator')
        ps = np.linspace(0, 1, num=10)
        np.random.shuffle(ps)
        ps = chunks(ps, size)
    else:
        ps = None
    ps = comm.scatter(ps, root=0)
    data_gen(ps)

if __name__ == '__main__':
    main()

