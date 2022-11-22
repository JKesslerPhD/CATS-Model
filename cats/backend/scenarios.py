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

import configparser
import os
import re

class GetScenarios():
    def __init__(self, filepath='config.ini'):
        """


        Parameters
        ----------
        filepath : TYPE, optional
            DESCRIPTION. The default is 'config.ini'.

        Returns
        -------
        Returns the set of scenarios and locations of each scenario to run

        """
        self.filepath = filepath
        self.scenarios = {}
        self.scenario_folder = None
        self.results_folder = None
        self.production_change = None
        self.results = {}
        self.years = {}

        self.read_config(filepath)

    def __repr__(self):
        return str(list(self.scenarios.keys()))

    def __iter__(self):
        return iter(self.scenarios.items())

    def keys(self):
        return self.scenarios.keys()

    def values(self):
        return self.scenarios.values()

    def __getitem__(self, name):
        return self.scenarios[name]

    def read_config(self, filepath):
        config = configparser.ConfigParser()
        config.read(filepath)
        dirname = os.path.dirname(filepath)

        self.scenario_folder = os.path.join(dirname, config["scenarios"]["folder"])

        try:
            self.results_folder = os.path.join(dirname, config["results"]["folder"])
        except KeyError:
            self.results_folder = os.path.join(dirname, "results/")

        try:
            self.production_change = config["options"]["productionlimits"]
        except KeyError:
            print("No default production limit supplied.")
        self.validate_scenarios(config["scenarios"]["list"])
        try:
            self.get_model_years(config["years"])
        except KeyError as error:
            raise KeyError("No years were provided for model runs. \
                           This needs to be set for each scenario, or \
                               'all' needs to be defined.") from error

    def get_model_years(self, scenario):
        # return a list of all the years to load
        year_list = {}
        for _, scen in self.scenarios.items():
            try:
                year_list[scen] = self._year_parse(scenario[scen])
            except KeyError:
                continue

        if "all" in scenario:
            year_list["all"] = self._year_parse(scenario["all"])

        self.years = year_list

    def _year_parse(self, string):
        try:
            return [int(string)]

        except ValueError:
            pass

        if "," in string:
            years = [x.strip() for x in string.split(",")]
        else:
            years = string.split("-")
            try:
                minimum = int(years[0])
                maximum = int(years[1])+1
            except ValueError as error:
                raise Exception("Format for years in the \
                                config file was invalid. {}".format(string)) from error
            years = list(range(minimum, maximum))

        # check to get full years
        return_years = []
        for year in years:
            try:
                year = int(year)
                return_years.append(year)
            except ValueError:
                additional_range = self._year_parse(year)
                for extra_year in additional_range:
                    return_years.append(extra_year)



        return return_years

    def validate_scenarios(self, scenarios):
        if scenarios == "all":
            try:
                scenario_list = os.listdir(self.scenario_folder)
            except FileNotFoundError as error:
                raise Exception("The scenario folder '{}' \
                                cannot be found".format(self.scenario_folder)) from error
        else:
            scenario_list = [x.strip() for x in scenarios.split(",")]

        for scenario in scenario_list:
            pattern = "scenario_inputs.*\.xlsx"
            file="scenario_inputs.xlsx"
            filenames = next(os.walk(os.path.join(self.scenario_folder,scenario)), (None, None, []))[2]  # [] if no file

            for file in filenames:
                if re.match(pattern, file):
                    break

            file_path = os.path.join(self.scenario_folder,scenario, file)

            results_path = os.path.join(self.results_folder,scenario)
            if os.path.exists(file_path):
                self.scenarios[scenario] = file_path
                if not os.path.exists(results_path):
                    os.makedirs(results_path)
                self.results[scenario] = os.path.join(results_path,"full_results.txt")
