# -*- coding: utf-8 -*-
"""
The California Transportation Supply (CATS) model.
This is the database layer to interact with the user inputs and to generate
a python class structure to read the data
"""

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
import math

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



# Things to add
# * Generate scenario_input.xlsx
# * credits
# * policies
# * Do something with inf and 0 for constraints
# * test on production and supply limits for fuels
# add functionality to update


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
        
    def get_production(self, year):
        ProductionPathway.set_year(year)
        return ProductionPathway
    
    def blend_list(self, year):
        try:
            return self.blends[year]
        except:
            return []
        
    def get_blends(self, year, fuel, fuelpool):
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
        except:
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
        except:
            raise PermissionError("One or more sheets could not be read in the configuration file.  Make sure '{}' is closed before continuing".format(rd))
        
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
            
        except Exception as e:
            print("The scenario tempalate is corrupt or invalid.  Data could not be loaded. {}".format(e))
            raise
            
        self._status = "INITIALIZED"
    
    def _verify_data(self, year):
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
        for index, row in xls.iterrows():
            # Think about fuel pool vs compliance pool
            year = validate_numeric(row["Year"])
            benchmark = row["Benchmark"]
            standard = validate_float(row["Standard"])
            LCFS.add_benchmark(year, benchmark, standard)
            
        self.lcfs = LCFS.benchmarks
        
    def _load_creditsupply(self, xls):
        if xls.empty:
            return None
        
        for index, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            credit = row["Credit Type"]
            quantity = validate_numeric(row["Quantity"])
            
            c = Credit.get(credit)
            c.add_supply(year, quantity)
        
    def _load_creditlimits(self, xls):
        if xls.empty:
            return None
        
        for index, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            credit = row["Credit Type"]
            minimum = validate_bounds(row["Minimum"])
            maximum = validate_bounds(row["Maximum"])
            
            c = Credit.get(credit)
            c.add_limit(year, minimum, maximum)

        
    def _load_fuelpools(self, xls):
        for index, row in xls.iterrows():
            f = FuelPool.add_pool(row["Fuel Pool"])
            energy = validate_numeric(row["Energy"])/1
            f.add_demand(row["Year"], energy)
            if f.name not in self.demand:
                self.demand[f.name] = f
                
    def _load_fuellimits(self, xls): 
        if xls.empty:
            return None
        
        for index, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            fuel = row["Fuel"]
            max_amount = validate_bounds(row["Maximum Volume"])/1
            pct_change = validate_float(row["Maximum YoY Percent Change"])
            
            try:
                f = self.fuels[fuel]
            except:
                raise KeyError("{} does not appear to be a valid fuel. Cannot set production limits.".format(fuel))
            
            f.add_limit(year, max_amount, pct_change)        
            
    def _load_blends(self, xls):
        if xls.empty:
            return None
        
        for index, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            fuel = row["Produced Fuel"]
            fuelpool = row["Fuel Pool"]
            minimum = validate_float(row["Minimum Percent Energy"])
            maximum = validate_float(row["Maximum Percent Energy"])
            
            if year not in self.blends:
                self.blends[year] = []
        try:
            blend = BlendRequirement.add(fuel, fuelpool, minimum, maximum, year)
            
            if blend not in self.blends[year]:
                self.blends[year].append(blend)
        except:
            raise KeyError("Unable to add blend requirement for '{}'".format(fuel))
        
            
    def _load_fuelsupply(self, xls): 
        if xls.empty:
            return None
        
        for index, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            fuel = row["Fuel"]
            amount = validate_numeric(row["Energy"])
            policy = row["Policy Attribution"]
        
        try:
            f = Fuel.get(fuel)
            f.add_supply(year, amount, policy)
        except:
            raise KeyError("Unable to add supply. Please add '{}' as a fuel to the module first".format(fuel))
 
    
    def _load_production(self, xls):
        
        for index, row in xls.iterrows():
            year = validate_numeric(row["Year"])
            fuel = row["Fuel"]
            fuelpool = row["Fuel Pool"]
            feedstock = row["Feedstock"]
            cost = validate_numeric(row["Conversion Cost"])
            fsyield = validate_float(row["Conversion Yield"])/1
            ci = validate_float(row["Carbon Intensity"])
            subs = validate_float(row["Exogenous Subsidy"])
            credit = row["Credit Type"]
            benchmark = row["LCFS Benchmark"]
        
            f = Fuel.add_fuel(fuel, fuelpool)
            
            pathway = ProductionPathway.add_pathway(year, fuel, fuelpool, feedstock, cost, ci, fsyield, credit, benchmark)
            pathway.add_subsidy(subs)
            
            if feedstock not in self.productionpathways:
                self.productionpathways[feedstock] = []
            
            self.productionpathways[feedstock].append(fuel)
            self.fuels[f.name] = f
            self.credits[credit] = Credit.get(credit)
    
    def _load_feedstocks(self, xls):
        prices = [x for x in xls.columns if isinstance(x, int)]
        for index, row in xls.iterrows():
            if not isinstance(row["Feedstock"],str):
                continue
            fs = Feedstock.add_feedstock(row["Feedstock"])
            for price in prices:
                if math.isnan(row[price]):
                    continue
                fs.add_supply(price, row[price])
            if fs.name not in self.feedstocks:
                self.feedstocks[fs.name] = fs
            
