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


#########################
### Model Explanation ###
#########################
# Variables are the amount of feedstock used to generate fuel for a specific 
# fuel pathway pathway at a specific feedstock price
# Minimize total cost of fuel supply, subject to constraints

# Constraints:
        # Feedstock does not exceed feedstock availability
        # Fuel Pool CI does not exceed LCFS Constraint
        # Credit types generated do not exceed credit amount constraint
        # Fuel pool supply >= Fuel Demand

# Tests to Run:
    # Make sure supply constraints in a given year do not exceed limit constraints

# Still to implement:
# * Reading model outputs and generating past-year data.

from ortools.linear_solver import pywraplp
        
class Model():    
    def __init__(self, data):
        # Move instance attributes to dictionaries (tolerance, default production limit)
        self.solver = pywraplp.Solver("CATS Instance",pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)
        self.objective = self.solver.Objective()
        self.objective.SetMinimization()
        
        self._year = None
        self.data = data
        self.variables = {}
        self.constraints = {}
        self.status = None
        self.deficit_fuels = []
        self._tolerance = 1e-6
        self._default_production_limit = 0.40
        self._prior_solution = {}
        
        if data._status == "NO DATA":
            raise Exception("The data variable passed to the model does not contain data.")
        
        # Sequence:
        #   * Loop through production pathways
        #       * Define variable: Quantity Fuel
        #          set objective function: min(Total Cost): 
        #           sum( Quantity Fuel *[ (Feedstock Cost + Conversion Cost)/Yield - Exogenous Subsidy] )
        #       * Define feedstock variables: (feedstock_p)
        #       * Define Feedstock Constraints:
        #               sum(Feedstock_p) < total
        #
        # Constraints Feedstock Constraint
    def _set_tolerance(self):
        tolerance = self._tolerance*10
        self.solver.SetSolverSpecificParametersAsString("solution_feasibility_tolerance: %f" 
                                                        % tolerance)
        self._tolerance = tolerance
    
    def set_default_production(self, limit):
        """
        The percent change that a given fuel can ramp up or down in a year 
        compared to a previous year

        Parameters
        ----------
        limit : float
            DESCRIPTION.

        Returns
        -------
        None.

        """
        
        try:
            self._default_production_limit = float(limit)
        except ValueError as error:
            raise ValueError("The provided limit is not a valid decimal value") from error
        
    def show_solutions(self, to_text=None):
        output = ""
        output+="\nConstraint Info\n"
        c_res = self.solver.ComputeConstraintActivities()
        integer = 0
        for constraint in self.solver.constraints():
            output+="\n{}: {}. Dual: {}".format(constraint.name(), c_res[integer], constraint.DualValue())
            integer = integer + 1
        
        output+="\n\nVariable Values\n"
        for variable in self.solver.variables():
            if variable.SolutionValue() != float(0):
                output+="\n{}: {}".format(variable.name(), variable.SolutionValue())
                
        if to_text:
            with open(to_text, 'w') as f:
                f.write(output)
            return "Output printed to file {}".format(to_text)
        
        return output
    
    def calculate_fuel_supply(self, disaggregate_feedstock=False):
        if self.status != 0:
            raise Exception("Model has not converged on a solution.")
            
        pathways = self.data.get_production(self._year)
        supply = {}
        for fuel, feedstocks in self.variables["feedstock"].items():
            quantity = 0
            for feedstock, prices in feedstocks.items():
                yields = pathways.get(feedstock, fuel).yields
                key = fuel
                if disaggregate_feedstock:
                    quantity = 0
                    key = "{}_{}".format(fuel, feedstock)
                quantity = quantity + sum(x.SolutionValue() for x in prices)*yields
                if quantity > 0:
                    supply[key] = quantity
                    
        return supply
    def optimize(self, year=2020, increment_time = False):
        self.set_year(year)
        
        if not increment_time:
            # Clears any prior solution data from being used to set constraints
            self._prior_solution.clear()
        
        self.data._verify_data(year)
        
        # Adds the variables to the model
        self._add_feedstocks()
        
        # Adds the model constraints
        self._add_constraints()
        
        # Solves the linear programming problem
        self.status = self.solver.Solve()
        if self.status == self.solver.ABNORMAL:
            if self._tolerance > 10:
                raise Exception("Model could not be resolved.  There is likely an issue with the magnitude of units being analyzed.  Try aggregating inputs and changing units to reduce the range of magnitude (e.g. fewer zeroes)")
            print("\n\nThe model precision requirements could not be met.  This happens because there are too many zeroes for the range of input units (e.g. MJ) versus million tons. Adjusting tolerance and trying again")
            self._set_tolerance()
            return self.optimize(year)
        
        return self.status
    
    def save_results(self):
        # Print out feedstock supply
        # print out fuel supply
        # print out dual values
        # Print into format similar to ICS Calculator tables:
        # |Years                               |
        # |Fuel Name  Quantity                |
            
        # Output:  year.csv
        
        # Need other function to combine the output data into an ICS input file
        
        # Outputs:
            # E85 (mm gal)
            # Cellulosic Ethanol (mm gal)
            # Renewable Gasoline (mmg gal)
            # Hydrogen (mm kg)
            # Electricity for LDVs (1000 MWh)
            # Biodiesel (mm gal)
            # Renewable Diesel (mm gal)
            # Natural Gas Demand (mm DGE)
            # H2 for HDVs (mm kg)
            # Electricity for HDVs (1000 MWh)
            # Total Propane 
            # Alternative Jet Fuel
            
            
        
        raise Exception("This model functionality has not been built yet")
    def _calculate_incremental_limits(self, threshold = 1e9):
        #Zeroing Out Threshold: 1e9 MJ, or about 10 million GGE per year
        
        # Need to grab any banked credits as well!
        resolved_supply = self.calculate_fuel_supply()
        limits = {}
        for fuel, value in resolved_supply.items():
            minimum = (1 - self._default_production_limit) * value
            maximum = (1+self._default_production_limit) * value
            
            if minimum < threshold:
                minimum = 0
                
            limits[fuel] = (minimum, maximum)
        
        return limits
        
        
    def increment_time(self):
        
        self._prior_solution = self._calculate_incremental_limits()
        self.optimize(self._year+1, True)
    
    def _add_feedstocks(self):
        """
        This method adds the feedstock variables to the optimization program and ensures that the total
        feedstock supply constraint holds regardless of the fuel production pathway used.

        Raises
        ------
        Exception
            DESCRIPTION.

        Yields
        ------
        None.

        """
        if not self._year:
            raise Exception("A year has not been defined. Please use the 'set_year(x)' method to define the year. The model cannot setup variables.")
        self.solver.Clear()

        # Generate Feedstock Variables:   Fuel_Feedtock_Price
        # sum(Fuel_Feedstock_Price) <= Feedstock_limit
        
        self.variables["feedstock"] = {}
        self.variables["credits"] = {}
        pathways = self.data.get_production(self._year)
        
        #Add Credit Supply Variables
        for credit in self.data.credits.values():
            try:
                supply = credit.supply[self._year]
            except KeyError:
                supply = None
                
            if supply:
                self.variables["credits"][credit.name] = self.solver.NumVar(0, supply, "CreditVariable: {}".format(credit.name))
        
        self.constraints["feedstock"] = {}
        for feedstock in self.data.feedstocks.values():
            
            # Set feedstock supply constraint
            fs_c = self.constraints["feedstock"][feedstock.name] = self.solver.Constraint(0, feedstock.Ub(), "FeedstockConstraint: {}".format(feedstock.name))
            
            # Iterate over production pathways for use
            fuel_list = []
            for fstck, fuellist in self.data.productionpathways.items():
                if fstck == feedstock.name:
                    # [fuel for fuel in fuellist]
                    fuel_list = list(fuellist)
    
            # Note: list is [[list] ]
            for fuel in fuel_list:         
                pathway = pathways.get(feedstock.name, fuel)
              
                # Fuel (MJ) = Feedstock (ton) * yield (MJ/ton)
                # Cost ($/MJ) = Conversion Cost ($/ton) / yield (MJ/ton)

                if fuel not in self.variables["feedstock"]:
                    self.variables["feedstock"][fuel] = {}
                
                if feedstock.name not in self.variables["feedstock"][fuel]:
                    self.variables["feedstock"][fuel][feedstock.name] = []
                        
                for price, supply in feedstock:
                    name = "{}_{}_{}".format(fuel, feedstock.name, price)
                    fs = self.solver.NumVar(0, supply, name)
                    
                    # Add the variable to the model dictionary
                    self.variables["feedstock"][fuel][feedstock.name].append(fs)
                    
                    # Cost ($/ton) = Conversion Cost ($/ton) + Feedstock Cost ($/ton) - Subsidy ($/MJ) * yield (MJ/ton)
                    cost = pathway.conversioncost + price - pathway.subsidy*pathway.yields
                    self.objective.SetCoefficient(fs, cost)
                    fs_c.SetCoefficient(fs, 1)
                    
    def _set_demand_constraint(self):
        #Setup Demand Pool Constraints.  Ensures that the fuel energy supply is >= the demand in a given fuel pool
        
        self.constraints["demand"] = {}
        
        for pool_name, demand in self.data.demand.items():
            self.constraints["demand"][pool_name] = self.solver.Constraint(demand[self._year], float('inf'), "FuelDemandRequirement: {}".format(pool_name))
    
    def _set_supply_constraint(self):
        self.constraints["supply"] = {}
        for fuel in self.data.fuels.values():
            try:
                min_value, attribution = fuel.supply[self._year]
            except KeyError:
                min_value = 0
                attribution = None
            
            
            # Need to do something w. the Supply Constraint
            try:
                max_value, pct_change = fuel.limits[self._year]
                if not attribution:
                    attribution = "ProductionLimit"
            except KeyError:
                max_value = float('inf')
                
            if min_value == 0 and max_value == float('inf') and fuel.name not in self._prior_solution:
                continue
            
            try:
                prior_min, prior_max = self._prior_solution[fuel.name]

                minimum = max(min_value, prior_min)
                maximum = min(max_value, prior_max)
            except KeyError:
                minimum = min_value
                maximum = max_value
            
            if minimum > maximum:
                raise Exception("The model will be unable to converge, because {} has a minimum fuel requirement that exceeds that maximum fuel of that type allowed".format(fuel.name))
            # Also need logic for historic values
            self.constraints["supply"][fuel.name] = self.solver.Constraint(minimum, maximum, "FuelSupplyConstraint({}): {}".format(attribution, fuel.name))
            
        
            
            
    
    def _set_blending_constraints(self):
        

        # Minimum Blend Level
        # Percent_min <= Component/Pool
        # Percent_min*Pool - Component <= 0

        # Maximum Blend Level
        # Component/Pool <= Percent_max
        # Component - Percent_max*Pool <=0
        blend_list = self.data.blend_list(self._year)
        
        self.constraints["blend"] = {}
        for req in blend_list:
            self.constraints["blend"][req.name] = (
                self.solver.Constraint(float("-inf"), 0, "BlendMinimum: {}".format(req.name)),
                self.solver.Constraint(float("-inf"), 0, "BlendMaximum: {}".format(req.name))
                )
        
            
    def _set_ci_constraint(self):
        """
        Adds the LCFS Constraint.  The benchmark determines the "allowed" emisisons, and the actual fuel CI determines actual emissions.
        In any given year, the actual emissions must be less than the allowed emissions.

        Returns
        -------
        None.

        """
        self.constraints["ci"] = {}
        self.deficit_fuels.clear()
        
        # The overall constraint is implemtend such that:
        # Sum(Benchmark * Energy) - sum(ActualCI * Energy) + Additional credits >= 0
        
        pathways = self.data.get_production(self._year)
        

        for credit in self.data.credits.values():
            c_name = credit.name
            
            if self._year in credit.limits:
                c_min, c_max = (float(x) for x in credit.limits[self._year])

            else:
                c_min, c_max = (0, float('inf'))
                
            # Dual value of the constraint is the $/ton cost of achieving the constraint, or marginal credit price
            c_cons = self.constraints["ci"][c_name] = self.solver.Constraint(c_min, c_max, "CI Constraint_{}".format(c_name))
            
            # Add additional credits (tons CO2e)
            if c_name in self.variables["credits"]:
                c_cons.SetCoefficient(self.variables["credits"][c_name], 1)
        
        for benchmark in self.data.lcfs.values():
            ci = benchmark[self._year]
            
            if not ci:
                continue
            
            
            pathway_list = pathways.get_benchmark(benchmark.name, self._year)
            print("Generating a valid pathway list for calculating the average CI of the '{}' benchmark".format(benchmark.name))
            
            
            for pw in pathway_list:
                for fstck_var in self.variables["feedstock"][pw.fuel.name][pw.feedstock.name]:
                    
                    # Actual Emissions = Feedstock (tons) * Yield (MJ/ton) * Pathway CI (gCO2e/MJ)
                    # Allowed Emissions = Feedstock (tons) * Yield (MJ/ton) * Benchmark CI (gCO2e/MJ) 
                    # Credits = (Allowed Emissions - Actual Emissions) * 1e-6 gCO2e/tonCO2e
                    
                    c_name = pw.credit.name
                    coef = (ci - pw.ci) * pw.yields*1e-6
                    
                   # print("adding CI constraint for {}. Coef: {}.  Benchmark: {}, PW CI: {}".format(fstck_var.name(), 
                   #                                                                                 coef, ci, pw.ci))
                    if coef < 0:
                        self.deficit_fuels.append(fstck_var)
                    
                    constraint = self.constraints["ci"][c_name]
                    constraint.SetCoefficient(fstck_var, coef)

        
    def _add_constraints(self):
        if not self._year:
            raise Exception("A year has not been defined.  The model cannot setup variables.")
        
        
        # Define the Constraints
        self._set_demand_constraint()
        self._set_ci_constraint()
        self._set_blending_constraints()
        self._set_supply_constraint()

        # Load the pathways and fuel pools that have blending constituents
        pathways = self.data.get_production(self._year)
        blend_list = self.data.blend_list(self._year)
        blend_pools = {x.fuelpool.name for x in blend_list}
        
            
        #Ensure feedstock conversion is serving demand pool demand
        for fuel, feedstock_list in self.variables["feedstock"].items():
            fp = self.data.fuels[fuel].fuelpool
            fuelpool_c = self.constraints["demand"][fp]
            
            try:
                fuel_constraint = self.constraints["supply"][fuel]
            except KeyError:
                fuel_constraint = None
            
            
            # Move nested blocks to their own functions
            for fstck, prices in feedstock_list.items():
                pathway = pathways.get(fstck, fuel)
                yields = pathway.yields 
                
                for price in prices:
                    fuelpool_c.SetCoefficient(price, yields)
                    
                    if fuel_constraint:
                        fuel_constraint.SetCoefficient(price, yields)
                    
                    # Add coefficients to the blend constraints
                    if fp in blend_pools:
                        for requirement in [x for x in blend_list if x.fuelpool.name == fp]:
                            min_c, max_c = self.constraints["blend"][requirement.name]
                            
                            
                            # Minimum Blend Level
                            # Percent_min <= Component/Pool
                            # Percent_min*Pool - Component <= 0
                            min_coef = requirement.minimum
                            
                            # Maximum Blend Level
                            # Component/Pool <= Percent_max
                            # Component - Percent_max*Pool <=0
                            max_coef = -1*requirement.maximum
        
                            if requirement.fuel.name == fuel:
                                min_coef = min_coef - 1
                                max_coef = 1 + max_coef
                            
                            #print("Setting Coefficients Min {}: {} ".format(price.name(), yields*min_coef))
                            #print("Setting Coefficients Max {}: {} ".format(price.name(), yields*max_coef))
                            #print("Fuel Yield {}: {} ".format(price.name(), yields))
                            min_c.SetCoefficient(price, yields*min_coef)
                            
                            # Will need to add a coefficient for a variable to overcome the blendwall constraint
                            max_c.SetCoefficient(price, yields*max_coef)

        
    def set_year(self, year):
        self._year = year
        


    