import os
import datetime
from ftplib import FTP
import ftplib
from tqdm import tqdm

from src.helper import argwrapper, imap_unordered_bar

JAXA_FTP = os.getenv('JAXA_FTP')
JAXA_USER = os.getenv('JAXA_USER')
JAXA_PASSWORD = os.getenv('JAXA_PASSWORD')

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

def date_to_path(date, product):
    return os.path.join(product.replace('.', '/'), date.strftime('%Y%m'), date.strftime('%d'))


def filename_filter(path, datatype=None, product='jma.netcdf', ext='.nc'):
    if type(datatype) != list:
        datatype = [datatype]
    if type(ext) != list:
        ext = [ext]
    path_ext = os.path.splitext(path)[-1]
    if path_ext not in ext:
        return False

    filename = os.path.basename(path)
    if product == 'jma.netcdf':
        path_datatype = filename.split('_')[4]
        if path_datatype not in datatype:
            return False
    else:
        print('need criteria for product=', product)

    return True


def get_ftp_path(ftp_dir, datatype=None, product='jma.netcdf', ext='.nc'):
    try:
        list_ftp_path = ftp.nlst(ftp_dir)
        list_ftp_path = [ftp_path for ftp_path in list_ftp_path if filename_filter(ftp_path,
                                                                                   datatype=datatype,
                                                                                   product=product,
                                                                                   ext=ext)]
    except ftplib.error_temp:
        print(ftp_dir, ' does not exist')
        return []
    return list_ftp_path


def search_ftp_path(date_start, date_stop, datatype=None, product='jma.netcdf', processes=1):
    # date_start = datetime_start.date()
    # date_stop = datetime_stop.date()
    date_dif = date_stop - date_start
    list_date = [date_start + datetime.timedelta(days=day) for day in range(date_dif.days + 1)]
    list_ftp_dir = [date_to_path(date, product) for date in list_date]

    if processes == 1:
        list_ftp_path = []
        global ftp
        ftp = FTP(JAXA_FTP, user=JAXA_USER, passwd=JAXA_PASSWORD)
        for ftp_dir in tqdm(list_ftp_dir, total=len(list_ftp_dir)):
            list_ftp_path.extend(get_ftp_path(ftp_dir,
                                              datatype=datatype,
                                              product=product))
    else:
        credentials = [JAXA_FTP, JAXA_USER, JAXA_PASSWORD]
        init(*credentials)
        func_args = [(get_ftp_path, ftp_dir, datatype, product) for ftp_dir in list_ftp_dir]
        list_ftp_path = imap_unordered_bar(argwrapper, func_args, processes, extend=True, init=init,
                                           credentials=credentials)

    return list_ftp_path


def main():
    date_start = datetime.datetime(year=2015, month=7, day=12)
    date_stop = datetime.datetime(year=2015, month=7, day=16)
    datatype = 'r14'
    product = 'jma.netcdf'
    processes = 3

    list_ftp_path = search_ftp_path(date_start=date_start,
                                    date_stop=date_stop,
                                    datatype=datatype,
                                    product=product,
                                    processes=processes)
    print(list_ftp_path)


if __name__ == "__main__":
    main()
