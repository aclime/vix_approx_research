import io
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as pv

from io import StringIO
from datetime import timedelta
import pytz
import datetime

#import pandas_datareader.data as web
import pandas_market_calendars as mcal
from scipy.interpolate import CubicSpline, interp1d

from box_client import make_client
client=make_client()

CMT=30 #constant maturity term: 30 days
mins_in_year=365*24*60
CMT_mins=CMT*24*60

from interest_rate_consol import get_yc_history
yc_pull=get_yc_history()

#sample input:
#periods_dict={0:{'year':2023,'month':2},
#            1:{'year':2023,'month':3}}
def retreiev_OM_data(periods_dict): #MAYBE only allow one month and year here
    """ given a specific range of periods to search,
    retrieve daily OptionMetrics data stored in monthly-level files
    link: https://umd.box.com/s/m7ak9i8e1uotzrpiumnvnj9sfk22reyh
    """
    ################
    #client=make_client()
    ################
    returned_dfs=[]
    om_folder_srch=client.search().query(query='OptionMetrics', type='folder')
    om_folder_id=[item.id for item in om_folder_srch][0]
    #res=client.folder(om_folder_id).get_items(limit=2)
    res=client.folder(om_folder_id).get_items(limit=None)

    for r in res:
        #print(r.name)
        file_name=r.name
        year=file_name.split('.')[0].split('_')[1]
        month=file_name.split('.')[0].split('_')[-1]
        for k,v in periods_dict.items():
            #print(v)
            #print(int(v['year']) == year)
            #print(int(v['month']) , month)
            #print('----')
            
            if (int(v['year'])==int(year)) and (int(v['month'])==int(month)):
                # https://support.box.com/hc/en-us/community/posts/360049203253-Read-box-files-in-python
                file_content = r.content()
                s=str(file_content,'utf-8')
                data = StringIO(s)
                df = pd.read_csv(data)
                #df.to_csv(r.name)
                #display(df.head())
                returned_dfs.append(df)
    return pd.concat(returned_dfs)

def change_date_cols(df):
    df['date'] = pd.to_datetime(df['date'])
    df['exdate'] = pd.to_datetime(df['exdate'])
    df['last_date'] = pd.to_datetime(df['last_date'])
    return df

def filter_option_types_and_expirations(df):
    """
    #ExpiryIndicator  This field indicates if the option is a regular, weekly or monthly option.                          
        #blank – regular option expiring on the third Friday of a month or unknown 
        # w – weekly option 
        # d – daily option 
        # m – end of month option
    """
    df=change_date_cols(df)
    lb=min(df.exdate)
    ub=max(df.exdate)
    #CBOE Holidays and Early Closes
    #   NOTE: need to come back to early closes
    cboe=mcal.get_calendar('CBOE_Index_Options')
    cboe_holidays=cboe.holidays()
    cboe_holidaylist=pd.to_datetime(cboe_holidays.holidays)
    #sched=cboe.schedule(start_date=lb, end_date=ub)
    #cboe.early_closes(schedule=sched)

    #Times to Expiration
    fridays = list( pd.date_range(lb, ub,freq='W-FRI', tz='US/Eastern',normalize=True).values )
    third_fridays = list( pd.date_range(lb, ub,freq='WOM-3FRI', tz='US/Eastern',normalize=True).values )
    fridays=pd.to_datetime(fridays).normalize()
    third_fridays=pd.to_datetime(third_fridays).normalize()
    diffed_fridays=list(set(fridays)-set(third_fridays))
    
    #1. Make sure option has not already expired
    #2. Filter for standard and weekly options
    df2=df[ (df.exdate>=df.date) & 
       ( (df.expiry_indicator.isin(['w']) | (pd.isnull(df.expiry_indicator))) ) ]
    
    expirs=df2.exdate.unique()
    expir_dict={}
    holiday_dict={}
    for expir in expirs:
        #Determine type of expiration
        if expir in third_fridays:
            expir_dict[expir]=2 #third friday
        elif expir in diffed_fridays:
            expir_dict[expir]=1 #fridays besides third of month
        else:
            expir_dict[expir]=0 #other expiration
        #Determine if expiration falls on a holiday
        if expir in cboe_holidaylist:
            holiday_dict[expir]=True
        else:
            holiday_dict[expir]=False
    df2=df2.copy()
    df2['exp_code']=df2['exdate'].map(expir_dict)
    df2['holiday_exp']=df2['exdate'].map(holiday_dict)
     #SPXW option contracts expiring at end of week,
     #   excluding the ones expiring on the same date as AM-settled
     #   SPX option contracts.
    df3=df2[~( (df2.exp_code==2) & (df2.symbol.str.contains('SPXW')) )]
    return df3

