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
# See the License for the specific language governing permissions ands
# limitations under the License.

import os
import cats
from cats.backend.scenarios import GetScenarios
from cats.backend.data import Loader
from cats.backend.setuplp import Model
from cats.backend.data import Template
import pandas as pd


def generate_template(scenario_name):
    conf = os.path.abspath(os.path.join(os.path.dirname(cats.__file__),"..","config.ini"))
    slist = GetScenarios(conf)
    Template(slist.scenario_folder, scenario_name)


def run(verbose = False, disableautoincrement=False):
    conf = os.path.abspath(os.path.join(os.path.dirname(cats.__file__),"..","config.ini"))
    slist = GetScenarios(conf)

    print("The following scenarios exist that were specified in the config file: {}".format(slist))


    # Load data for one specific scenario
    for scenario in slist.keys():
        if scenario in slist.years:
            years = slist.years[scenario]
        else:
            years = slist.years["all"]

        data = Loader(slist[scenario])
        data.load()
        model = Model(data)

        if slist.production_change:
            model.set_default_production(slist.production_change)

        for year in years:
            print("\n\nRunning model...  Scenario: {}. Year: {}".format(scenario, year))
            results_name = "{}_{}.txt".format(scenario, year)
            if year - 1 == model.get_year():
                if not disableautoincrement:
                    print("Incrementing by 1 year...")
                    model.increment_time()
            else:
                model.optimize(year)

            if model.status == model.solver.OPTIMAL:
                if verbose:
                    print("\nSaving Solutions to file {}".format(results_name))
                    model.show_solutions("results/{}/{}".format(scenario, results_name))
                model.save_results(verbose)

            if model.status == model.solver.INFEASIBLE:
                print("\n\n A constraint was specified that cannot be met.  Results are not being saved.")
                print("\n\nModel runs could not complete. Exiting Model")
                return

            if model.status == model.solver.ABNORMAL:
                print("The model was unable to converge.  An abnormal solution resulted. Try adjusting unit magnitudes for inputs")
            df = pd.DataFrame.from_dict(model.results)
            df.index.name = "Variable"
            print("Model results saved to '{}.xlsx'".format(scenario))
            df.to_excel("results/{}.xlsx".format(scenario))
