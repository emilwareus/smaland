import os
import pyotp


def totp(secret):
    
    totp = pyotp.TOTP(secret)
    return totp.now()

