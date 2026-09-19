"""Умножение матриц: блочная схема с широковещательной рассылкой и gather."""
import time
from mpi4py import MPI
import numpy as np

import matrix


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="MPI matrix multiplication (block scheme)")
    parser.add_argument("-n", "--dim", type=int, default=600,
                        help="размер квадратной матрицы (по умолчанию 600)")
    return parser.parse_args()


def main():
    args = parse_args()
    dim = args.dim
    total = dim * dim

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    rng = np.random.default_rng(seed=0)
    a = rng.integers(0, 10, size=(dim, dim), dtype=np.int64)
    b = rng.integers(0, 10, size=(dim, dim), dtype=np.int64)

    comm.Bcast(a, root=0)
    comm.Bcast(b, root=0)

    start, stop = matrix.split_range(total, size, rank)
    local = matrix.multiply_tile(a, b, start, stop, dim)

    # Собираем на корне массив значений и границы каждого процесса
    all_values = comm.gather(local, root=0)
    all_bounds = comm.gather((start, stop), root=0)

    if rank == 0:
        c = np.zeros((dim, dim), dtype=np.int64)
        for values, (s, e) in zip(all_values, all_bounds):
            matrix.write_tile(c, values, s, e, dim)

        expected = a @ b
        print(f"dim={dim}, procs={size}")
        print("correct:", bool(np.array_equal(c, expected)))


if __name__ == "__main__":
    main()