def add_expiration_time(df3): #SLOWWWWW
    #standard SPX 9:30 a.m. ET
    #weekly SPXW 4:15 p.m. ET
    #Taking out non-friday expirations
    df4=df3[df3.exp_code!=0]

    def add_exp_time(row):
        exp_date=row.exdate
        exp_code=row.exp_code
        if exp_code==2:
            exp_time=pytz.timezone('US/Eastern').localize(exp_date.replace(hour=9,minute=30))
        elif exp_code==1:
            exp_time=pytz.timezone('US/Eastern').localize(exp_date.replace(hour=16,minute=15))
        return exp_time
    
    df4=df4.copy()
    #add closing day datetime to date
    df4['datetime_close']=df4['date'].apply(lambda x:pytz.timezone('US/Eastern').localize(x.replace(hour=16,minute=15)) )
    #add timestamp to expiration date based on rules
    df4['ex_time']=df4.apply(add_exp_time,axis=1)
    return df4

def find_between(lst, num):
    """Finds the two numbers in a sorted list that a given number is between."""
    lst.sort()  # Ensure the list is sorted
    for i in range(len(lst) - 1):
        if lst[i] <= num <= lst[i + 1]:
            return lst[i], lst[i + 1]
    return None  # Number is not between any pair in the list

def calculate_interest_rates(current_date,t):
    #display(yc_pull)
    
    #prior_day=current_date-timedelta(days=1)
    #print(prior_day)
    #yc_yday=yc_pull.loc[str(prior_day)]
    yc_yday=yc_pull.iloc[ yc_pull.index.get_loc(str(current_date))+1 ]
    
    #print(yc_yday)
    #t=next_term_df.iloc[0].time_to_exp.days
    #t=near_term_df.iloc[0].time_to_exp.days
    #t=24
    intvl=find_between(list(yc_yday.keys()), t) 
    if intvl:
        #print(list(intvl) )
        #print( [yc_yday[i] for i in intvl])
        BEY=CubicSpline(list(intvl),[yc_yday[i] for i in intvl],
                        bc_type='natural',extrapolate=True )(t,0)
        #print(BEY)
        APY=(1+BEY/2)**2-1
        r=np.log(1+APY)
    elif t<min(yc_yday.index):
        #print(t)
        t_1,CMT_1=yc_yday.index[0],yc_yday.iloc[0]
        t_x,CMT_x=yc_yday.index[1],yc_yday.iloc[1]
        m_low=(CMT_x-CMT_1)/(t_x-t_1)
        b_low=CMT_1-m_low*t_1
        m_up=0
        b_up=CMT_1+m_up*t_1
        #print(b_low,b_up)
        BEY=CubicSpline([t_1,t_x],
                        [b_low,b_up],bc_type='natural',extrapolate=True )(t,0)
        #print(BEY)
        APY=(1+BEY/2)**2-1
        r=np.log(1+APY)
    #print(r)
    return r



def calculate_sigma_sq(term_df,r,t):

    ATM_strike_cands=term_df[~( (pd.isnull(term_df.best_bid)) | (pd.isnull(term_df.best_offer)) ) 
             & ~(term_df.best_bid>term_df.best_offer) 
             & ~( (term_df.best_bid<=0)  )  ]

    def min_strike_diff(slice):
        #display(slice[slice.cp_flag=='P'])
        if ('C' in slice.cp_flag.unique()) and ('P' in slice.cp_flag.unique()):
            return abs( slice[slice.cp_flag=='P'].midpoint_price.values[0] - slice[slice.cp_flag=='C'].midpoint_price.values[0])

    F_strike=ATM_strike_cands.groupby(['strike_price']).apply(min_strike_diff).idxmin()
    call_put_diff=ATM_strike_cands[(ATM_strike_cands.strike_price==F_strike)].sort_values(by='cp_flag')['midpoint_price'].diff().dropna().values[0]
    F=F_strike+np.exp(r*t)*call_put_diff
    K0=term_df[term_df.strike_price<=F].strike_price.max()
    #term_df[(term_df.strike_price<K0)&(term_df.best_bid<=0)][['best_bid','best_offer','strike_price','midpoint_price']]

    def filter_included_options(opt_type):
        if opt_type=='put':
            OOM_opts=term_df[(term_df.strike_price<K0)&(term_df.cp_flag=='P')]
            OOM_opts=OOM_opts.copy()
            OOM_opts['excl_ind']=OOM_opts.best_bid.apply(lambda x: pd.isnull(x) or x<=0)
            OOM_opts.sort_values(by=['strike_price'],ascending=False,inplace=True) #sort upside down for puts
        else:
            OOM_opts=term_df[(term_df.strike_price>K0)&(term_df.cp_flag=='C')]
            OOM_opts=OOM_opts.copy()
            OOM_opts['excl_ind']=OOM_opts.best_bid.apply(lambda x: pd.isnull(x) or x<=0)
            #dont need to change sorting order for calls

        OOM_opts['excl_ind']=OOM_opts['excl_ind'].cumsum()
        incl_opts=OOM_opts[OOM_opts.excl_ind<2]
        incl_opts=incl_opts[incl_opts.best_bid>0]
        if opt_type=='put':
            incl_opts.sort_values(by=['strike_price'],ascending=True,inplace=True)#change back
        return incl_opts

    incl_puts,incl_calls=filter_included_options('put'),filter_included_options('call')

    pca=pd.DataFrame.from_dict({'strike_price':K0,'cp_flag':'P/C Avg', #put-call average
                            'midpoint_price':term_df[(term_df.strike_price==K0)]['midpoint_price'].mean()},orient='index').T
    #pca=term_df[(term_df.strike_price==K0)]['midpoint_price'].mean()#put-call average

    opt_portfolio=pd.concat([incl_puts,pca,incl_calls])[['strike_price','cp_flag','midpoint_price']]
    opt_portfolio['dK']=(opt_portfolio.strike_price.shift(-1)-opt_portfolio.strike_price.shift(1))/2
    opt_portfolio=opt_portfolio.copy()
    opt_portfolio.iloc[0]['dK']=opt_portfolio.iloc[1]['strike_price']-opt_portfolio.iloc[0]['strike_price']
    opt_portfolio.iloc[-1]['dK']=opt_portfolio.iloc[-1]['strike_price']-opt_portfolio.iloc[-2]['strike_price']
    opt_portfolio['contribution_by_strike']=opt_portfolio.dK/opt_portfolio.strike_price**2
    opt_portfolio['contribution_by_strike']*=opt_portfolio['midpoint_price']*np.exp(r*t)
    #opt_portfolio
    correction_term=(1/t)*(F/K0-1)**2
    sigma_sq=opt_portfolio.contribution_by_strike.sum()*(2/t)-correction_term
    #sigma_sq**0.5
    return sigma_sq

