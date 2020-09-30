import os
import datetime
from ftplib import FTP
import ftplib
from tqdm import tqdm
import urllib
import pytz
from copy import deepcopy

import numpy as np
import pandas as pd

from src.search import search_ftp_path
from src.convert import get_single_layer_gtiff
from src.helper import transfer_to_s3, argwrapper, imap_unordered_bar, get_s3_url_head, update_data_list_df

import warnings
warnings.filterwarnings('ignore')

DIR_PARENT_RAW_LOCAL = 'data/JAXA_HIMAWARI/netcdf'
DIR_PARENT_CONVERTED_LOCAL = 'data/JAXA_HIMAWARI/gtiff'
DIR_PARENT_RAW_S3 = 'data/JAXA_HIMAWARI/netcdf'
DIR_PARENT_CONVERTED_S3 = 'data/JAXA_HIMAWARI/gtiff'

JAXA_FTP = os.getenv('JAXA_FTP')
JAXA_USER = os.getenv('JAXA_USER')
JAXA_PASSWORD = os.getenv('JAXA_PASSWORD')

S3_BUCKET_NAME = 'nict-ets9'

DICT_SATELLITE_NAME = {
    'H08': 'Himawari-8',
    'H09': 'Himawari-9'
}

DICT_SPATIAL_RESOLUTION = {
    '05': '0.5 km',
    '10': '1 km',
    '20': '2 km',
}

FILENAME_LIST = 'list_himawari.csv'

def init(*credentials):
    """ set variable of FTP connection as global variable for multiprocessing

    Args:
        *credentials (): [ftp address, user name, password] (for JAXA, 'anonymous' is OK)

    Returns:

    """
    global ftp
    server, user, password = credentials
    ftp = FTP(server)
    ftp.login(user=user, passwd=password)


