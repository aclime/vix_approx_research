import os
import pandas as pd
from glob import glob
from datetime import timedelta


def consolidate_treasurey_files():
    #return os.getcwd()
    root='/Users/austinclime/vs_code_projects/vix_approx/vix_approx_research/'
    #daily_files_by_year= glob('treasury_rates/daily-treasury-rates*.csv')
    daily_files_by_year= glob(root+'/treasury_rates/daily-treasury-rates*.csv')
    combined_df=pd.concat([pd.read_csv(f) for f in daily_files_by_year])
    combined_df['Date']=pd.to_datetime(combined_df['Date'])
    combined_df.set_index(['Date'],inplace=True)
    combined_df.sort_index(ascending=False,inplace=True)
    combined_df/=100
    
    #combined_df.columns=[maturity_mapping.get(col) for col in combined_df.columns]
    
    dest=root+'/treasury_rates/consol_treasury_rates.csv'
    combined_df.to_csv(dest,index=True)
    #return combined_df
    #return daily_files_by_year

# Pull the Yield curve from the day prior like the CBOE does
def get_yc_history():
    yc_pull=pd.read_csv(f'treasury_rates/consol_treasury_rates.csv',index_col='Date')
    #display(yc_pull)
    #corresponding number of days used in the natural cubic spline interpolation for each fixed maturity found on the website are as follows
    maturity_mapping={'1 Mo':30,
                    '2 Mo':60, 
                    '3 Mo':91,
                    '4 Mo':121, 
                    '6 Mo':182, 
                    '1 Yr' :365,
                    '2 Yr':730, 
                    '3 Yr' :1095,
                    '5 Yr' :1825,
                    '7 Yr' :2555,
                    '10 Yr':3650, 
                    '20 Yr':7300, 
                    '30 Yr':10950}
    yc_pull.columns=[maturity_mapping.get(col) for col in yc_pull.columns]
    return yc_pull
