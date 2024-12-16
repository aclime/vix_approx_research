# https://umd.app.box.com/developers/console/app/2296199/configuration

from boxsdk import Client, OAuth2
from io import StringIO
import pandas as pd
from creds import (token as token, 
                   client_id as client_id, 
                   client_secret as client_secret)

#token='lTzFSbg3fMSb2VIxXWhJQvdJjqu8yxtu'
#auth = OAuth2(
#    client_id='oop3wjglt4mz19180pbnvaatgrjpzmqh',
#    client_secret='YvcSyOLkrjYpV3pdtHirHG92saANuZY0',
#    access_token=token,
#)


def make_client():
    #print(token)
    auth = OAuth2(
        client_id=client_id,
        client_secret=client_secret,
        access_token=token,
    )

    client=Client(auth)
    return client

client=make_client()

def get_folder_id(query='OptionMetrics'):
    #client=make_client()
    om_folder_srch=client.search().query(query=query, type='folder')
    om_folder_id=[item.id for item in om_folder_srch][0]
    return om_folder_id

def upload_to_box(path,name):
    #update file
        #https://github.com/box/box-python-sdk/blob/main/docs/usage/files.md#upload-a-new-version-of-a-file
    om_folder_id=get_folder_id('OptionMetrics')
    #client.folder(om_folder_id).upload(file_path=path,file_name=name) 
    chunked_uploader=client.folder(om_folder_id).get_chunked_uploader(path,name) 
    uploaded_file = chunked_uploader.start()


def pull_data_off_box(periods_dict):
    client=make_client()
    om_folder_srch=client.search().query(query='OptionMetrics', type='folder')
    om_folder_id=[item.id for item in om_folder_srch][0]
    res=client.folder(om_folder_id).get_items(limit=None)

    for r in res:
        file_name=r.name
        year=file_name.split('.')[0].split('_')[1]
        month=file_name.split('.')[0].split('_')[-1]
        for k,v in periods_dict.items():
            #print(v)
            #print(int(v['year']) == year)
            #print(int(v['month']) , month)
            #print('----')
            """
            if (int(v['year'])==int(year)) and (int(v['month'])==int(month)):
                print(year,month)
                with open('test_csv.csv', 'wb') as open_file:
                    r.download_to(open_file)
                    table = pv.read_csv(open_file)
                    open_file.close()
            """
            
            if (int(v['year'])==int(year)) and (int(v['month'])==int(month)):
                file_content = r.content()
                s=str(file_content,'utf-8')
                data = StringIO(s)
                df = pd.read_csv(data)
                #dest=r'vix_approx_research/white_paper_replicate'
                #df.to_csv(rf'{dest}/{r.name}')