class DataManagerJaxaHimawari(object):
    def __init__(self,
                 dir_parent_raw_local=DIR_PARENT_RAW_LOCAL,
                 dir_parent_converted_local=DIR_PARENT_CONVERTED_LOCAL,
                 dir_parent_raw_s3=DIR_PARENT_RAW_S3,
                 dir_parent_converted_s3=DIR_PARENT_CONVERTED_S3,
                 s3_bucket_name=S3_BUCKET_NAME,
                 processes=1):

        self.dir_parent_raw_local = dir_parent_raw_local
        self.dir_parent_converted_local = dir_parent_converted_local
        self.dir_parent_raw_s3 = dir_parent_raw_s3
        self.dir_parent_converted_s3 = dir_parent_converted_s3
        self.processes = processes
        self.s3_bucket_name = s3_bucket_name
        self.list_meta_raw = []
        # self.list_dict_meta_info_raw = []
        self.list_dict_meta_info_converted = []

    def _makedirs_from_ftp_path(self, list_ftp_path, convert_to_gtiff=True):
        list_dirs = []
        for path_ftp in list_ftp_path:
            path_local = os.path.join(self.dir_parent_raw_local, path_ftp)
            list_dirs.append(os.path.dirname(path_local))

            if convert_to_gtiff:
                dir_converted_local = os.path.join(self.dir_parent_converted_local,
                                                   os.path.dirname(path_local).split(self.dir_parent_raw_local)[-1][1:])
                list_dirs.append(dir_converted_local)
        list_dirs_unique = list(np.unique(list_dirs))

        for dir in list_dirs_unique:
            if not os.path.exists(dir):
                os.makedirs(dir)
        return

    def download_from_ftp(self, path_ftp):
        path_local = os.path.join(self.dir_parent_raw_local, path_ftp)

        # make dir
        dir_local = os.path.dirname(path_local)
        if not os.path.exists(dir_local):
            os.makedirs(dir_local)

        try:
            with open(path_local, 'wb') as f:
                ftp.retrbinary('RETR {0}'.format(path_ftp), f.write)
        except (urllib.error.URLError, FileNotFoundError) as e:
            print('FAILED: {0}'.format(path_ftp))

        return path_local

    def get_dict_meta_info_from_filename(self, path_local, product):
        dict_meta_info = {
            'path_local': path_local,
        }
        if product == 'jma.netcdf':
            filename = os.path.basename(path_local)
            list_element = filename.split('_')
            dict_meta_info.update(
                satellite_name=DICT_SATELLITE_NAME.get(list_element[1]),
                observation_start_datetime=datetime.datetime.strptime(list_element[2] + '_' + list_element[3],
                                                                      '%Y%m%d_%H%M').replace(tzinfo=pytz.utc),
                layer_name=list_element[3]
            )
        return dict_meta_info

    def exec_get_raster(self, ftp_path, convert_to_gtiff, product, layer_name, save_s3=False, remove_local_files=False):
        path_local = self.download_from_ftp(ftp_path)
        dict_meta_info_raw = self.get_dict_meta_info_from_filename(path_local, product)

        # convert to gtiff
        if convert_to_gtiff:
            list_dict_meta_info_converted = get_single_layer_gtiff(path_local, layer_name=layer_name,
                                                                   dir_save=self.dir_parent_converted_local)
        else:
            list_dict_meta_info_converted = {}

        # save_s3
        if save_s3:
            url_s3 = transfer_to_s3(path_local, dir_local_parent=self.dir_parent_raw_local,
                                    dir_s3_parent=self.dir_parent_raw_s3,
                                    remove_local_file=remove_local_files,
                                    multiprocessing=self.processes > 1, s3_bucket_name=self.s3_bucket_name)
            dict_meta_info_raw['url_s3'] = url_s3
            if remove_local_files:
                dict_meta_info_raw['path_local'] = None

            list_dict_meta_info_converted_out = []
            if len(list_dict_meta_info_converted) > 0:
                for dict_meta_info_converted in list_dict_meta_info_converted:
                    path_converted = dict_meta_info_converted['path_local']
                    url_s3 = transfer_to_s3(path_converted, dir_local_parent=self.dir_parent_converted_local,
                                            dir_s3_parent=self.dir_parent_converted_s3,
                                            remove_local_file=remove_local_files,
                                            multiprocessing=self.processes > 1, s3_bucket_name=self.s3_bucket_name)
                    dict_meta_info_converted['url_s3'] = url_s3
                    if remove_local_files:
                        dict_meta_info_converted['path_local'] = None
                    list_dict_meta_info_converted_out.append(dict_meta_info_converted)
                list_dict_meta_info_converted = deepcopy(list_dict_meta_info_converted_out)
        return list_dict_meta_info_converted

    def get_raster_data(self,
                        date_start,
                        date_stop,
                        datatype=None,
                        layer_name=None,
                        product='jma.netcdf',
                        convert_to_gtiff=True,
                        save_s3=False,
                        remove_local_files=False):
        list_ftp_path = search_ftp_path(date_start=date_start,
                                        date_stop=date_stop,
                                        datatype=datatype,
                                        product=product,
                                        processes=self.processes)
        # make dirs
        self._makedirs_from_ftp_path(list_ftp_path, convert_to_gtiff=convert_to_gtiff)

        if self.processes == 1:
            list_dict_meta_info_converted_out = []
            global ftp
            ftp = FTP(JAXA_FTP, user=JAXA_USER, passwd=JAXA_PASSWORD)
            for ftp_path in tqdm(list_ftp_path, total=len(list_ftp_path)):
                list_dict_meta_info_converted = self.exec_get_raster(ftp_path,
                                                                     convert_to_gtiff,
                                                                     product,
                                                                     layer_name,
                                                                     save_s3=save_s3,
                                                                     remove_local_files=remove_local_files)
                list_dict_meta_info_converted_out.extend(list_dict_meta_info_converted)
        else:
            credentials = [JAXA_FTP, JAXA_USER, JAXA_PASSWORD]
            init(*credentials)
            func_args = [(self.exec_get_raster, ftp_dir, convert_to_gtiff, product, layer_name, save_s3,
                          remove_local_files) for ftp_dir in list_ftp_path]
            list_dict_meta_info_converted_out = imap_unordered_bar(argwrapper, func_args, self.processes, extend=True,
                                                                   init=init,
                                                                   credentials=credentials)

        self.list_dict_meta_info_converted.extend(list_dict_meta_info_converted_out)
        return list_dict_meta_info_converted_out

    def save_list(self, filename_list=FILENAME_LIST):
        df_meta_info = pd.DataFrame(self.list_dict_meta_info_converted)

        url_s3_head = get_s3_url_head(self.s3_bucket_name)
        url_s3 = os.path.join(url_s3_head, filename_list)
        df_record_s3 = update_data_list_df(path_org=url_s3, df_new=df_meta_info)

        # save local
        path_record_local = os.path.join(self.dir_parent_converted_local, filename_list)

        df_record_s3.to_csv(path_record_local, index=False)
        transfer_to_s3(path_local=path_record_local, dir_local_parent=self.dir_parent_converted_local,
                       dir_s3_parent=self.dir_parent_converted_s3, remove_local_file=False, multiprocessing=False,
                       s3_bucket_name=self.s3_bucket_name)

        return df_record_s3


def main():
    date_start = datetime.datetime(year=2015, month=7, day=12)
    date_stop = datetime.datetime(year=2015, month=7, day=14)
    datatype = 'r14'
    product = 'jma.netcdf'
    layer_name = ['tbb_07', 'tbb_14', 'tbb_15'] #None #['tbb_07', 'tbb_14', 'tbb_15']
    convert_to_gtiff = True
    save_s3 = True
    remove_local_files = True
    processes = 15

    data_manager_jaxa_himawari = DataManagerJaxaHimawari(processes=processes)
    data_manager_jaxa_himawari.get_raster_data(date_start=date_start,
                                               date_stop=date_stop,
                                               datatype=datatype,
                                               layer_name=layer_name,
                                               product=product,
                                               convert_to_gtiff=convert_to_gtiff,
                                               save_s3=save_s3,
                                               remove_local_files=remove_local_files
                                               )
    data_manager_jaxa_himawari.save_list()

if __name__ == "__main__":
    main()
