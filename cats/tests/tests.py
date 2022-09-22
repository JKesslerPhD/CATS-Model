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

import unittest

class DataMethods(unittest.TestCase):

    def test_fuel_pool(self):
        from cats.backend.data import FuelPool
        FuelPool.add_pool("Test")
        FuelPool.get("Test")

    def test_feedstock(self):
        from cats.backend.data import Feedstock
        Feedstock.add_feedstock("TestFeedstock")
        Feedstock.get("TestFeedstock")

    def test_fuel(self):
        from cats.backend.data import Fuel
        from cats.backend.data import FuelPool
        FuelPool.add_pool("FuelPool")
        Fuel.add_fuel("TestFuel","FuelPool")

    def test_production(self):
        from cats.backend.data import ProductionPathway
        from cats.backend.data import Feedstock
        from cats.backend.data import FuelPool
        from cats.backend.data import Fuel

        # Setting up fuel and feedstock to covnert
        FuelPool.add_pool("FuelPool")
        fs = Feedstock.add_feedstock("Feedstock")

        fs_cost = 10 # $/ton
        fs_supply = 100
        fs.add_supply(fs_cost, fs_supply)
        Fuel.add_fuel("TestFuel", "FuelPool")

        conversioncost = 100 # $100 per ton
        yields = 10 # MJ per ton
        ci = 1 #gCO2e/MJ
        year = 2019

        pathway = ProductionPathway.add_pathway(year, "TestFuel", "FuelPool", "Feedstock", conversioncost, ci, yields, "Default")

        total_cost = int((conversioncost + fs_cost)/yields)


        assert pathway.supplycurve[total_cost] == fs_supply*yields
    def test_temporal_production(self):
        from cats.backend.data import ProductionPathway
        from cats.backend.data import Feedstock
        from cats.backend.data import FuelPool
        from cats.backend.data import Fuel

        fuelpool = "FuelPool"
        feedstock = "Feedstock"
        fuel = "TestFuel"

        FuelPool.add_pool(fuelpool)
        Fuel.add_fuel(fuel, fuelpool)

        fs = Feedstock.add_feedstock(feedstock)
        fs_cost = 10 # $/ton
        fs_supply = 100 # tons
        fs.add_supply(fs_cost, fs_supply)


        year1 = 2020
        year2 = 2021
        yield1 = 1
        yield2 = 10
        ci = 1
        conversioncost = 100


        ProductionPathway.add_pathway(year1, fuel, fuelpool, feedstock, conversioncost, ci, yield1, "Default")
        ProductionPathway.add_pathway(year2, fuel, fuelpool, feedstock, conversioncost, ci, yield2, "Default")


        ProductionPathway.set_year(year1)
        assert ProductionPathway.get(feedstock, fuel).yields is yield1

        ProductionPathway.set_year(year2)
        assert ProductionPathway.get(feedstock, fuel).yields is yield2

        ProductionPathway.set_year(year2 + 10)
        assert ProductionPathway.get(feedstock, fuel).yields is yield2

    def test_model_run(self):
        import cats
        from cats.backend.scenarios import GetScenarios
        from cats.backend.data import Loader
        import os
        from cats.backend.setuplp import Model

        conf = os.path.abspath(os.path.join(os.path.dirname(cats.__file__),"..","config_example.ini"))
        # Get list of Scenarios
        slist = GetScenarios(conf)

        # Load data for one specific scenario

        d = Loader(slist["Test"])
        d.load()
        m = Model(d)

        m.optimize(2022)


    def test_co_products(self):
        from cats.backend.data import Fuel
        from cats.backend.data import Coproducts
        from cats.backend.data import FuelPool

        fuelpool = "FuelPool"
        fuel = "TestFuel"
        other_fuel = "Other Fuel"
        cp = "Coproduct1"
        cp2 = "Coproduct2"

        FuelPool.add_pool(fuelpool)
        Fuel.add_fuel(fuel, fuelpool)
        Fuel.add_fuel(cp, fuelpool)
        Fuel.add_fuel(cp2, fuelpool)
        Fuel.add_fuel(other_fuel, fuelpool)
        multiplier = 1.02

        Coproducts.add_coproduct(cp, fuel, multiplier)
        Coproducts.add_coproduct(cp, other_fuel, multiplier)
        Coproducts.add_coproduct(cp2, fuel, multiplier)

        assert multiplier == Coproducts.get_multiplier(cp, fuel)
        assert other_fuel in Coproducts.which_basefuel(cp)
        assert fuel in Coproducts.which_basefuel(cp)



    def _test_increment_model_run(self):
        from cats.backend.scenarios import GetScenarios
        from cats.backend.data import Loader
        from cats.backend.setuplp import Model
        import cats
        import os

        conf = os.path.abspath(os.path.join(os.path.dirname(cats.__file__),"..","config_example.ini"))
        # Get list of Scenarios
        slist = GetScenarios(conf)

        # Load data for one specific scenario

        d = Loader(slist["default"])
        d.load()
        m = Model(d)

        m.optimize(2020)
        m.increment_time()
        if slist.production_change:
            m.set_default_production(slist.production_change)


""" def test_incremental_constraints():
     for fuel, constraint in m.constraints["supply"].items():
         print("{} Range: {} - {}".format(fuel, constraint.Lb(), constraint.Ub()))
 """

if __name__ == '__main__':
    unittest.main(verbosity=2)



def testing(line, **kwargs):
    for arg in kwargs:
        print(line)
        print(arg)