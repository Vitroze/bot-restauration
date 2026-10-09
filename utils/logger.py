class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def printMessage(MODULE, message):
    print(f"{bcolors.OKGREEN}[VitrozeRestauration - {MODULE}] {message}{bcolors.ENDC}")

def printError(MODULE, message):
    print(f"{bcolors.FAIL}[VitrozeRestauration - {MODULE}] [ERREUR] : {message}{bcolors.ENDC}")

def printLog(MODULE, message):
    print(f"{bcolors.OKBLUE}[VitrozeBot - {MODULE}] [LOG] : {message}{bcolors.ENDC}")
