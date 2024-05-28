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
import random

def read_biogeme_params(data_path):
  params = {}
  try:
    # Read data from CSV assuming header=None (no header row)
    data = pd.read_csv(data_path)
    
    for k, v in zip(data['fields'], data['Value']):
      if k.startswith('B_'):
        param_name = k[2:]
        params[param_name] = float(v)  # Assuming numeric values
  except FileNotFoundError:
    print(f"Error: File not found at {data_path}")
  return params


def calculate_utility(params, parcel_frame):
  utility = 0
  for col, value in params.items():
    if col in parcel_frame.columns:
      utility += value * parcel_frame[col]
    
  return utility


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
        self.draws = self.config['draws']
        self.qry_developable=self.config['filter_Undevelopable']
        #specify the field used to aggregate total units and occupied units to check for vacancy ratio
        self.vacancy_agg_fld=self.config['vacancy_cap_aggregate_unit']
        
    def sample_alts(self,LU):
        # This method samples development options for a land use, respecting filters
        sites_avail = self.zone_df.query(self.land_uses[LU]["filter_fn"] + " & "+ self.qry_developable) 
        site_sample = sites_avail.sample(self.draws,replace=False,axis=0)
        return(site_sample)
    def allocate(self):
        start = time.time()
        # This method allocates land use control totals using Monte Carlo simulation
        id = self.config['geo_id']
        #dev_queue = [] # enumerate a "queue" of development projects to build
        queue_len = 0
        position = 0
        progress = 0
        _last_part = 0
        print("Allocating queue...")

        for LU in self.land_uses:
           queue_len += int(self.land_uses[LU]["total"])
           store_fld = self.land_uses[LU]["store_fld"]
           self.zone_df[store_fld] = 0 # initialize field to which units will be allocated
           #for each lu type get target vacancy ratio: ratio of unoccupied space divided by total space available; note it is difference from the vacancy indicator in the data frame. The latter indicates where there is building on parcel or not.
           self.target_vacancy_rate = self.land_uses[LU]["target_vacancy_rate"]
           agghhvshu=self.zone_df.groupby(self.vacancy_agg_fld)[[self.land_uses[LU]["total_units"],self.land_uses[LU]["occupied_units"]]].sum().reset_index()
           agghhvshu.loc[:, self.land_uses[LU]["vacancy_cap_fld"]] = np.floor(-1*((agghhvshu.loc[:,self.land_uses[LU]["occupied_units"]]) /(self.target_vacancy_rate - 1)))-agghhvshu.loc[:,self.land_uses[LU]["total_units"]]
           # check edge case; if there are few units built (eg. < 25 percentile among all blocks) we should build even when it causes a high vacancy rate
           max_vacant_units = agghhvshu[self.land_uses[LU]["total_units"]].describe()['25%']
           # this allows for up to max_vacant_units*2 - 1 units to be built before any
           # are occupied
           agghhvshu.loc[agghhvshu[self.land_uses[LU]["total_units"]]< max_vacant_units, self.land_uses[LU]["vacancy_cap_fld"]] =max_vacant_units
           agghhvshu.loc[:, self.land_uses[LU]["vacancy_cap_fld"]] = self.land_uses[LU]['flag']* agghhvshu.loc[:, self.land_uses[LU]["vacancy_cap_fld"]] 

           #set minimum vacancy_cap to 1 even for areas with high vacancy ratio
           agghhvshu.loc[agghhvshu[self.land_uses[LU]["vacancy_cap_fld"]]<=0, self.land_uses[LU]["vacancy_cap_fld"]] = 1

           self.zone_df=self.zone_df.merge(agghhvshu[[self.vacancy_agg_fld,self.land_uses[LU]["vacancy_cap_fld"]]], on=self.vacancy_agg_fld, how='inner').copy()

           print("Total {} units of {} to allocate".format(self.land_uses[LU]['total'],self.land_uses[LU]['name']))
        while len(self.land_uses)>0:
            LU = random.choice(list(self.land_uses.keys()))
            store_fld = self.land_uses[LU]["store_fld"]
            self.zone_df[store_fld] = 0 # initialize field to which units will be allocated
            #print("Enumerating " + self.land_uses[LU]['name'] + " to allocate")
            
            store_fld = self.land_uses[LU]["store_fld"]
            value_fn = self.land_uses[LU]["value_fn"]
            options = self.sample_alts(LU)
            params = read_biogeme_params(self.land_uses[LU]['big_para_file'])
            utility = calculate_utility(params, options)
            #utility = options.eval(value_fn,inplace=False).to_numpy()
            expUtil = options[self.land_uses[LU]["vacancy_cap_fld"]]*np.exp(utility)
            denom = np.sum(expUtil)
            probs = expUtil/denom
            zoneSel = rng.choice(options.index.to_numpy(),p=probs)
            if self.land_uses[LU]["capacity_fn"]==1:
               alloc = 1
            else: 
               alloc=int(min(self.land_uses[LU]["total"],np.ceil(self.zone_df.iloc[[zoneSel]].eval(self.land_uses[LU]["capacity_fn"],inplace=False).squeeze())))
            self.zone_df.at[zoneSel,store_fld] += alloc
            self.land_uses[LU]["total"]=self.land_uses[LU]["total"]-alloc

            remaining = int(self.land_uses[LU]["total"])
            print("Remaining {} {}  to allocate".format(self.land_uses[LU]['total'] , self.land_uses[LU]['name']))
            if self.land_uses[LU]["total"]==0:
               self.land_uses.pop(LU, None)            
            

            position = position + alloc
            progress = round(100*(position)/queue_len,0)
            part = round((progress % 10)/2,0)
            if part != _last_part:
                if part == 0:
                    print(f"{progress}%")
                else:
                    print(".", end="", flush=True)

            _last_part = part

        
        run_min = round((time.time()-start)/60,1)
        print(f"Total run time = {run_min} minutes")
    def update(self):
        # this is a function for custom updates on the dataframe before/after allocation
        for op in self.config['update_block']:
            self.zone_df.eval(op, inplace=True)

def main():
    test_model = model(sys.argv[1])
    test_model.allocate()
    test_model.update()
    test_model.zone_df.to_csv(sys.argv[2], index=False)

if __name__=="__main__":
    import os
    os.chdir(r'.\OLAF-SRTA')
    main()