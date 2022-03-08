
# The California Transportation Supply (CATS) Model
## About the Model
The CATS model was created as an exploratory tool, and is provided without any warranties.  The model is a substantial simplification of the overall California transportation and fuel market, and therefore results should be interpreted with caution.

CATS can be used to explore how different assumptions relating to the cost, supply, demand, and carbon intensities of various fuel may impact the transportation market, and how Low Carbon Fuel Standard credit prices may respond to changes in market conditions and program stringency.

## Getting Started

1. Download the <a href="#">code base</a>
2. Setup the Python environment
3. Configure the scenario inputs
4. Running the model
5. Save and analyze the results

### Setting up the Python environment
To setup the environment, download and install <a href="https://www.anaconda.com/">Anaconda</a>.  Once Anaconda is installed, open up the Anaconda command prompt, and create a new environment.

```
conda create --name CATS python=3.9
conda activate CATS
```

If you intend to edit the scripts, or write your own methods or procedures, the Spyder Development Environment is recommended.  This can be installed from the Anaconda command prompt.

```
conda activate CATS
conda install spyder
```
Once the Spyder development environment is installed, you will be able to open Spyder from your desktop, and create specific methods to interact with CATS data.


From the Anaconda command prompt, navigate to the directory that you extracted CATS into.  An example directory is below.

```
cd "c:/CATS Model/"
```

Before running the model, you must first install model dependencies.  The model makes use of the or-tools optimization framework from Google.  
```
pip install -r requirements.txt
```
### Configuring the scenario inputs

Data for each scenario must be input into the model using a `scenario_inputs.xlsx` workbook located in the scenario directory.

> **Important Information About Inputs:** For some of the scenario inputs, the model will use the closest date value provided, while for other inputs the value will be `None` unless specified.  The `FuelProduction` pathways do not need to be defined for each year, the closest value will be used in the model.  If yields or CI change, however, then a new production pathway should be provided for that year.  Each Energy Demand `FuelPool` will also use the value provided from the closest year. For instance, if a value for 2040 is provided, and no `FuelPool` is provided in 2020, then the energy demand in 2020 for that `FuelPool` will be equal to the 2040 energy demand value. `LCFS` benchmarks will use the closest year entered. All other worksheets will only use the values entered for a given year.  As such, things like blend requirements must be entered annually.

The fundamental structure and description of worksheets for inputting data and assumptions into the model is provided in the table below.  The classes used to represent different `datatypes` in the model are also indicated.  Ensure that a `scenario_inputs.xlsx` file has been generated and modified for each scenario that you want to run.  Each scenario should be located in its own directory (`/scenario/Default/scenario_inputs.xlsx`)

| Worksheet Name | Description |
| --------------- | ----------- |
| Energy Demand | The minimum amount (MJ) of energy that must be provided for a given `FuelPool` in a specified year. A value of `0` may be used in the 'Energy' column to represent possible production pathways to create a product that does not have an energy requirement, such as Direct Air Capture.|
| Defined Supply | This worksheet may be left blank. Anything added to this worksheet will create a lower bound fuel energy (MJ) requirement/constraint for the model in a given year.  The model will require a quantity of `Fuel` to be generated in a given year. 'Policy Attribution' is the name or effect is driving that the user would like to attribute the constraint. |
| Fuel Production | The `ProductionPathway` and costs ($/ton) needed to convert (MJ/ton) `Feedstock` (ton) to `Fuel` (MJ).  This sheet also specifies the `FuelPool` the fuel will satisfy demand for, the `LCFS` benchmark that the carbon intensity (gCO2e/MJ) will be evaluated against, and a type identifier for `Credit` generation using this pathway.  Exogenous subsidies ($/MJ) that can increase or decrease fuel costs may also be specified. |
| Production Limits | This worksheet allows for 'Fuel' limits to be imposed.  This will prevent fuel production from exceeding an allowed amount in a given year, or a limit to growth relative to the past year, whichever is less. `None` may be specified for the 'Maximum Volume' or 'Maximum YoY Percent Change'. |
| Additional Credits | This allows a specific `Credit` quantity to be added to (or subtracted from) the model in a given year without an underlying credit `ProductionPathway`.  Credits added in this way will effectively reduce (or increase) demand for credits under the `LCFS` constraint. |
| LCFS Benchmark | This worksheet is where the `LCFS` policy benchmarks are defined.  A 'Year', 'Benchmark' (e.g gasoline, diesel, alt. jet), and carbon intensity 'Standard' must be provided.  The model will use the closest standard to a given benchmark year that is defined for each model run. |
| Feedstock | This worksheet is where each `Feedstock` supply curve is defined. Feedstock costs should be provided in units consistent with the 'Fuel Production' worksheet inputs for yield and conversion costs Feedstock price points and supply (tons) will only be parameterized as whole integers. |
| Credit Type Limits | Similar to the 'Production Limits' worksheet, a constraint is added to the model to ensure that a minimum or maximum `Credit` quantity of a specific type is generated in a specific year `0` and `inf` my be specified. |
|Blend Requirements| Specify the minimum and maximum blend requirement for a given fuel as a percentage of the energy content for a fuel pool.  For instance, a 10% ethanol blend by volume is a 7.04% blend by energy content for the gasoline `FuelPool`.

### Running the Model
The `config.ini` file should be modified to ensure that the model will run the specific scenarios you are interested in running.  Ensure that you have created a results folder in the same location that you have extracted the model to.

Once your scenarios and configuration files are configured, the model can be run from the command prompt.  The example provided below assumes you have extracted the model to the `c:\CATS model` folder, and installed an Anaconda instance as described previously.

```
cd "c:\CATS model"
conda activate CATS
python -m cats
```
The model will run, and store results files in the specified results directory.
