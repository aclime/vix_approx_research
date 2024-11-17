#from db_connection import get_db_connection

def option_metric_query(tick,year,day=None,month=None):
    """get OptonMetrics data from optionm.opprcdyyyy
    where yyyy is taken from the year param
    tick will map to one of the secid's listed below
    if the user specfies an optional day and month, the df will be filtered to 
    include those specfifc days (note this filters on date column on exdate-aka the expiration)"""
    sec_id_map={'DJX':102456, #Dow Jones Industrial Average
    'NDX':102480, #NASDAQ 100 Index
    'MNX':102491, #CBOE Mini-NDX Index
    'XMI':101499, #AMEX Major Market Index
    'SPX':108105, #S&P 500 Index
    'OEX':109764, #S&P 100 Index
    'MID':101507, #S&P Midcap 400 Index
    'SML':102442, #S&P Smallcap 600 Index
    'RUT':102434, #Russell 2000 Index
    'NYZ':107880, #NYSE Composite Index (Old)
    'WSX':108656  #PSE Wilshire Smallcap Index
    }
    #db = get_db_connection()
    req=f"""
    SELECT *
    FROM optionm.opprcd{year} AS tbl 
    WHERE secid = {sec_id_map.get(tick)}
    """
    if month:
        req+=f""" and EXTRACT(MONTH from date)={month}"""
    
    if day:
        req+=f""" and EXTRACT(DAY from date)={day}"""

    #df = db.raw_sql(req)
    #display(df.head())
    return req
    #return df



