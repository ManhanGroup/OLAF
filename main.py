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
        self.zone_df = gpd.read_file(self.config['zonal_inputs'])
        self.zone_df.set_index(self.config['geo_id'])
        self.land_uses = self.config['land_uses']
    def validate(self):
        # This method may contain functions to verify that the internal data structures are consistent
        pass
    def enumerate(self,n,land_use):
        # This method enumerates n development options for a land use, within build-out capacities (reflecting filters)
        # Valid development options are a subset of all zones and product types
        capacity_field = self.land_uses["land_use"]["capacity"]
        inventory_field = self.land_uses["land_use"]["inventory"]
        potential = np.maximum(self.zone_df[capacity_field] - self.zone_df[inventory_field], 0)
        options = zone_df.sample(n,weights=potential)
        return(options)
    def allocate(self):
        # This method allocates land use control totals using Monte Carlo simulation
        for land_use in self.land_uses:
            value_fn = self.land_uses[land_use]["value_fn"]
            growth = int(self.land_uses[land_use]["growth"])
            for draw in range(growth):
                options = self.enumerate(30,land_use)
                utility = options.eval(value_fn)
                expUtil = np.exp(utility)
                zoneSel = self.zone_df.sample(1,weights=expUtil)[self.config['geo_id']]
                self.zone_df[self.config['geo_id']==zoneSel,:][self.land_uses[land_use]["inventory"]] += 1
