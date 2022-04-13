# -*- coding: utf-8 -*-
# Copyright 2021 California Air Resources Board
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pandas as pd
def validate_numeric(value):
    if pd.isna(value):
        return int(0)

    try:
        return int(value)
    except ValueError as error:
        raise ValueError("Entered input was not a valid number.") from error


def validate_bounds(value):
    if float(value) == float("inf"):
        return float('inf')

    if float(value) == float('-inf'):
        return float('-inf')

    return validate_numeric(value)

def validate_float(value):
    if pd.isna(value):
        return float(0)
    try:
        return float(value)

    except ValueError as error:
        raise ValueError("Entered value was not a valid decimal.") from error

def validate_string(value):
    try:
        return str(value)

    except ValueError as error:
        raise ValueError("Entered value is not a valid string") from error


def closest_value(search, items, positive_value=False):
    if positive_value:
        return min(items, key = lambda key: float('inf') if (search-key) >0 else abs(search-key))

    return min(items, key = lambda key: abs(search-key))

def write_output(variable, output_file = "output.txt"):

    with open(output_file, "w") as file:
        file.write(variable)