def calculate_vix_daily(day_df):
    unique_expirs=day_df.ex_time.unique()
    #print(unique_expirs)
    const_matur_expir=day_df.iloc[0].datetime_close+timedelta(days=CMT) #constant maturity expir
    #print(const_matur_expir)

    #Find closest expiration to the CMT expiration without going over
    near_term_exp=max(unique_expirs[unique_expirs<=const_matur_expir])
    near_term_df=day_df[day_df.ex_time==near_term_exp]
    #Find closest expiration to the CMT expiration that is strictly above
    next_term_exp=min(unique_expirs[unique_expirs>const_matur_expir])
    next_term_df=day_df[day_df.ex_time==next_term_exp]

    #CAN USE THIS TO GET DATE WHEN GROUPBY
    current_date=day_df.iloc[0].datetime_close.date() #current date
    current_date

    #minutes to expiration
    near_term_mins=near_term_df.time_to_exp.iloc[0].total_seconds()/60
    next_term_mins=next_term_df.time_to_exp.iloc[0].total_seconds()/60
    t_near,t_next=near_term_mins/mins_in_year,next_term_mins/mins_in_year
    #print(t_near,t_next)
    #Interest Rates
    r_near=calculate_interest_rates(current_date,near_term_df.iloc[0].time_to_exp.days)
    r_next=calculate_interest_rates(current_date,next_term_df.iloc[0].time_to_exp.days)

    sigma_sq_near=calculate_sigma_sq(near_term_df,r_near,t_near)
    sigma_sq_next=calculate_sigma_sq(next_term_df,r_next,t_next)

    first_term=t_near*sigma_sq_near*((next_term_mins-CMT_mins)/(next_term_mins-near_term_mins))
    second_term=t_next*sigma_sq_next*((CMT_mins-near_term_mins)/(next_term_mins-near_term_mins))
    sigma=np.sqrt((first_term+second_term)*(mins_in_year/CMT_mins))*100
    #CMT_mins
    #near_term_mins
    #next_term_mins
    #mins_in_year
    #print(current_date)
    return sigma


def vix_main_func(df):
    print('__selecting options__')
    df2=filter_option_types_and_expirations(df)
    df3=add_expiration_time(df2)
    df5=df3.copy() #skipping to df5
    df5['time_to_exp']=df5['ex_time']-df5['datetime_close']
    df5['midpoint_price']=(df5.best_bid+df5.best_offer)/2
    df5['strike_price']/=1000
    vix_dict={}
    excl_dates=[]
    print('__calculating daily VIX__')
    for day_i in df5.date.unique():
        #print(str(day_i.date()))
        day_df_i=df5[df5.date==str(day_i.date())]
        try:
            sigma=calculate_vix_daily(day_df_i)
            #print(sigma)
            vix_dict[str(day_i.date())]=sigma
        except:
            print(f'error with {str(day_i.date())}')
    
    vix_rep_df=pd.DataFrame.from_dict(vix_dict,orient='index')
    vix_rep_df.index.name='Date'
    vix_rep_df.columns=['vix_rep']
    return vix_rep_df

def func1():

    return 1