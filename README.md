# OLAF: an Open Land-use Allocation Framework

![](https://upload.wikimedia.org/wikipedia/en/6/6d/Olaf_from_Disney%27s_Frozen.png?20151210060105)

This is an ultra-minimalist Python 3 script designed to serve as a code pattern for building simple and flexible microsimulation-based land use allocation models.  Such models are generally used to predict the spatial distribution of forecasted control totals of various quantities of development activity (such as housing units or square feet of commercial real estate).  Urban planners and transportation engineers use the predictions to run travel forecasting models that estimate traffic on roads and ridership on transit lines; those numbers are used to help prioritize which proposed transportation projects are built and/or to measure the performance of alternative networks with respect to key indicators such as emissions.

## Design Philosophy
There are a wide range of land use models to choose from which are based upon specific theories of urban development promulgated by various economists, planners, and other thinkers; these are implemented with highly complex code that is tightly bound to the theory upon which they are based.  This library seeks to be as theory-agnostic as possible; the only theoretical construct it presupposes is that of multinomial logit location choice, as described by Nobel award-winning economist Daniel McFadden in his seminal 1978 [paper](https://www.semanticscholar.org/paper/Modelling-the-Choice-of-Residential-Location-McFadden/55a63c2a72325a86de9a17814fb6243c132ac19a) "Modeling the Choice of Residential Location".  Whether the hypothetical agent choosing from available locations is a household, a firm, or a developer is up to you; the basic idea in all cases is that each location has some "utility", or benefit, that can be scored, and used to compute the probability that any particular location is the highest-scoring of the options available to that agent.

We do not make any assumptions regarding the number of locations in the study area; models built using this script could be parcel-based, gridcell-based, TAZ-based, or constructed from other geographic units of analysis such as Census Blocks.  In some such cases if every possible location were included in the set of available choices, it would become infeasible to compute the choice probabilities; so a sample of choices is drawn instead and the selection of an alternative based upon utility scores is simulated (i.e. Monte Carlo simulation). Constraints such as developable land capacity, zoning regulations, or other practicalities can be implmented as filters or queries applied during the choice set selection phase.

## User Configuration
A single [YAML](https://yaml.org/)-format configuration file is used to specify the input data (in CSV format).  Examples of the input data and config file are provided.  Do not confuse these for an actual land use model nor any kind of assumptions recommended by the code author(s).

## Dependencies
Aside from Python 3, the script requires NumPy, Pandas and PyYAML.  These can be installed using the command:

`pip3 install pandas numpy pyyaml`

It is good practice to create a virtual environment before doing this, e.g.:

`python3 -m venv env && source env/bin/activate`

## Disclaimer
This script should be considered Beta software, published under an MIT license.  It makes use of Pandas functions which perform arbitrary executions on a dataframe and therefore could possibly present a security vulnerability.  The author assumes no liability whatsoever for any damages incurred by users.
