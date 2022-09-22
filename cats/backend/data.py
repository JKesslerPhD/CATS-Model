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

"""
The California Transportation Supply (CATS) model.
This is the database layer to interact with the user inputs and to generate
a python class structure to read the data
"""

import os
import math
import pandas as pd

from cats.util.funcs import validate_numeric
from cats.util.funcs import validate_bounds
from cats.util.funcs import validate_float
from cats.backend.datatypes import Fuel
from cats.backend.datatypes import FuelPool
from cats.backend.datatypes import LCFS
from cats.backend.datatypes import ProductionPathway
from cats.backend.datatypes import Credit
from cats.backend.datatypes import Feedstock
from cats.backend.datatypes import BlendRequirement
from cats.backend.datatypes import Coproducts



class Template():
    def __init__(self, scenario_folder, scenario_name):
        self.workbook = os.path.join(scenario_folder, scenario_name, "scenario_inputs.xlsx")

        if os.path.isfile(self.workbook):
            raise FileExistsError("'{}' scenario_inputs.xlsx template already exists.  Template will not been overwritten.".format(scenario_name))
        else:
            try:
                os.makedirs(os.path.join(scenario_folder, scenario_name))
            except FileExistsError:
                print("""'{}' scenario folder created.  Template does not exist. Adding template to folder...""".format(scenario_name))

        self.build_worksheets()


    def build_worksheets(self):

        fstck = {"Feedstock":[], "Units":[]}
        for value in range(25, 1625, 25):
            fstck[value] = []


        workbook = {"Energy Demand":
                        {"Year":[],
                         "Fuel Pool":[],
                         "Energy":[],
                         "Exceed?":[],},

                    "Defined Supply": {
                        "Year":[],
                        "Fuel":[],
                        "Energy":[],
                        "Policy Attribution":[]},

                    "Coproducts": {
                        "Fuel":[],
                        "Base Fuel":[],
                        "Production Multiplier":[]},


                    "Fuel Production": {
                        "Year":[],
                        "Fuel":[],
                        "Fuel Pool":[],
                        "Feedstock":[],
                        "Conversion Cost":[],
                        "Units Notes":[],

                        "Conversion Yield":[],
                        "Conversion Units":[],
                        "Carbon Intensity":[],
                        "Units":[],
                        "EER":[],
                        "Refernces":[],
                        "Exogenous Subsidy":[],
                        "Subsidy Unit Notes":[],
                        "Credit Type":[],
                        "LCFS Benchmark":[],
                        "Blend Requirement":[],
                        "Results Name":[],
                        "Results Units":[],
                        "Results Multiplier":[],
                        "Results Notes":[]},


                    "Production Limits": {
                        "Year":[],
                        "Fuel":[],
                        "Maximum Volume":[],
                        "Maximum YoY Percent Change":[]},

                    "Feedstock": fstck,

                    "LCFS Benchmark":{
                        "Year":[],
                        "Benchmark":[],
                        "Standard":[]},

                    "Credit Type Limits":{
                        "Year":[],
                        "Credit Type":[],
                        "Minimum":[],
                        "Maximum":[]},

                    "Additional Credits":{
                        "Year":[],
                        "Credit Type":[],
                        "Quantity":[]},

                    "Blend Requirements":{
                        "Year":[],
                        "Requirement Name":[],
                        "Fuel Pool":[],
                        "Minimum Percent Energy":[],
                        "Maximum Percent Energy":[]}

                    }
        with pd.ExcelWriter(self.workbook) as writer:
            for wksht, cols in workbook.items():
                data = pd.DataFrame(cols)
                data.to_excel(writer, sheet_name=wksht, index=False)



