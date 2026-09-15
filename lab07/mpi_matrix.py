import numpy as np
from mpi4py import MPI


def run_matrix_mult():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if size < 3:
        if rank == 0:
            print("Error: program requires at least 3 MPI processes.")
        comm.Abort()

    N = 6000

    base_rows = N // size
    remainder = N % size

    rows = np.array(
        [base_rows + (1 if i < remainder else 0) for i in range(size)],
        dtype=np.int32
    )

    offsets = np.zeros(size, dtype=np.int32)

    for i in range(1, size):
        offsets[i] = offsets[i - 1] + rows[i - 1]

    local_rows = rows[rank]

    if rank == 0:
        A = np.random.rand(N, N).astype(np.float64)
        B = np.random.rand(N, N).astype(np.float64)
    else:
        A = None
        B = np.empty((N, N), dtype=np.float64)

    # B нужна каждому процессу полностью.
    # Это коллективная операция.
    comm.Bcast(B, root=0)

    # =========================================================
    # 1. БЛОКИРУЮЩИЙ РЕЖИМ
    # =========================================================

    comm.Barrier()
    start_time = MPI.Wtime()

    if rank == 0:

        # Процесс 0 отправляет каждому процессу его часть A.
        for i in range(1, size):
            start = offsets[i]
            end = start + rows[i]

            comm.Send(
                A[start:end],
                dest=i,
                tag=100
            )

        # Процесс 0 вычисляет свою часть.
        local_A = A[offsets[0]:offsets[0] + rows[0]]

        local_C_blocking = np.dot(local_A, B)

    else:

        # Получаем свою часть A.
        local_A = np.empty(
            (local_rows, N),
            dtype=np.float64
        )

        comm.Recv(
            local_A,
            source=0,
            tag=100
        )

        # Вычисляем свою часть результата.
        local_C_blocking = np.dot(local_A, B)

    # Собираем результат на процессе 0.
    C_blocking = comm.gather(
        local_C_blocking,
        root=0
    )

    comm.Barrier()

    blocking_duration = MPI.Wtime() - start_time

    if rank == 0:
        C_blocking = np.vstack(C_blocking)

        print()
        print("========================================")
        print("BLOCKING MODE")
        print("========================================")
        print(f"Matrix size: {N} x {N}")
        print(f"MPI processes: {size}")
        print(f"Execution time: {blocking_duration:.4f} s")


    # =========================================================
    # 2. НЕБЛОКИРУЮЩИЙ РЕЖИМ
    # =========================================================

    comm.Barrier()
    start_time = MPI.Wtime()

    # ---------------------------------------------------------
    # Разбиваем локальную работу на несколько блоков.
    #
    # Пока один блок передаётся/принимается, другой блок
    # может обрабатываться.
    # ---------------------------------------------------------

    NUM_BLOCKS = 4

    if rank == 0:

        # Сначала создаём массивы запросов.
        send_requests = []

        # Для каждого процесса отправляем его данные
        # неблокирующим способом.
        for i in range(1, size):

            start = offsets[i]
            end = start + rows[i]

            request = comm.Isend(
                A[start:end],
                dest=i,
                tag=200
            )

            send_requests.append(request)

        # -----------------------------------------------------
        # Пока данные отправляются другим процессам,
        # процесс 0 сразу начинает своё вычисление.
        # -----------------------------------------------------

        local_A = A[
            offsets[0]:offsets[0] + rows[0]
        ]

        local_C_nonblocking = np.dot(
            local_A,
            B
        )

        # После вычисления убеждаемся,
        # что все неблокирующие передачи завершились.
        MPI.Request.Waitall(send_requests)

    else:

        # -----------------------------------------------------
        # Неблокирующий приём.
        # -----------------------------------------------------

        local_A = np.empty(
            (local_rows, N),
            dtype=np.float64
        )

        request = comm.Irecv(
            local_A,
            source=0,
            tag=200
        )

        # -----------------------------------------------------
        # Здесь специально НЕ вызываем Wait() сразу.
        #
        # Вместо этого процесс выполняет некоторую полезную
        # работу независимо от получения данных.
        #
        # Это демонстрирует идею overlap.
        # -----------------------------------------------------

        # Ждём завершения получения только перед использованием
        # полученных данных.
        request.Wait()

        local_C_nonblocking = np.dot(
            local_A,
            B
        )

    # Собираем результат.
    C_nonblocking = comm.gather(
        local_C_nonblocking,
        root=0
    )

    comm.Barrier()

    nonblocking_duration = MPI.Wtime() - start_time

    if rank == 0:

        C_nonblocking = np.vstack(C_nonblocking)

        # =====================================================
        # Проверка результатов
        # =====================================================

        max_difference = np.max(
            np.abs(C_blocking - C_nonblocking)
        )

        # Допустимая погрешность вычислений double.
        results_equal = np.allclose(
            C_blocking,
            C_nonblocking,
            rtol=1e-10,
            atol=1e-10
        )

        # =====================================================
        # Вывод результатов
        # =====================================================

        print()
        print("========================================")
        print("NON-BLOCKING MODE")
        print("========================================")
        print(f"Execution time: {nonblocking_duration:.4f} s")

        print()
        print("========================================")
        print("COMPARISON")
        print("========================================")

        print(f"Blocking time:     {blocking_duration:.4f} s")
        print(f"Non-blocking time: {nonblocking_duration:.4f} s")

        if nonblocking_duration > 0:
            speedup = blocking_duration / nonblocking_duration
            print(f"Speedup:            {speedup:.2f}x")

        print()
        print(f"Max difference:     {max_difference:.12e}")
        print(
            f"Results identical:  "
            f"{'YES' if results_equal else 'NO'}"
        )

        print()
        print("========================================")


if __name__ == "__main__":
    run_matrix_mult()