import numpy as np
import pandas as pd
import geopandas as gpd
from utilities import load_yaml, eval_mnl

class OLAF_model:
    def __init__(self,config):
        # The initialization code should read a YAML config file and use it to define the basic parameters of the model
        # Examples: number of zones, number of product types
        # Probabaly can use this to load initial supply inventory and capacity values by product type
        self.config = load_yaml(config)
        self.base_df = gpd.read_file(self.config['zonal_inputs'])
        # Note on control totals: rather than a single "growth" value, include both growth and decline to allow churn
        self.product_types = self.config['product_types']
    def validate(self):
        # This method may contain functions to verify that the internal data structures are consistent
        pass
    def evaluate(self):
        # Evaluates the supply inventory in its current state, including scoring the utility of development options
        # A lot of customization should be allowed here--ideally, the user can write their own custom scoring function
        # Ultimately, an entire bid-rent analysis might just plug-in here
        pass
    def enumerate(self,k,v):
        # This method enumerates k development options for product type v, within build-out capacities (reflecting filters)
        # Valid development options are a subset of all zones and product types
        pass
    def denumerate(self,k,v):
        # This method enumerates k potential redevelopment sites for inventory product type v, respecting appropriate filters
        pass
    def undevelop(self):
        # This method allocates negative control total "stocks" to development option "sinks" using Monte Carlo simulation
        # method is the same as below, except:
        # - only options that are non-zero are eligible for removal from inventory
        # - sign of score is flipped so that lower-utility options are likelier for selection
        pass
    def allocate(self):
        # This method allocates positive control total "stocks" to development option "sinks" using Monte Carlo simulation
        pass
