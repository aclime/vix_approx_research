#from db_connection import get_db_connection

def cboe_vix__query(ticks,start=None,end=None):
    """get CBOE VIX data
        column labels are as follows
        Variable Name	Type	Description
        date	Date	Date (date)
        vixo	Decimal	CBOE S&P500 Volatility Index - Open (vixo)
        vixh	Decimal	CBOE S&P500 Volatility Index - High (vixh)
        vixl	Decimal	CBOE S&P500 Volatility Index - Low (vixl)
        vix	    Decimal	CBOE S&P500 Volatility Index - Close (vix)
        vxoo	Decimal	CBOE S&P100 Volatility Index - Open (vxoo)
        vxoh	Decimal	CBOE S&P100 Volatility Index - High (vxoh)
        vxol	Decimal	CBOE S&P100 Volatility Index - Low (vxol)
        vxo	    Decimal	CBOE S&P100 Volatility Index - Close (vxo)
        vxno	Decimal	CBOE NASDAQ Volatility Index - Open (vxno)
        vxnh	Decimal	CBOE NASDAQ Volatility Index - High (vxnh)
        vxnl	Decimal	CBOE NASDAQ Volatility Index - Low (vxnl)
        vxn	    Decimal	CBOE NASDAQ Volatility Index - Close (vxn)
        vxdo	Decimal	CBOE DJIA Volatility Index - Open (vxdo)
        vxdh	Decimal	CBOE DJIA Volatility Index - High (vxdh)
        vxdl	Decimal	CBOE DJIA Volatility Index - Low (vxdl)
        vxd	    Decimal	CBOE DJIA Volatility Index - Close (vxd)
        """
    
    #db = get_db_connection()

    def flatten(xss):
        return [x for xs in xss for x in xs]
    col_list=[ [tick+branch for branch in ['','o','h','l']] for tick in ticks]
    col_list=flatten(col_list)


    req=f"""
    SELECT date, {str(col_list).replace('[','').replace(']','').replace("'",'')}
    FROM cboe.cboe AS tbl 
    WHERE 1=1 
    """
    if start:
        req+=f""" and date >= '{start}'"""
    
    if end:
        req+=f""" and date <= '{end}'"""

    #print(req)
    #df = db.raw_sql(req)
    #display(df.head())
    #return req
    #return df
    return req



