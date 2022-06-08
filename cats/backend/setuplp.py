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
# fuel pathway at a specific feedstock price
# Minimize total cost of fuel supply, subject to constraints

# Constraints:
        # Feedstock does not exceed feedstock availability
        # Fuel Pool CI does not exceed LCFS Constraint
        # Credit types generated do not exceed credit amount constraint
        # Fuel pool supply >= Fuel Demand
        # Blending constraints (e.g. E10) and co-product constraints (e.g. AJF as pct of RD)


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
        self.results = None

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

    def get_year(self):
        if self.status == None:
            return None

        return self._year

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
            if limit:
                self._default_production_limit = float(limit)
        except ValueError:
                self._default_production_limit = 0

    def save_as_mps(self, filename=""):
        results = self.solver.ExportModelAsMpsFormat(False, False)
        with open(filename, 'w') as f:
            f.write(results)


    def show_solutions(self, to_text=None, save_mps=False):
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
        if save_mps:
            self.save_as_mps("mps_"+to_text)

        return output

    def calculate_fuel_supply(self, disaggregate_feedstock=False):
        if self.status != 0:
            raise Exception("Model has not converged on a solution.")

        pathways = self.data.get_production(self._year)
        supply = {}
        for fuel, feedstocks in self.variables["feedstock"].items():
            quantity = 0
            for feedstock, prices in feedstocks.items():
                if feedstock == "slack":
                    continue

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

        self.data.verify_data(year)

        # Adds the variables to the model
        self._add_feedstocks()

        # Adds the model constraints
        print("Adding constraints...")



        self._add_constraints()

        # Solves the linear programming problem
        self.status = self.solver.Solve()
        if self.status == self.solver.ABNORMAL:
            if self._tolerance > 10:
                raise Exception("Model could not be resolved.  There is likely an issue with the magnitude of units being analyzed.  Try aggregating inputs and changing units to reduce the range of magnitude (e.g. fewer zeroes)")
            print("\n\nThe model precision requirements could not be met.  This happens because there are too many zeroes for the range of input units (e.g. MJ versus million tons). Adjusting tolerance and trying again")
            self._set_tolerance()

            return self.optimize(year, increment_time)

        print("Model Solved...")
        return self.status

    def save_results(self):
        if not self.results:
            self.results = {}
            self.results["Category"] = {}
            self.results["Units"] = {}

        pathways = self.data.get_production(self._year)
        category = self.results["Category"]
        units = self.results["Units"]
        emissions = {}
        results_dict = self.results[self._year] = {}
        constraint_results = self.solver.ComputeConstraintActivities()


        for fuel, feedstock_dict in self.variables['feedstock'].items():

            for feedstock, prices in feedstock_dict.items():

                # Setting defaults that are overwritten if specified for results
                aggregator = fuel
                runits = "MJ"
                multiplier = 1

                quantity = 0
                carbon = 0
                energy = 0

                if feedstock == "slack":
                    if prices.SolutionValue() > 0:
                        print("\n\n\t Fuel Production Volumes are Constrained.  The model is adding a slack variable to relax this constraint.  Price estimates are unreliable.")
                        category[aggregator] = "RelaxedConstraint"
                        units[aggregator] = prices.name()
                        results_dict[aggregator] = prices.SolutionValue()
                    continue
                    # Need to add some logic here for slack variables

                pw = pathways.get(feedstock, fuel)

                if pw.results["raggregator"]:
                    aggregator = pw.results["raggregator"]
                    runits = pw.results["runits"]
                    multiplier = pw.results["rmultiplier"]


                for price in prices:
                    energy = energy + price.SolutionValue()*pw.yields
                    quantity = energy*multiplier
                    carbon = carbon + pw.ci*price.SolutionValue()*pw.yields


                if aggregator not in results_dict:
                    results_dict[aggregator] = 0


                if aggregator not in emissions:
                    emissions[aggregator] = {}
                    emissions[aggregator]["carbon"] = 0
                    emissions[aggregator]["energy"] = 0

                category[aggregator] = "Fuel"
                units[aggregator] = runits
                results_dict[aggregator] += quantity


                emissions[aggregator]["carbon"] += carbon
                emissions[aggregator]["energy"] += energy

        for fuel, constraint in self.constraints["demand"].items():
            results_dict[fuel + " Cost"] = round(float(constraint.DualValue())*115.83,2)
            category[fuel + " Cost"] = "Marginal Cost"
            units[fuel + " Cost"] = "$/GGE"

        for c_name, constraint in self.constraints["ci"].items():
            if not isinstance(c_name, str):
                raise Exception("There was en error saving results.  Please check your results output paramaters in the scenario_input file.")

            if c_name == "total":
                results_dict[c_name] = int(constraint.DualValue())
                category[c_name] = "Credit Price"
                units[c_name] = "$/ton"
            else:
                results_dict[c_name] = int(constraint.DualValue())
                category[c_name] = "Credit Differential"
                units[c_name] = "$/ton"

            results_dict[c_name + " credit quantity"] = int(constraint_results[constraint.index()])
            category[c_name + " credit quantity"] = "Credits"
            units[c_name + " credit quantity"] = "tons"

        for key, ci_dict in emissions.items():
            if not isinstance(key, str):
                raise Exception("There was en error saving results.  Please check your results output paramaters in the scenario_input file.")
            name = key + " Avg CI"

            try:
                results_dict[name] = round(ci_dict["carbon"]/ci_dict["energy"],2)
                category[name] = "Carbon Intensity"
                units[name] = "gCO2e/MJ"
            except ZeroDivisionError:
                continue


        return self.results


    def _calculate_incremental_limits(self, threshold = 1e9):
        #Zeroing Out Threshold: 1e9 MJ, or about 10 million GGE per year

        # Does not currently bring forward banked credits from prior years
        resolved_supply = self.calculate_fuel_supply()
        limits = {}
        for fuel, value in resolved_supply.items():
            minimum = (1 - self._default_production_limit) * value
            maximum = (1 + self._default_production_limit) * value

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
                if supply > 0:
                    self.variables["credits"][credit.name] = self.solver.NumVar(0, supply, "CreditVariable: {}".format(credit.name))
                else:
                    self.variables["credits"][credit.name] = self.solver.NumVar(-supply, float('inf'), "CreditVariable: {}".format(credit.name))

        self.constraints["feedstock"] = {}
        for feedstock in self.data.feedstocks.values():

            # Set feedstock supply constraint

            # Get set of fuels that can use the feedstock
            try:
                fuels = self.data.productionpathways[feedstock.name]
            except KeyError:
                fuels = []

            for fuel in fuels:
                pathway = pathways.get(feedstock.name, fuel)

                # Fuel (MJ) = Feedstock (ton) * yield (MJ/ton)
                # Cost ($/MJ) = Conversion Cost ($/ton) / yield (MJ/ton)

                if fuel not in self.variables["feedstock"]:
                    self.variables["feedstock"][fuel] = {}
                    slack = self.solver.NumVar(0, float('inf'), "{}_slack".format(feedstock.name))
                    self.variables["feedstock"][fuel]["slack"] = slack
                    self.objective.SetCoefficient(slack, 100000)


                if feedstock.name not in self.variables["feedstock"][fuel]:
                    self.variables["feedstock"][fuel][feedstock.name] = []



                for price, supply in feedstock:
                    constraint_name = "{}_{}".format(feedstock.name, price)

                    try:
                        fs_c = self.constraints["feedstock"][constraint_name]
                    except KeyError:
                        fs_c = self.constraints["feedstock"]["{}_{}".format(feedstock.name, price)] = \
                            self.solver.Constraint(0, supply, "FeedstockConstraint: {}_{}".format(feedstock.name, price))

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
            if demand.exceed:
                maximum = float('inf')
            else:
                maximum = demand[self._year]

            self.constraints["demand"][pool_name] = self.solver.Constraint(demand[self._year], maximum, "FuelDemandRequirement: {}".format(pool_name))

    def _set_supply_constraint(self):
        self.constraints["supply"] = {}
        for fuel in self.data.fuels.values():
            pct_change = self._default_production_limit
            minimum = 0
            maximum = 0

            try:
                min_value, attribution = fuel.supply[self._year]
            except KeyError:
                min_value = 0
                attribution = None

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


                # If a pct_change value is provided, this will override
                # the default value in the config file
                if pct_change != 0:
                    old_value = prior_min/(1 - self._default_production_limit)
                    prior_min = (1-pct_change)*old_value
                    #Maximum value is at least a 200 MM GGE/yr facility
                    prior_max = max((1+pct_change)*old_value, 50*1e6*115.83)

                minimum = max(min_value, prior_min)
                maximum = min(max_value, prior_max)
            except KeyError:
                minimum = min_value
                maximum = max_value

            if minimum > maximum:
                raise Exception("The model will be unable to converge, because {} has a minimum fuel requirement that exceeds that maximum fuel of that type allowed".format(fuel.name))

            if minimum == 0 and maximum == 0:
                print("Avoiding minimum constraint for {}".format(fuel.name))
            else:
                print("Setting Constraint for {}: {},{} ".format(fuel.name, minimum, maximum))
                self.constraints["supply"][fuel.name] = self.solver.Constraint(minimum, maximum, "FuelSupplyGrowthConstraint({}): {}".format(attribution, fuel.name))





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

        lcfs = self.constraints["ci"]["total"] = \
            self.solver.Constraint(0, float('inf'), "CI Constraint_{}".format("total"))

        for credit in self.data.credits.values():
            c_name = credit.name

            if self._year in credit.limits:
                c_min, c_max = (float(x) for x in credit.limits[self._year])

            else:
                c_min, c_max = (float('-inf'), float('inf'))

            # Dual value of the constraint is the $/ton cost of achieving the constraint, or marginal credit price
            c_cons = self.constraints["ci"][c_name] = \
                self.solver.Constraint(c_min, c_max, "CI Constraint_{}".format(c_name))

            # Add additional credits (tons CO2e)
            if c_name in self.variables["credits"]:
                var = self.variables["credits"][c_name]
                if var.Lb() > 0:
                    coef = -1
                else:
                    coef = 1
                c_cons.SetCoefficient(self.variables["credits"][c_name], coef)
                lcfs.SetCoefficient(self.variables["credits"][c_name], coef)

        for benchmark in self.data.lcfs.values():
            ci = benchmark[self._year]

            if ci is None:
                continue


            pathway_list = pathways.get_benchmark(benchmark.name, self._year)
            print("Generating a valid pathway list for calculating the average CI of the '{}' benchmark".format(benchmark.name))


            for pw in pathway_list:
                for fstck_var in self.variables["feedstock"][pw.fuel.name][pw.feedstock.name]:

                    # Actual Emissions = Feedstock (tons) * Yield (MJ/ton) * Pathway CI (gCO2e/MJ)
                    # Allowed Emissions = Feedstock (tons) * Yield (MJ/ton) * Benchmark CI (gCO2e/MJ)
                    # Credits = (Allowed Emissions - Actual Emissions) * 1e-6 gCO2e/tonCO2e

                    c_name = pw.credit.name
                    coef = (ci - pw.ci/pw.eer) * pw.yields*1e-6*pw.eer

                    #print("adding CI constraint for {}. Coef: {}.  Benchmark: {}, PW CI: {}".format(fstck_var.name(),
                    #                                                                                coef, ci, pw.ci))
                    if coef < 0:
                        self.deficit_fuels.append(fstck_var)

                    constraint = self.constraints["ci"][c_name]
                    constraint.SetCoefficient(fstck_var, coef)
                    lcfs.SetCoefficient(fstck_var, coef)


    def _set_coproduct_constraints(self):
        # Get basefuels
        # See how many coproducts each basefuel has
        # New constraint for each coproduct

        self.constraints["coproduct"] = {}
        coproducts = self.data.get_coproducts()
        for basefuel, fuel_list in coproducts.items():
            self.constraints["coproduct"][basefuel] = {}
            for fuel in fuel_list:
                self.constraints["coproduct"][basefuel][fuel] = \
                    self.solver.Constraint(0, 0, \
                                           "Coproduct Constraint_{}_{}".format(basefuel,fuel))


    def _add_constraints(self):
        if not self._year:
            raise Exception("A year has not been defined.  The model cannot setup variables.")

        # Define the Constraints
        self._set_demand_constraint()
        self._set_ci_constraint()
        self._set_blending_constraints()
        self._set_supply_constraint()
        self._set_coproduct_constraints()

        coproducts = self.data.get_coproducts()
        cp_fuels = coproducts.get_all_fuels()

        constraint_args = {}

        # Load the production pathway information for the model year
        pathways = self.data.get_production(self._year)

        #Ensure feedstock conversion is serving demand pool demand
        for fuel, feedstock_list in self.variables["feedstock"].items():
            fuelpool = self.data.fuels[fuel].fuelpool
            constraint_args["fuelpool_c"] = self.constraints["demand"][fuelpool]

            if fuel in cp_fuels:
                constraint_args["coproducts"] = True
            else:
                constraint_args["coproducts"] = False

            try:
                constraint_args["fuel_constraint"] = self.constraints["supply"][fuel]

            except KeyError:
                constraint_args["fuel_constraint"] = None

            for fstck, prices in feedstock_list.items():
                if fstck == "slack":
                    continue

                pathway = pathways.get(fstck, fuel)
                # adds coefficients to each constraint affiliated
                # with the feedstock price and production pathway
                self._add_price_coefficients(fuelpool, pathway, prices, constraint_args)

    def _add_price_coefficients(self, fuelpool, pathway, prices, constraints):
        fuelpool_c = constraints["fuelpool_c"]
        fuel_constraint = constraints["fuel_constraint"]
        blend_list = self.data.blend_list(self._year)
        blend_pools = {x.fuelpool.name for x in blend_list}

        if fuel_constraint:
            slack = self.variables["feedstock"][pathway.fuel.name]["slack"]
            fuel_constraint.SetCoefficient(slack, -pathway.yields)

        # Setting up relevant variables if there are coproducts
        if constraints["coproducts"]:
            coproducts = self.data.get_coproducts()
            basefuels = coproducts.which_basefuel(pathway.fuel.name)


        for fs_price_var in prices:
            fuelpool_c.SetCoefficient(fs_price_var, pathway.yields)

            if fuel_constraint:
                fuel_constraint.SetCoefficient(fs_price_var, pathway.yields)


            # Add coefficients to any blend pool constraints that exist
            if fuelpool in blend_pools:
                self._add_blend_coefficients(fs_price_var, blend_list, fuelpool, pathway)

            if constraints["coproducts"]:
                # set coefficient for Basefuel vs Non-base for coproducts
                # Constraint:  [Base Fuel]*multiplier - [Fuel] = 0
                # Coeficient is: -1 if not-base, or the multiplier if base

                if not basefuels:
                    for fuel, constraint in self.constraints["coproduct"][pathway.fuel.name].items():
                        multiplier = coproducts.get_multiplier(fuel, pathway.fuel.name)
                        constraint.SetCoefficient(fs_price_var, pathway.yields*multiplier)
                else:
                    for fuel in basefuels:
                        constraint = self.constraints["coproduct"][fuel][pathway.fuel.name]
                        constraint.SetCoefficient(fs_price_var, -pathway.yields)




    def _add_blend_coefficients(self, fs_price_var, blend_list, fuelpool, pathway):
        """


        Parameters
        ----------
        fs_price_var : Linear Programming Variable
            This is the linear programming variable object type for feedstock conversion at a specified feedstock price
        blend_list : list
            The list of blend requirements for a given year that may impact a specifed fuel.
        fuelpool : string
            The fuelpool that the production pathway provides energy for
        pathway : fuel pathway object
            the production pathway to convert from feedstock to fuel

        Returns
        -------
        None.

        """
        for blend in [x for x in blend_list if x.fuelpool.name == fuelpool]:
            min_c, max_c = self.constraints["blend"][blend.name]


            # Minimum Blend Level
            # Percent_min <= Component/Pool
            # Percent_min*Pool - Component <= 0
            min_coef = blend.minimum

            # Maximum Blend Level
            # Component/Pool <= Percent_max
            # Component - Percent_max*Pool <=0
            max_coef = -1*blend.maximum

            if blend.requirement == pathway.blend:
                min_coef = min_coef - 1
                max_coef = 1 + max_coef

            min_c.SetCoefficient(fs_price_var, pathway.yields*min_coef)

            # TODO: Will need to add a coefficient for a variable to overcome the blendwall constraint
            # if option is checked to make problem feasible
            max_c.SetCoefficient(fs_price_var, pathway.yields*max_coef)

    def set_year(self, year):
        self._year = year
