import numpy as np
import pandas as pd
import yaml
import sys
rng = np.random.default_rng(12345)

## Load config details from YAML
def load_yaml(filename):
    with open(filename, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as error:
            print(error)
    return None

import time

class model:
    def __init__(self,config):
        # The initialization code should read a YAML config file and use it to define the basic parameters of the model
        # Examples: number of zones, number of product types
        # Probabaly can use this to load initial supply inventory and capacity values by product type
        self.config = load_yaml(config)
        self.zone_df = pd.read_csv(self.config['zonal_data'])
        self.id = self.config['geo_id']
        self.zone_df.set_index(self.id,drop=False,inplace=True)
        self.land_uses = self.config['land_uses']
    def sample_alts(self,n,LU):
        # This method samples n development options for a land use, respecting filters
        sites_avail = self.zone_df.query(self.land_uses[LU]["filter_fn"]) 
        site_sample = sites_avail.sample(n,replace=False,axis=0)
        return(site_sample)
    def allocate(self):
        start = time.time()
        # This method allocates land use control totals using Monte Carlo simulation
        id = self.config['geo_id']
        dev_queue = [] # enumerate a "queue" of development projects to build
        for LU in self.land_uses:
            store_fld = self.land_uses[LU]["store_fld"]
            inventory = self.land_uses[LU]["inventory"]
            self.zone_df[store_fld] = self.zone_df[inventory] # initialize with the existing stock
            print("Enumerating " + self.land_uses[LU]['name'] + " to allocate")
            growth = int(self.land_uses[LU]["growth"])
            for draw in range(growth):
                dev_queue.append(LU)
        rng.shuffle(dev_queue) # randomize the order so no specific LU gets priority
        position = 0
        progress = 0
        _last_part = 0
        print("Allocating queue...")
        for LU in dev_queue:
            position = position + 1
            progress = round(100*(position)/len(dev_queue),0)
            part = round((progress % 10)/2,0)
            if part != _last_part:
                if part == 0:
                    print(f"{progress}%")
                else:
                    print(".", end="", flush=True)
            _last_part = part
            store_fld = self.land_uses[LU]["store_fld"]
            value_fn = self.land_uses[LU]["value_fn"]
            options = self.sample_alts(30,LU)
            utility = options.eval(value_fn,inplace=False).to_numpy()
            expUtil = np.exp(utility)
            denom = np.sum(expUtil)
            probs = expUtil/denom
            zoneSel = rng.choice(options[id].to_numpy(),p=probs)
            self.zone_df.at[zoneSel,store_fld] += 1
        run_min = round((time.time()-start)/60,1)
        print(f"Total run time = {run_min} minutes")

def main():
    test_model = model(sys.argv[1])
    test_model.allocate()
    test_model.zone_df.to_csv(sys.argv[2])

if __name__=="__main__":
    main()