class Loader():
    def __init__(self, file):
        self.demand = {}
        self.fuels = {}
        self.feedstocks = {}
        self.productionpathways = {}
        self.periods = None
        self.policies = []
        self.credits = {}
        self._file = file
        self.lcfs = None
        self.blends = {}
        self._status = "NO DATA"

    @staticmethod
    def get_production(year):
        ProductionPathway.set_year(year)
        return ProductionPathway

    def blend_list(self, year):
        try:
            return self.blends[year]
        except KeyError:
            return []

    def get_coproducts(self):
        return Coproducts

    @staticmethod
    def get_blends(year, fuel, fuelpool):
        """


        Parameters
        ----------
        year : TYPE
            DESCRIPTION.
        fuel : TYPE
            DESCRIPTION.
        fuelpool : TYPE
            DESCRIPTION.

        Returns
        -------
        TYPE
            DESCRIPTION. Returns 0 if requirement doesn't exist, otherwise returns (minimum, maximum)

        """
        try:
            req = BlendRequirement.get(year, fuel, fuelpool)
        except KeyError:
            return (0, 0)

        return (req.minimum, req.maximum)

    def __repr__(self):
        return self._status

    def reset(self):
        """
        Clears all stored data in the object

        Returns
        -------
        None.

        """
        self.demand.clear()
        self.fuels.clear()
        self.feedstocks.clear()
        self.productionpathways.clear()
        self.credits.clear()
        self.blends.clear()
        self._status = "NO DATA"

        Fuel.reset()
        FuelPool.reset()
        LCFS.reset()
        ProductionPathway.reset()
        Credit.reset()
        Feedstock.reset()
        BlendRequirement.reset()
        Coproducts.reset()

        return True

    def load(self):
        """
        Will run the functions to move data from the excel scenario file into a data class

        Raises
        ------
        PermissionError
            The spreadsheet is likely not closed, and is therefore locked to reading and writing.

        Returns
        -------
        None.

        """
        self.reset()
        rd = self._file
        try:
            demand = pd.read_excel(rd, "Energy Demand")
            supply = pd.read_excel(rd, "Defined Supply")
            production = pd.read_excel(rd, "Fuel Production")
            productionlimits = pd.read_excel(rd, "Production Limits")
            feedstock = pd.read_excel(rd, "Feedstock")
            lcfs = pd.read_excel(rd, "LCFS Benchmark")
            creditlimits = pd.read_excel(rd, "Credit Type Limits")
            creditsupply = pd.read_excel(rd, "Additional Credits")
            blends = pd.read_excel(rd, "Blend Requirements")
            coproducts = pd.read_excel(rd, "Coproducts")
        except PermissionError as error:
            raise PermissionError("One or more sheets could not be read in the configuration file.  Make sure '{}' is closed before continuing".format(rd)) from error

        try:
            self._load_fuelpools(demand)
            self._load_feedstocks(feedstock)
            self._load_production(production)
            self._load_fuelsupply(supply)
            self._load_fuellimits(productionlimits)
            self._load_creditlimits(creditlimits)
            self._load_lcfs(lcfs)
            self._load_creditsupply(creditsupply)
            self._load_blends(blends)
            self._load_coproducts(coproducts)

        except Exception as e:
            print("The scenario tempalate is corrupt or invalid.  Data could not be loaded. {}".format(e))
            raise

        self._status = "INITIALIZED"

    def verify_data(self, year):
        """
        Checks that the data input for a given year can meet basic constraints

        Parameters
        ----------
        year : TYPE int
            DESCRIPTION. the year for which the model is going to be run

        Raises
        ------
        KeyError
            DESCRIPTION. The model will not be able to covnerge for the specified year with the defined inputs

        Returns
        -------
        None.

        """

        #TODO: add something to verify LCFS benchmarks exist for pathways
        # add something to verify blend production can be met

        for fuelpool in self.demand.keys():
            valid_paths = ProductionPathway.get_fuel_pool(fuelpool, year)
            if not valid_paths:
                raise KeyError("There are not valid production pathways to satisy demand for the {} fuel pool".format(fuelpool))
            energy_supply = 0
            energy_demand = self.demand[fuelpool][year]
            for path in valid_paths:
                energy_supply = energy_supply + path.feedstock.Ub()*path.yields

            if energy_supply < energy_demand:
                raise KeyError("While valid production pathways exist for the {} fuel pool, only {} can be supplied compared to {} needed".format(fuelpool, energy_supply, energy_demand))

    def _load_lcfs(self, xls):
        for _, row in xls.iterrows():
            # Think about fuel pool vs compliance pool
            year = validate_numeric(row["Year"])
            benchmark = row["Benchmark"]
            standard = validate_float(row["Standard"])
            LCFS.add_benchmark(year, benchmark, standard)

        self.lcfs = LCFS.benchmarks

    @staticmethod
    def _load_creditsupply(xls):
        if xls.empty:
            return

        for _, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            credit = row["Credit Type"]
            quantity = validate_numeric(row["Quantity"])

            c = Credit.get(credit)
            c.add_supply(year, quantity)

    @staticmethod
    def _load_creditlimits(xls):
        if xls.empty:
            return

        for _, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            credit = row["Credit Type"]
            minimum = validate_bounds(row["Minimum"])
            maximum = validate_bounds(row["Maximum"])

            c = Credit.get(credit)
            c.add_limit(year, minimum, maximum)


    def _load_fuelpools(self, xls):
        for _, row in xls.iterrows():
            f = FuelPool.add_pool(row["Fuel Pool"])
            energy = validate_numeric(row["Energy"])/1
            limit = row["Exceed?"]
            f.add_demand(row["Year"], energy, limit)
            if f.name not in self.demand:
                self.demand[f.name] = f

    def _load_fuellimits(self, xls):
        if xls.empty:
            return

        for _, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            fuel = row["Fuel"]
            max_amount = validate_bounds(row["Maximum Volume"])/1
            pct_change = validate_float(row["Maximum YoY Percent Change"])

            try:
                f = self.fuels[fuel]
            except KeyError as error:
                raise KeyError("{} does not appear to be a valid fuel. Cannot set production limits.".format(fuel)) from error

            f.add_limit(year, max_amount, pct_change)

    def _load_blends(self, xls):
        if xls.empty:
            return

        for _, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            requirement = row["Requirement Name"]
            fuelpool = row["Fuel Pool"]
            minimum = validate_float(row["Minimum Percent Energy"])
            maximum = validate_float(row["Maximum Percent Energy"])

            if year not in self.blends:
                self.blends[year] = []
            try:
                blend = BlendRequirement.add(requirement, fuelpool, minimum, maximum, year)

                if blend not in self.blends[year]:
                    self.blends[year].append(blend)
            except KeyError as error:
                raise KeyError("Unable to add blend requirement for '{}'".format(requirement)) from error

    def _load_coproducts(self, xls):
        if xls.empty:
            return

        for _, row in xls.iterrows():
            fuel = row["Fuel"]
            basefuel = row["Base Fuel"]
            multiplier = row["Production Multiplier"]

            if fuel not in self.fuels:
                raise KeyError("{} is not a valid fuel.  Cannot be defined as a coproduct of {}".format(fuel, basefuel))

            if basefuel not in self.fuels:
                raise KeyError("{} is not a valid base fuel.  {} cannot be defined as a coproduct.".format(basefuel, fuel))

            Coproducts.add_coproduct(fuel, basefuel, multiplier)

    @staticmethod
    def _load_fuelsupply(xls):
        if xls.empty:
            return

        for _, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            fuel = row["Fuel"]
            amount = validate_numeric(row["Energy"])
            policy = row["Policy Attribution"]

            try:
                f = Fuel.get(fuel)
                f.add_supply(year, amount, policy)
            except KeyError as error:
                raise KeyError("Unable to add supply. Please add '{}' as a fuel to the module first".format(fuel)) from error


    def _load_production(self, xls):

        for _, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            fuel = row["Fuel"]
            fuelpool = row["Fuel Pool"]
            feedstock = row["Feedstock"]
            cost = validate_numeric(row["Conversion Cost"])
            fsyield = validate_float(row["Conversion Yield"])/1
            ci = validate_float(row["Carbon Intensity"])
            eer = validate_float(row["EER"])
            subs = validate_float(row["Exogenous Subsidy"])
            credit = row["Credit Type"]
            benchmark = row["LCFS Benchmark"]
            blend = row["Blend Requirement"]
            runits = row["Results Units"]
            raggregator = row["Results Name"]
            rmultiplier = row["Results Multiplier"]

            f = Fuel.add_fuel(fuel, fuelpool)

            pathway = ProductionPathway.add_pathway(year, fuel, fuelpool,
                                                    feedstock, cost, ci, fsyield,
                                                    credit_type = credit,
                                                    blend = blend,
                                                    benchmark = benchmark,
                                                    eer = eer,
                                                    raggregator = raggregator,
                                                    rmultiplier = rmultiplier,
                                                    runits = runits
                                                    )
            pathway.add_subsidy(subs)

            if feedstock not in self.productionpathways:
                self.productionpathways[feedstock] = []

            self.productionpathways[feedstock].append(fuel)
            self.fuels[f.name] = f
            self.credits[credit] = Credit.get(credit)

    def _load_feedstocks(self, xls):
        prices = [x for x in xls.columns if isinstance(x, int)]
        for _, row in xls.iterrows():
            if not isinstance(row["Feedstock"],str):
                continue
            fs = Feedstock.add_feedstock(row["Feedstock"])
            for price in prices:
                if math.isnan(row[price]):
                    continue
                fs.add_supply(price, row[price])
            if fs.name not in self.feedstocks:
                self.feedstocks[fs.name] = fs
