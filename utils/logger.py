class BColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_message(module, message):
    print(f"{BColors.OKGREEN}[VitrozeRestauration - {module}] {message}{BColors.ENDC}")


def print_error(module, message):
    print(f"{BColors.FAIL}[VitrozeRestauration - {module}] [ERREUR] : {message}{BColors.ENDC}")


def print_log(module, message):
    print(f"{BColors.OKBLUE}[VitrozeBot - {module}] [LOG] : {message}{BColors.ENDC}")
