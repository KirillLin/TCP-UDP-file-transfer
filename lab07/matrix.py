import numpy as np


def split_range(total, size, rank):
    base, extra = divmod(total, size)
    start = rank * base + min(rank, extra)
    stop = start + base + (1 if rank < extra else 0)
    return start, stop


def linear_to_ij(indices, dim):
    indices = np.asarray(indices)
    return indices // dim, indices % dim


def multiply_tile(a, b, start, stop, dim):
    indices = np.arange(start, stop)
    rows, cols = linear_to_ij(indices, dim)
    return np.einsum('ij,ij->i', a[rows], b.T[cols])


def write_tile(c, values, start, stop, dim):
    rows, cols = linear_to_ij(np.arange(start, stop), dim)
    c[rows, cols] = values