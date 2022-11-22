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

from cats.util.funcs import closest_value
from cats.util.funcs import validate_numeric
from cats.util.funcs import validate_bounds
import pandas as pd


class Fuel():
    fuels = {}
    def __init__(self, name, fuelpool):
        self.name = name
        self.limits = {}
        self.benchmark = None
        # Can force instatiation of FuelPool instead.  Not sure I want to do that?
        if fuelpool not in FuelPool.pools:
            raise TypeError("Specified Fuel Pool '{}' has not been defined try {}".format(fuelpool,
                                                                              list(FuelPool.pools)))
        self.fuelpool = fuelpool
        self.supply = {}
        self.years = self._years()

    @classmethod
    def add_fuel(cls, name, fuelpool):
        try:
            return cls.fuels[name]
        except KeyError:
            new_fuel = cls(name, fuelpool)
            cls.fuels[name] = new_fuel
            return new_fuel

    @classmethod
    def reset(cls):
        cls.fuels = {}

    @classmethod
    def get(cls, name):
        try:
            return cls.fuels[name]
        except KeyError:
            return None

    def __repr__(self):
        return self.name

    def add_limit(self, year, max_amount, pct_change):
        self.limits[year] = (max_amount, pct_change)

    def add_supply(self, year, amount, attribution = None):
        self.supply[year] = (amount, attribution)

    def aggregate_supply(self, policy):
        total = 0
        for amount, pol in self.supply.values():
            if policy == pol:
                total = total + amount
        return total

    def __getitem__(self, year):
        try:
            limits = self.limits[year]
        except KeyError:
            limits = None

        try:
            supply = self.supply[year]

        except KeyError:
            supply = None

        return {"supply":supply, "limits":limits}

    def _years(self):
        return {"supply": list(self.supply.keys()), "limits": list(self.limits.keys())}


class FuelPool():
    pools = {}
    def __init__(self, name):
        self.name = name
        self.demand = {}
        self.exceed = False
        self.years = self.keys()

    def __repr__(self):
        return self.name

    @classmethod
    def add_pool(cls, name):
        try:
            return cls.pools[name]
        except KeyError:
            new_pool = cls(name)
            cls.pools[name] = new_pool
            return new_pool

    @classmethod
    def reset(cls):
        cls.pools.clear()

    @classmethod
    def get(cls, name):
        return cls.pools[name]

    def add_demand(self, year, amount, exceed=False):
        self.demand[year] = amount
        self.exceed = exceed

    def __getitem__(self, year):
        year = closest_value(year, self.demand.keys())
        return self.demand[year]

    def __iter__(self):
        return iter(self.demand.items())

    def keys(self):
        return self.demand.keys()

    def items(self):
        return self.demand.items()

    def values(self):
        return self.demand.values()


class Coproducts():
    coproducts = {}
    def __init__(self, fuel, basefuel, multiplier, exceed = False):
        self.fuel = Fuel.get(fuel)
        self.basefuel = Fuel.get(basefuel)
        self.multiplier = multiplier
        self.exceed = exceed

    @classmethod
    def __iter__(cls):
        return iter(cls.coproducts.items())

    @classmethod
    def keys(cls):
        return cls.coproducts.keys()

    @classmethod
    def items(cls):
        return cls.coproducts.items()

    @classmethod
    def add_coproduct(cls, fuel, basefuel, multiplier, exceed = False):
        try:
            return cls.coproducts[basefuel][fuel]
        except KeyError:
            coproduct = cls(fuel, basefuel, multiplier, exceed)

            if basefuel not in cls.coproducts:
                cls.coproducts[basefuel] = {}

            cls.coproducts[basefuel][fuel] = coproduct
            return coproduct

    @classmethod
    def get_base_fuels(cls):
        return cls.coproducts.keys()

    @classmethod
    def get_all_fuels(cls):
        fuel_list = []
        for k,v in cls.coproducts.items():
            fuel_list.append(k)
            fuel_list.extend(list(v.keys()))

        return fuel_list

    @classmethod
    def get_multiplier(cls, fuel, basefuel):
        try:
            return cls.coproducts[basefuel][fuel].multiplier

        except KeyError:
            return None

    @classmethod
    def get_exceed(cls, fuel, basefuel):
        try:
            return cls.coproducts[basefuel][fuel].exceed

        except KeyError:
            return None

    @classmethod
    def which_basefuel(cls, fuel):
        fuel_list = []
        for k, v in cls.coproducts.items():
            if fuel in v.keys():
                fuel_list.append(k)

        return fuel_list

    @classmethod
    def reset(cls):
        cls.coproducts = {}

    def __repr__(self):
        return "{} from {}".format(self.fuel, self.basefuel)



