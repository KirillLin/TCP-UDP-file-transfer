```markdown
# РУКОВОДСТВО
___
## Требования
___

### Linux (Ubuntu/Debian)

```bash
sudo apt update && sudo apt upgrade

pip install mpi4py

sudo apt install python3-mpi4py

pip install numpy

sudo apt-get install openssh-server openssh-client

sudo systemctl start ssh

sudo apt install openmpi-bin openmpi-common libopenmpi-dev

sudo ufw disable
```

### Windows

1. Установите **Microsoft MPI (MS-MPI)**:
   - Скачайте и установите `msmpisetup.exe` и `msmpisdk.msi` с официального сайта Microsoft:
     https://learn.microsoft.com/en-us/message-passing-interface/microsoft-mpi
   - После установки добавьте в переменную среды `PATH` путь к `mpiexec.exe`
     (обычно `C:\Program Files\Microsoft MPI\Bin\`).

2. Установите **Python 3.10+** (обязательно одинаковой версии на всех узлах)
   с https://www.python.org/downloads/ (галочка «Add Python to PATH»).

3. Установите зависимости:

```powershell
pip install mpi4py==4.0.0
pip install numpy==2.1.1
```

4. Установите **OpenSSH Server** (для приёма подключений) и **OpenSSH Client**:
   - «Параметры» → «Приложения» → «Дополнительные компоненты» →
     добавьте «Клиент OpenSSH» и «Сервер OpenSSH».
   - Запустите службу:

```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

5. Откройте порт 22 в брандмауэре:

```powershell
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' `
  -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

> **Важно:** для запуска `mpiexec` на Windows используется `mpiexec.exe`
> из MS-MPI, а не `mpiexec` из OpenMPI. На всех узлах должна быть
> установлена одинаковая версия MS-MPI.

### macOS

1. Установите **Homebrew** (если ещё не установлен):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Установите OpenMPI и Python:

```bash
brew install open-mpi
brew install python@3.11
```

3. Установите зависимости:

```bash
pip3 install mpi4py==4.0.0
pip3 install numpy==2.1.1
```

4. Включите **Удалённый вход** (SSH-сервер):
   - «Системные настройки» → «Основные» → «Общий доступ» →
     включите «Удалённый вход».

5. Проверьте, что SSH-клиент доступен:

```bash
ssh localhost
```

!!! ВНИМАНИЕ !!!

Версии пакетов и библиотек должны совпадать на всех узлах.
Особенно:
- numpy
- mpi
- python

## Запуск
___
### 1. Создание пользователей
___
Создайте 3 пользователей с одинаковым именем и паролем.

**Пример пользователя:**
   - пользователь: *user-lab03*
   - пароль: *1234*

**Пример узлов:**
   - 10.188.64.252
   - 10.188.64.156
   - 10.188.64.162

### 2. Подготовка окружения
___
#### Компьютер 1 (10.188.64.252) — главный узел
___
Заполните файл *hosts.txt*.

```plain-text
# hosts.txt

10.188.64.252 slots=6 // число слотов
10.188.64.156 slots=2
10.188.64.162 slots=4
```

Выполните следующие команды.

**Linux / macOS:**

```bash
ssh-keygen          # нажмите Enter и введите "yes"

ssh-copy-id user-lab03@10.188.64.156
ssh-copy-id user-lab03@10.188.64.162

mpiexec --hostfile hosts.txt python3 var1.py
mpiexec --hostfile hosts.txt python3 var2.py
```

**Windows (PowerShell):**

```powershell
ssh-keygen          # нажмите Enter

# Копирование ключа (ssh-copy-id отсутствует в Windows — используем type)
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh user-lab03@10.188.64.156 "cat >> .ssh/authorized_keys"
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh user-lab03@10.188.64.162 "cat >> .ssh/authorized_keys"

mpiexec -hostfile hosts.txt python var1.py
mpiexec -hostfile hosts.txt python var2.py
```

> На Windows используется `mpiexec` из MS-MPI и `python` вместо `python3`.

Проверить соединение можно командами:

```bash
ssh user-lab03@10.188.64.156
ssh user-lab03@10.188.64.162
```

#### Компьютер 2 (10.188.64.162) — рабочий узел
___

Исходные файлы должны находиться в корневой директории
(**/home/user-lab03/** на Linux/macOS, **C:\\Users\\user-lab03\\** на Windows).

**Linux / macOS:**

```bash
ssh-keygen
ssh-copy-id user-lab03@10.188.64.162
```

**Windows (PowerShell):**

```powershell
ssh-keygen
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh user-lab03@10.188.64.162 "cat >> .ssh/authorized_keys"
```

Проверка соединения:

```bash
ssh user-lab03@10.188.64.162
```

#### Компьютер 3 (10.188.64.156) — рабочий узел
___

Исходные файлы должны находиться в корневой директории
(**/home/user-lab03/** на Linux/macOS, **C:\\Users\\user-lab03\\** на Windows).

**Linux / macOS:**

```bash
ssh-keygen
ssh-copy-id user-lab03@10.188.64.156
```

**Windows (PowerShell):**

```powershell
ssh-keygen
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh user-lab03@10.188.64.156 "cat >> .ssh/authorized_keys"
```

Проверка соединения:

```bash
ssh user-lab03@10.188.64.156
```
```