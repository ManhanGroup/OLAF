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




class model:
    def __init__(self,config):
        # The initialization code should read a YAML config file and use it to define the basic parameters of the model
        # Examples: number of zones, number of product types
        # Probabaly can use this to load initial supply inventory and capacity values by product type
        self.config = load_yaml(config)
        self.zone_df = pd.read_csv(self.config['zonal_data'])
        self.id = self.config['geo_id']
        self.zone_df.set_index(self.id,drop=False,inplace=True)
        self.neighbors=np.load(self.config['neighbors'])
        self.year=self.config['year']
        self.land_uses = self.config['land_uses']
        self.draws = self.config['draws']
        self.qry_developable=self.config['filter_Undevelopable']
        self.cnty_sqft_per_unit=self.config['BuildingSQFT_per_Unit']

        
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
           print("Total {} units of {} to allocate".format(self.land_uses[LU]['total'],self.land_uses[LU]['name']))

        while len(self.land_uses)>0:
            LU = random.choice(list(self.land_uses.keys()))
                      
            store_fld = self.land_uses[LU]["store_fld"]
            value_fn=self.land_uses[LU]["value_fn"]
            options = self.sample_alts(LU)
            utility = options.eval(value_fn,inplace=False).to_numpy()
            expUtil = np.nan_to_num(np.exp(utility))
            denom = np.sum(expUtil)
            probs = expUtil/denom
            zoneSel = rng.choice(options.index,p=np.nan_to_num(probs))
            if self.land_uses[LU]["capacity_fn"]==1:
               alloc = 1
            else: 
               alloc=int(min(self.land_uses[LU]["total"],np.ceil(self.zone_df.loc[self.zone_df[id]==zoneSel].eval(self.land_uses[LU]["capacity_fn"],inplace=False).squeeze())))
            self.zone_df.at[zoneSel,store_fld] += alloc
            #print(self.zone_df.loc[self.zone_df[store_fld]>0][store_fld].count())
            self.land_uses[LU]["total"]=self.land_uses[LU]["total"]-alloc

            remaining = int(self.land_uses[LU]["total"])
            #print("Remaining {} {}  to allocate".format(self.land_uses[LU]['total'] , self.land_uses[LU]['name']))
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

    def updateneighbor(self):
       # Load neighbors from the NPY file
       # remove the address/point itself from the array because it itself is its nearest neighbour
       neighbors = self.neighbors[:, 1:]
       self.zone_df.loc[(self.zone_df.BuildingSQFT>0) & (pd.isnull(self.zone_df.YearBuilt)), '.YearBuilt']=self.year+np.random.integer(0,5)
       self.zone_df.loc[(self.zone_df.BuildingSQFT>0), 'bldage']=self.zone_df.loc[(self.zone_df.BuildingSQFT>0),'.YearBuilt'].map(lambda x: self.year+5-x)

       #Create a dataframe to store intermediate columns
       nei_parcel = pd.DataFrame(index=self.zone_df.index)
       ncols=['neighbors_age','neighbors_totalunits','neighbors_BUILDING_SQFT','neighbors_PARCEL_SQFT','neighbors_per_built']
       for c in ncols:
           nei_parcel[c]=None

       #calculate neiboring parcels total building ages
       nei_parcel['neighbors_age']= [self.zone_df['bldage'].iloc[n].sum() for n in neighbors]

       #calculate neiboring parcels total building sqft and total parcel sqft
       nei_parcel['neighbors_BUILDING_SQFT']= [self.zone_df['BuildingSQFT'].iloc[n].sum() for n in neighbors]
       nei_parcel['neighbors_PARCEL_SQFT']= [self.zone_df['usableland'].iloc[n].sum() for n in neighbors]
    

       #calculate neiboring parcels percent with building_sqft>0
       nei_parcel['neighbors_per_built']= [self.zone_df['BuildingSQFT'].iloc[n].map(lambda x: 1 if x>0 else 0).sum()/8.0 for n in neighbors]
       
       #calculate neiboring parcels total units and total jobs
       nei_parcel['neighbors_totalunits'] = [self.zone_df['TOT_DU_final'].iloc[n].sum() for n in neighbors]
       nei_parcel['neighbors_totaljobs'] = [self.zone_df['JOBS_final'].iloc[n].sum() for n in neighbors]

       #calculate neiboring building sqft
       nei_parcel['neighbors_BuildingSQFT']= [self.zone_df['BuildingSQFT'].iloc[n].sum() for n in neighbors]
       
       jobcates=self.zone_df.columns[self.zone_df.columns.str.startswith('emp')] #list of job categories
       for k in jobcates:
        if k!='emptot_p':
            self.zone_df[k+'_final']=self.zone_df[k]*self.zone_df['JOBS_final']/self.zone_df['emptot_p'].map(lambda x: 1 if x==0 else x)
            #calculate neiboring parcels jobs by category
            nei_parcel['neighbors_'+k]= [self.zone_df[k+'_final'].iloc[n].sum() for n in neighbors]               

       
       self.zone_df['neighbors_FAR']=nei_parcel['neighbors_BUILDING_SQFT']/nei_parcel['neighbors_PARCEL_SQFT'].map(lambda x: x if x>0 else 1) 
       self.zone_df['neighbors_bldsqft_per_unit']=nei_parcel['neighbors_BUILDING_SQFT']/nei_parcel['neighbors_totalunits'].map(lambda x: x if x>0 else 1)
       self.zone_df['neighbors_unit_per_acre']=nei_parcel['neighbors_totalunits']*43560.0/nei_parcel['neighbors_PARCEL_SQFT'].map(lambda x: x if x>0 else 1)

       self.zone_df.loc[:,'neighbors_bldsqft_per_unit']=nei_parcel['neighbors_BuildingSQFT']/nei_parcel['neighbors_totalunits'].map(lambda x: x if x>0 else 1)
       self.zone_df.loc[:,'neighbors_bldsqft_per_unit']=self.zone_df.loc[:,'neighbors_bldsqft_per_unit'].fillna(self.cnty_sqft_per_unit)
       
       self.zone_df['neighbors_bldsqft_per_unit_n']=np.log(self.zone_df['neighbors_bldsqft_per_unit'].map(lambda x: 1 if (x==0) | (x is None) else x))/np.log(self.zone_df['neighbors_bldsqft_per_unit'].max())
       self.zone_df['neighbors_age_n']=self.zone_df['neighbors_age']/(self.zone_df['neighbors_per_built'].map(lambda x: 1 if (x==0) | (x is None) else x)*8)
       self.zone_df['neighbors_age_n']=self.zone_df['neighbors_age_n']/self.zone_df['neighbors_age_n'].max()

       #calculate neiboring total households
       nei_parcel['neighbors_totalhh']= [self.zone_df['TOT_HH'].iloc[n].sum() for n in neighbors]

       #calculate neiboring total sf units
       nei_parcel['neighbors_sfunits']= [self.zone_df['SFDU_final'].iloc[n].sum() for n in neighbors]
       self.zone_df['Vacancy']=self.zone_df.apply(lambda r: 1 if r.TOT_DU_final==0 & r.JOBS_final==0 else 0, axis=1)

       nei_parcel['neighbors_totvacancy']= [self.zone_df['Vacancy'].iloc[n].sum() for n in neighbors]

       #calculate neighboring parcels average percentage of improved value and FAR ratio
       self.zone_df.loc[:,'neighbors_hudensity']=nei_parcel['neighbors_totalunits']*43560.0/nei_parcel['neighbors_PARCEL_SQFT'].map(lambda x: x if x>0 else 1) 
       self.zone_df.loc[:,'neighbors_jobdensity']=nei_parcel['neighbors_totaljobs']*43560.0/nei_parcel['neighbors_PARCEL_SQFT'].map(lambda x: x if x>0 else 1)

       self.zone_df.loc[:,'neighbors_hhvshu']=1-nei_parcel['neighbors_totalhh']/nei_parcel['neighbors_totalunits'].map(lambda x: x if x>0 else 1)
       self.zone_df.loc[:,'neighbors_per_sf']=1-nei_parcel['neighbors_sfunits']/nei_parcel['neighbors_totalunits'].map(lambda x: x if x>0 else 1)
       self.zone_df.loc[:,'neighbors_per_blt']=1-nei_parcel['neighbors_totvacancy']/8.0
       selcols=['neighbors_per_'+k for k in jobcates if k!='emptot_p']

       valuebygeoid_bg=self.zone_df.groupby('GEOID10')[['BuildingSQFT', 'emptot_p','sqft_p', 'TOT_DU', 'calarea']].sum().reset_index()
       valuebygeoid_bg['bg_far']=valuebygeoid_bg['BuildingSQFT']/(10.7639104*valuebygeoid_bg['calarea'].map(lambda x: x if x>0 else 1))   #floor area ratio using calculated area of the parcel polygon instead of sqft in the modeling point data 
       valuebygeoid_bg['bg_jobdensity']=valuebygeoid_bg['emptot_p']*43560.0/valuebygeoid_bg['sqft_p'].map(lambda x: x if x>0 else 1)   #calculate job density per parcel area using sqft_p that comes in the same file as emptot_
       valuebygeoid_bg['bg_hudensity']=valuebygeoid_bg['TOT_DU']*43560.0/valuebygeoid_bg['sqft_p'].map(lambda x: x if x>0 else 1)   #calculate hu density per parcel area using sqft_p that comes in the same file as emptot_
       valuebygeoid_bg_age=self.zone_df.loc[~pd.isnull(self.zone_df.bldage) & (self.zone_df.bldage<200) ].groupby('GEOID10')['bldage'].mean().reset_index() #average age if the buildings in the block
       valuebygeoid_bg_age['bg_average_age_n']=valuebygeoid_bg_age['bldage']/valuebygeoid_bg_age['bldage'].max()  #Normalize the average ag
       self.zone_df.drop(columns=['bg_far','bg_hudensity', 'bg_jobdensity','bg_average_age_n'], inplace=True)
       self.zone_df=self.zone_df.merge(valuebygeoid_bg[['GEOID10','bg_far','bg_hudensity', 'bg_jobdensity']], on="GEOID10", how='left').merge(valuebygeoid_bg_age[['GEOID10','bg_average_age_n']], on="GEOID10", how='left')
 
       def calculate_entropy(row):
        return -sum((row[col] * np.log(row[col]) if row[col]>0 else 0) for col in selcols)
       self.zone_df.loc[:,'neighbors_jobentropy'] = self.zone_df.apply(calculate_entropy, axis=1).fillna(0)

       for k in jobcates:
        #calculate neiboring parcels total ret jobs
        if(k!='emptot_p'):
              self.zone_df.loc[:,'neighbors_per_'+k]=nei_parcel['neighbors_'+k]/nei_parcel['neighbors_emptot_p'].map(lambda x: x if x>0 else 1)
              
      
   
      
     

def main():
    test_model = model(sys.argv[1])
    test_model.allocate()
    test_model.update()
    test_model.zone_df.to_csv(sys.argv[2], index=False)

if __name__=="__main__":
    import os
    main()