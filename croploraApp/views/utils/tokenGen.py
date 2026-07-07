import random
import string

def generateRandomCode(length=8):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generateRandomNumericCode(length=5):
    return "".join(random.choices(string.digits, k=length))