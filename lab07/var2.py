import time
from mpi4py import MPI
import numpy as np

import matrix


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="MPI matrix multiplication (non-blocking scheme)")
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

    # Неблокирующая рассылка: пока данные идут, можно готовить вычисления
    req_a = comm.Ibcast(a, root=0)
    req_b = comm.Ibcast(b, root=0)
    req_a.Wait()
    req_b.Wait()

    start, stop = matrix.split_range(total, size, rank)
    local = matrix.multiply_tile(a, b, start, stop, dim)

    if rank == 0:
        # Асинхронно принимаем результаты от всех остальных процессов
        buffers = [np.empty(stop - start, dtype=np.int64) for _ in range(size)]
        requests = [
            comm.Irecv(buf, source=src, tag=src)
            for src, buf in enumerate(buffers)
            if src != 0
        ]
        MPI.Request.Waitall(requests)

        c = np.zeros((dim, dim), dtype=np.int64)
        matrix.write_tile(c, local, start, stop, dim)
        for src in range(1, size):
            s, e = matrix.split_range(total, size, src)
            matrix.write_tile(c, buffers[src], s, e, dim)

        print(f"dim={dim}, procs={size}")
        print("correct:", bool(np.array_equal(c, a @ b)))
    else:
        comm.Isend(local, dest=0, tag=rank)


if __name__ == "__main__":
    main()