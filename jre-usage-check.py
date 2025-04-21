import os
import sys
import subprocess
from typing import List

# if want to remote debug: uncomment the following lines
# import debugpy
# # listen on all IP for 23787port
# debugpy.listen(("0.0.0.0", 23787))
# print("waiting for debugger connected...（VS Code attach will break here）")
# debugpy.wait_for_client()
# debugpy.breakpoint()  # make vscode debugging stop here automatically


class ProcessInfo:
    def __init__(self, USER, PID, PPID, C, STIME, TTY, TIME, CMD, FULLLINE):
        self.USER = USER
        self.PID = PID
        self.PPID = PPID
        self.C = C
        self.STIME = STIME
        self.TTY = TTY
        self.TIME = TIME
        self.CMD = CMD
        self.FULLLINE = FULLLINE
        self.JAVA_EXEC = None
        # this is the absolute path of java executable, it is a real path
        self.REAL_JAVA_PATH = None
        # if the java path is a relative path
        self.RELARIVE_PATH = False


def get_real_path(path):
    """identical to the bash command `readlink -f`，works on multi level soft linke, absolute path, relative path...."""
    return os.path.realpath(path)


def get_all_processes() -> List[ProcessInfo]:
    """calling ps -ef and get the result"""
    result = subprocess.run(
        ["ps", "-ef"], stdout=subprocess.PIPE, universal_newlines=True, check=True
    )
    lines = result.stdout.strip().split("\n")
    processes: List[ProcessInfo] = []
    for line in lines[1:]:
        # ps -ef output：UID PID PPID C STIME TTY TIME CMD
        parts = line.split(None, 7)
        if len(parts) < 8:
            # the split expect to have 8 parts, but now it is less than 8, let's print the warning in red color
            print(
                f"\033[31mWarning: Line skipped due to insufficient parts: '{line}' after split, expect to have 8 parts, but now it is {len(parts)}\033[0m"
            )
            continue
        proc = ProcessInfo(
            USER=parts[0],
            PID=parts[1],
            PPID=parts[2],
            C=parts[3],
            STIME=parts[4],
            TTY=parts[5],
            TIME=parts[6],
            CMD=parts[7],
            FULLLINE=line,
        )
        processes.append(proc)
    return processes


def find_java_processes(processes: List[ProcessInfo]) -> List[ProcessInfo]:
    """return all java processes with the absolute path of JRE"""
    java_procs: List[ProcessInfo] = []
    for proc in processes:
        cmd = (
            proc.CMD
        )  # cmd contains not only the execute file but also the arguments, so we need to check the first part of the cmd
        # find java process
        # the start part maybe  /usr/bin/java ../abc/jdk/bin/java or java
        # as long as the first part of the cmd ends with java, we can consider it as a java process
        java_exec = cmd.split()[0]
        print(f"chekcing command: '{java_exec}'")
        if not java_exec.endswith("java"):
            # this is not a java process, so skip it
            print(f"It's not a java process, skip command: '{cmd}'")
            continue

        if not cmd.startswith("/"):
            # this is NOT absolute path, as of the permission limataion, we can't get the real path of it
            # so output waring
            print(
                f"\033[33mWarning: The command '{cmd}' is not an absolute path of java, so we can't get the real path of jre\033[0m"
            )
            # but we still keep it in the list so we can output summary later
            proc.RELARIVE_PATH = True

        proc.JAVA_EXEC = java_exec
        proc.REAL_JAVA_PATH = get_real_path(java_exec)
        java_procs.append(proc)
    return java_procs


def main():

    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <JRE Path to check>")
        sys.exit(1)

    input_jre = sys.argv[1]
    input_real_jre = get_real_path(input_jre)
    print(
        f"Checking if any process is running with the jar path: '{input_real_jre}' (orignal input: '{input_jre}')"
    )

    # input_real_jre can be not the full jre path which inludes the java file, it can be just the prefix， this will get all the java processes as long as the java path starts with the input path

    processes = get_all_processes()
    java_procs = find_java_processes(processes)

    matched: List[ProcessInfo] = []
    for proc in java_procs:
        if proc.RELARIVE_PATH:
            # this is not an absolute path, so we can't get the real path of it
            # so we skip it
            continue
        # check if the java path starts with the input path
        real_java: str = proc.REAL_JAVA_PATH
        if real_java.startswith(input_real_jre):
            matched.append(proc)

    # print in green color
    print("\033[32m" + "Summary" + "\033[0m\n")
    print(f"The inputed JRE path: {input_jre}")
    print(f"final full JRE path: {input_real_jre}")
    print(f"\nThe processes that use this JRE:\n")

    if not matched:
        print("Not Found")
    else:
        for proc in matched:
            # print with blue color
            print(f"User: \033[34m{proc.USER}\033[0m")
            print(f"Process PID: {proc.PID}")
            # print with pink color
            print(f"JRE Actual Path: \033[35m{proc.REAL_JAVA_PATH}\033[0m")
            print(f"ps -ef Info: {proc.FULLLINE}")
            print("-" * 80)

    # now print the summary of the processes which is not absolute path
    print(
        "\n\n\033[33mThe processes that are not absolute path (if has any output must check with the user as the relative path can't be evaluated):\033[0m\n"
    )
    for proc in java_procs:
        if not proc.RELARIVE_PATH:
            # this is an absolute path, so we skip it
            continue
        # print with red color
        print(f"User: \033[34m{proc.USER}\033[0m")
        print(f"Process PID: {proc.PID}")
        print(f"JRE Actual Path: {proc.REAL_JAVA_PATH}")
        print(f"ps -ef Info: {proc.FULLLINE}")
        print("-" * 80)

    print("\n\n\033[32mDone\033[0m")


if __name__ == "__main__":
    main()
