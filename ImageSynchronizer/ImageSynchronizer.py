#!/usr/bin/env python
# coding: utf-8

# In[162]:


import sys, glob, os
import pandas as pd
from smb.SMBConnection import SMBConnection
import numpy as np
import json
import cv2
import matplotlib.pyplot as plt
import shutil
import xml.etree.ElementTree as ET
import socket
import pyodbc
from IPython.display import clear_output
from tqdm import tqdm


class connectOpt():
    def __init__(self, server, database, username, password):
        # connect to sql db
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.reloadDB_content()
    def connectDB(self):
        # print("Connecting to Azure database....")
        cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+self.server+';DATABASE='+self.database+';UID='+self.username+';PWD='+self.password)
        self.cursor = cnxn.cursor()
        
    def reloadDB_content(self):
        self.connectDB()
        # get datasets detail
        self.cursor.execute("sp_columns main")
        datasets_cname = [i[3] for i in self.cursor.fetchall()]
        self.cursor.execute("SELECT * FROM main")
        row = self.cursor.fetchall()
        self.datasetsInfo = pd.DataFrame([list(i) for i in row],columns=datasets_cname)
        # Set dataframe style
        self.datasetsInfo = self.datasetsInfo.sort_values(by=['datasetID']).reset_index(drop=True)#.style.set_properties(**{'text-align':'left'}).set_table_styles([dict(selector='th', props=[('text-align', 'left')])])
        # get storageinfo detail
        self.cursor.execute("sp_columns storageinfo")
        storageinfo_cname = [i[3] for i in self.cursor.fetchall()]
        self.cursor.execute("SELECT * FROM storageinfo")
        row = self.cursor.fetchall()
        self.__storageinfo_dict = {k:v for k,v in zip(storageinfo_cname,row[0])}       
        self.cursor.close()
        
    def connectStorage(self):
        try:
            name, alias, addresslist = socket.gethostbyaddr(self.__storageinfo_dict['connect_address'])
        except socket.herror:
            name, alias, addresslist = 'None', 'None', 'None'
        if self.__storageinfo_dict['connect_type'] == 'smb':
            self.__main_folder = self.__storageinfo_dict['storage_path']
            self.conn = SMBConnection(self.__storageinfo_dict['connect_username'], self.__storageinfo_dict['connect_password'], 'py_user',name)
        try:
            print("Connecting to data storage...")
            self.conn.connect(self.__storageinfo_dict['connect_address'])
        except ConnectionRefusedError:
            print("Connection failed. Please contact to manager.") 
    
    def list_dsFiles_from_storage(self,dsID):
        _files = self.conn.listPath(self.__main_folder, os.path.join("ImageSynchronizer", dsID))
        _filenames = [i.filename for i in _files if i.filename not in [".",".."]] 
        _filenames.sort(reverse=False)
        return _filenames
        
    def list_dsFiles_from_SQL(self,dsID):
        print(f"Retrieving files from SQL...")
        self.connectDB()
        sql = f"SELECT file_name FROM [{dsID}]"
        self.cursor.execute(sql)
        row = self.cursor.fetchall()
        self.cursor.close()
        _filenames = [i[0] for i in row]
        _filenames.sort(reverse=False)
        print(f"Found {len(_filenames)} files.")
        return _filenames
        
    def retrieve(self, dsID, target_path, amount = None):
        ds_dir = os.path.join(target_path, dsID)
        if not os.path.exists(ds_dir):
            os.makedirs(ds_dir)
        _exists_files = [os.path.basename(i) for i in glob.glob(os.path.join(ds_dir, "*.*"))]
        _filenames = self.list_dsFiles_from_SQL(dsID)
        print("Checking exist files......")
        _filenames = [i for i in tqdm(_filenames) if i not in _exists_files]
        if len(_filenames)==0:
            return None
        self.connectStorage()
        for j,i in enumerate(_filenames):
            clear_output(wait=True)
            if amount is not None:
                print(f"Syncing files : {dsID} - {j+1}/{amount*2}\n")
            else:
                print(f"Syncing files : {dsID} - {j+1}/{len(_filenames)}\n")
            _target_filename = os.path.join(ds_dir, i)
            with open(_target_filename, 'wb') as f:
                self.conn.retrieveFile(self.__main_folder, os.path.join("ImageSynchronizer", dsID, i), f)
            if amount is not None:
                if j+1==amount*2:
                    break
        self.conn.close()
        return None



class synchronizer(connectOpt):
    def __init__(self, server, database, username, password):
        super().__init__(server, database, username, password)
        self.__subscribe_run = False
    
    def subscribe(self, datasets=None):
        # datasets : list, dataset ID that want to be subscribed
        self.__subscribe_run = True
        self.datasetsInfo_subscribed = self.datasetsInfo[self.datasetsInfo['datasetID'].isin(datasets)]
        
    def update_subscription(self, target_path, amount=None):
        if not self.__subscribe_run:
            print("subscribe method hasn't been called yet.")
            return None
        datasetID_selected = self.datasetsInfo_subscribed['datasetID']
        print("Checking dataset status...")
        for dsID in datasetID_selected:
            self.retrieve(dsID, target_path, amount)
        print(f"Synchronization complete!")