class ProductionPathway():
    feedstock = {}
    fuels = {}
    period = None
    def __init__(self,
                 year,
                 fuel,
                 fuelpool,
                 feedstock,
                 cost,
                 carbon,
                 yields,
                 credit_type = None,
                 blend = None,
                 benchmark = None,
                 eer = 1,
                 raggregator = None,
                 rmultiplier = None,
                 runits = None):

        if feedstock not in Feedstock.feedstocks:
            raise KeyError('''{} has not been defined as a feedstock.
                           Please ensure that this feedstock is defined in the model inputs sheet.'''.format(feedstock))


        self.year = year
        self.subsidy = 0
        self.yields = yields
        self.conversioncost = cost
        self.ci = carbon
        self.credit = Credit.add_credit(credit_type)
        self.fuel = Fuel.add_fuel(fuel, fuelpool)
        self.feedstock = Feedstock.add_feedstock(feedstock)
        self.supplycurve = self._generate_costs(cost, yields)
        self.name = self.fuel.name +" ({})".format(self.feedstock.name)
        self.benchmark = benchmark
        self.blend = blend
        self.eer = eer
        self.results = {"raggregator": raggregator, "rmultiplier": rmultiplier, "runits": runits}

    @classmethod
    def reset(cls):
        cls.feedstock.clear()
        cls.fuels.clear()

    @classmethod
    def set_year(cls, year):
        cls.period = year

    def __repr__(self):
        return str(self.year) + \
            ":" + self.fuel.name+" - "+self.feedstock.name+" ({})".format(self.ci)

    def add_subsidy(self, amount):
        self.subsidy = self.subsidy + amount

    def _generate_costs(self, conversioncost, yields):
        fs = self.feedstock
        supply_curve = {}
        for price, supply in fs:
            try:
                cost = int((float(conversioncost) + float(price))/yields)
                supply_curve[cost] = yields*supply
            except ZeroDivisionError as error:
                raise ZeroDivisionError("Error adding {} to at conversion cost {} \
                                 and price {} to \
                                 supply due to yield {}".format(fs.name, \
                                     conversioncost, price, yields)) from error
        return supply_curve

    def update(self, conversioncost, yields, carbon, credit_type):
        self.conversioncost = conversioncost
        self.yields = yields
        self.ci = carbon
        self.credit = Credit.add_credit(credit_type)
        self.supplycurve = self._generate_costs(conversioncost, yields)

    @classmethod
    def get(cls, feedstock, fuel):
        pathway = cls.feedstock[feedstock][fuel]
        if cls.period is None:
            year = max(list(pathway.keys()))
        else:
            year = closest_value(cls.period,list(pathway.keys()))

        return cls.feedstock[feedstock][fuel][year]

    @classmethod
    def get_benchmark(cls, benchmark, year):
        valid_paths = []
        for item in cls.feedstock.values():
            for value in item.values():
                period = closest_value(year, value.keys())
                if value[period].benchmark == benchmark:
                    valid_paths.append(value[period])

        return valid_paths

    @classmethod
    def get_blend_requirement(cls, requirement, year):
        valid_paths = []
        for item in cls.feedstock.values():
            for value in item.values():
                period = closest_value(year, value.keys())
                if value[period].blend == requirement:
                    valid_paths.append(value[period])

        return valid_paths


    @classmethod
    def get_fuel_pool(cls, fuelpool, year):
        valid_paths = []
        for item in cls.feedstock.values():
            for value in item.values():
                period = closest_value(year, value.keys())
                if value[period].fuel.fuelpool == fuelpool:
                    valid_paths.append(value[period])

        return valid_paths


    @classmethod
    def add_pathway(cls,
                    year,
                    fuel,
                    fuelpool,
                    feedstock,
                    cost,
                    carbon,
                    yields,
                    credit_type = "Default",
                    blend = None,
                    benchmark=None,
                    eer = 1,
                    raggregator = None,
                    rmultiplier = None,
                    runits = None):
        try:
            return cls.fuels[fuel][feedstock][year]
        except KeyError:
            pathway = cls(year, fuel, fuelpool, feedstock, cost,
                          carbon, yields,
                          credit_type = credit_type,
                          blend = blend,
                          benchmark=benchmark,
                          eer = eer,
                          raggregator = raggregator,
                          rmultiplier = rmultiplier,
                          runits = runits)


            if fuel not in cls.fuels:
                cls.fuels[fuel] = {}

            if feedstock not in cls.fuels[fuel]:
                cls.fuels[fuel][feedstock] = {}

            if feedstock not in cls.feedstock:
                cls.feedstock[feedstock] = {}

            if fuel not in cls.feedstock[feedstock]:
                cls.feedstock[feedstock][fuel] = {}



            cls.fuels[fuel][feedstock][year] = pathway


            cls.feedstock[feedstock][fuel][year] = pathway
            return pathway

class Credit():
    allcredits = {}
    def __init__(self, name):
        self.name = name
        self.limits = {}
        self.supply = {}

    def __repr__(self):
        return self.name

    @classmethod
    def reset(cls):
        cls.allcredits.clear()

    @classmethod
    def add_credit(cls, name):
        try:
            return cls.allcredits[name]
        except KeyError:
            c = cls(name)
            cls.allcredits[name] = c
            return c

    @classmethod
    def get(cls, name):
        try:
            return cls.allcredits[name]
        except KeyError as error:
            raise KeyError("{} is not a valid credit type.".format(name)) from error

    def add_limit(self, year, minimum, maximum):
        self.limits[year] = (minimum, maximum)

    def __getitem__(self, year):
        return {"supply": self.supply[year], "limits": self.limits[year]}

    def add_supply(self,year, amount):
        self.supply[year] = amount

    @classmethod
    def list_credits(cls):
        return cls.allcredits.keys()

