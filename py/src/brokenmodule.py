# import foo

import argparse

def blah():
    print("yes")

def init(args:argparse.Namespace=None, **kwargs:dict) -> bool:
    return True

def buildargs(argparse.Namespace, **kwargs:dict):
    return None

def access(args, op:str, **kwargs:dict) -> bool:
    return True

def main(args, **kwargs:dict):
    blah()
