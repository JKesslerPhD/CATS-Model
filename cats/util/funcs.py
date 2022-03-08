# -*- coding: utf-8 -*-
"""
Created on Tue Feb 15 08:36:08 2022

@author: jkessler
"""

import pandas as pd
def validate_numeric(value):
    if pd.isna(value):
        return int(0)
    
    try:
        return int(value)
    except:
        raise ValueError("Entered input was not a valid number.")
        

def validate_bounds(value):
    if float(value) == float("inf"):
        return float('inf')
    
    else:
        return validate_numeric(value)
    
def validate_float(value):   
    if pd.isna(value):
        return float(0)
    try:
        return float(value)
    
    except:
        raise ValueError("Entered value was not a valid decimal.")

def validate_string(value):
    try:
        return str(value)
    
    except:
        raise ValueError("Entered value is not a valid string")
        

def closest_value(search, items, positive_value=False):
    if positive_value:
        return min(items, key = lambda key: float('inf') if (search-key) >0 else abs(search-key))
    else:
        return min(items, key = lambda key: abs(search-key))

def write_output(variable, output_file = "output.txt"):

    file = open(output_file, "w")
    file.write(variable)
    file.close()
