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

import cats
from cats.backend.scenarios import GetScenarios
from cats.backend.data import Loader
from cats.backend.setuplp import Model
import os


# Get list of Scenarios
def run():
    conf = os.path.abspath(os.path.join(os.path.dirname(cats.__file__),"..","config.ini"))
    slist = GetScenarios(conf)
    
    print("Scenarios to choose from: {}".format(slist))

    
    # Load data for one specific scenario
    for scenario, path in slist:
        if scenario in slist.years:
            years = slist.years[scenario]
        else:
            years = slist.years["all"]
        
        d = Loader(slist[scenario])
        d.load()
        m = Model(d)
        for year in years:
            print("\n\nRunning model...  Scenario: {}. Year: {}".format(scenario, year))
            results_name = "{}_{}.txt".format(scenario, year)
            if year+1 == m._year:
                m.increment_time()
            else:
                m.optimize(year)
            print("\nSaving Solutions to file {}".format(results_name))
            m.show_solutions("results/{}/{}".format(scenario,results_name))
        
        
        
    