class Feedstock():
    feedstocks = {}

    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("The entered feedstock's name is invalid.")

        self.name = name
        self.supply = {}

    def __repr__(self):
        return self.name+str(self._upper())

    def __getitem__(self, price):
        return self.supply[price]

    def __iter__(self):
        return iter(self.supply.items())

    def keys(self):
        return self.supply.keys()

    def values(self):
        return self.supply.values()

    @classmethod
    def reset(cls):
        cls.feedstocks.clear()

    @classmethod
    def get(cls, name):
        return cls.feedstocks[name]
    @classmethod
    def add_feedstock(cls, name):
        try:
            return cls.feedstocks[name]
        except KeyError:
            new_fs = cls(name)
            cls.feedstocks[name] = new_fs
            return new_fs

    def add_supply(self, price, quantity):
        price = validate_numeric(price)
        quantity = validate_bounds(quantity)

        self.supply[price] = quantity

    def get_cumulative(self, price):
        price = validate_numeric(price)
        end_point = closest_value(price, self.supply.keys())
        cumulative = 0
        for key, value in self.supply.items():
            if key <= end_point:
                cumulative = cumulative + value

        return cumulative

    def marginal_cost(self, supply):
        """


        Parameters
        ----------
        supply : Integer
            Take an integer amount of supply for a given feedstock and
            generate the marginal cost for providing that level of supply.

        Raises
        ------
        KeyError
            Supply points have not been added for this specific feedstock
        ValueError
            The specified supply is greater than available supply of feedstock.

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        supply = validate_numeric(supply)
        cumulative = {p: self.get_cumulative(p) for p in self.supply.keys()}
        try:
            end_point = closest_value(supply, cumulative.values(),True)
        except KeyError as error:
            raise KeyError("""No cost data could be found.  Please add supply curve
                           data for '{}'""".format(self.name)) from error
        if end_point < supply:
            # Some errors here!
            raise ValueError("The supply curve is only established to {}.  This is less than the '{}' you entered.".format(end_point, supply))
        return [k for k, v in cumulative.items() if v == end_point][0]

    def _upper(self):
        """
        Returns the (marginal feedstock cost, cumulative feedstock supply)

        Returns
        -------
        Upper bound tuple: (marginal feedstock cost, cumulative feedstock supply)

        """
        try:
            cumulative = {p: self.get_cumulative(p) for p in self.supply.keys()}
            return (max(cumulative.keys()), max(cumulative.values()))
        except ValueError:
            return (None, None)

    def Ub(self):
        """


        Returns
        -------
        TYPE
            DESCRIPTION. The maximum supply of feedstock available

        """
        value = self._upper()[1]
        if value:
            return float(value)

        return 0


class BlendRequirement():
    requirements = {}
    def __init__(self, requirement, fuelpool, minimum, maximum, year):
        self.name = "{}_{} ({}, {})".format(requirement, fuelpool, minimum, maximum)
        self.requirement = requirement
        self.fuelpool = FuelPool.get(fuelpool)
        self.minimum = minimum
        self.maximum = maximum
        self.year = year

    @classmethod
    def reset(cls):
        cls.requirements.clear()

    @classmethod
    def add(cls, fuel, fuelpool, minimum, maximum, year):
        try:
            return cls.requirements[year][fuel][fuelpool]
        except KeyError:
            requirement = cls(fuel, fuelpool, minimum, maximum, year)


            if year not in cls.requirements:
                cls.requirements[year] = {}

            if fuel not in cls.requirements[year]:
                cls.requirements[year][fuel] = {}

            cls.requirements[year][fuel][fuelpool] = requirement

            return requirement

    def __repr__(self):
        return self.name

    @classmethod
    def get(cls, year, fuel, fuelpool):
        return cls.requirements[year][fuel][fuelpool]


class LCFS():
    benchmarks = {}
    def __init__(self, benchmark_name):
        self.standards = {}
        self.name = benchmark_name

    @classmethod
    def add_benchmark(cls, year, benchmark, standard):
        try:
            bm = cls.benchmarks[benchmark]
        except KeyError:
            bm = cls(benchmark)
            cls.benchmarks[benchmark] = bm

        bm.update(year, standard)

        return bm

    def __repr__(self):
        return self.name

    def __getitem__(self, year):
        return self.standards[closest_value(year, self.standards.keys())]


    def update(self, year, standard):
        if pd.isna(standard):
            standard = None
        self.standards[year] = standard

    @classmethod
    def reset(cls):
        cls.benchmarks.clear()

    @classmethod
    def get(cls, benchmark, year):
        try:
            return cls.benchmarks[benchmark][year]
        except KeyError as error:
            raise KeyError("Benchmark '{}' could not be found.".format(benchmark)) from error
