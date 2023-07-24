# -*- coding: utf-8 -*-
# Copyright 2022 California Air Resources Board
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

from cats import runopt

import argparse
import os



if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='CATS', usage='%(prog)s [options]', description="Run the CATS model with arguments specified.")
    parser.add_argument("-t", type=str, nargs='+', help="Will generate a new template of name")
    parser.add_argument("-v", action="store_true", help="Will generate verbose results for each year run")
    parser.add_argument("-i", action="store_true", help="Will disable autoincrementation of years")
    args = parser.parse_args()

    if not os.path.isfile("config.ini"):
        raise FileExistsError("config.ini was not found in the CATS directory.")
    if args.v:
        print("Verbose output enabled")


    if args.t:

        print("Generating a new template for scenario '{}'...".format(args.t[0]))
        runopt.generate_template(args.t[0])
    else:
        runopt.run(verbose=args.v, disableautoincrement=args.i)
