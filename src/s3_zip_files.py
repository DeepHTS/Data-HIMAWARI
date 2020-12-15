import os
import datetime
from tqdm import tqdm
import pandas as pd
from tqdm import tqdm
import shutil
from typing import List, Optional, Tuple, Dict

import rasterio
from rasterio.windows import Window, transform

from src.helper import get_all_file_path_s3, download_from_http, copy_to_s3, argwrapper, imap_unordered_bar


def get_cropped_gtiff(path_img: str, path_out: str, lon: float, lat: float, array_size: Tuple[int, int] = (256, 256),
                      pos: str = 'center', band: Optional[int] = 1) -> None:
    """

    Args:
        path_img (str): image path or url
        path_out (str): saved path on local
        lon (float): longitude
        lat (float): latitude
        array_size (Tuple[int, int]): numpy array size
        pos (str): If 'center', lon and lat are center position in acquired square
        band (Optional[int]): If None, all band.

    Returns:

    """
    # test
    src = rasterio.open(path_img)

    py, px = src.index(lon, lat)
    if pos == 'center':
        px = px - array_size[0] // 2
        py = py - array_size[1] // 2
    window = Window(px, py, array_size[1], array_size[0])
    out_profile = src.profile.copy()

    # temp
    transform_window = transform(window, src.transform)
    out_profile["transform"] = transform_window

    if band is not None:
        clip = src.read(band, window=window)
        out_profile.update(count=1,
                           height=clip.shape[0],
                           width=clip.shape[1])

        with rasterio.open(path_out, 'w', **out_profile) as dst:
            dst.write(clip, 1)
    else:
        clip = src.read(window=window)
        out_profile.update(height=clip.shape[1],
                           width=clip.shape[2])
        with rasterio.open(path_out, 'w', **out_profile) as dst:
            dst.write(clip)

    return


def get_date_from_filename_himawari(filename):
    filename = os.path.basename(filename)
    date_str = filename.split('_')[2]
    return datetime.date(year=int(date_str[:4]), month=int(date_str[4:6]), day=int(date_str[6:]))


# def zip_himawari(dir_parent_s3: str ='data/JAXA_HIMAWARI/gtiff'):
#     image_paths = get_all_file_path_s3(dir_parent=dir_parent_s3, ext_filter=['.tif'])
#     list_dicts = []
#     for path in tqdm(image_paths, total=len(image_paths)):
#         dict_temp = {}
#         dict_temp['date']=get_date_from_filename_himawari(path)
#         dict_temp['path_file'] = path
#     df = pd.DataFrame(list_dicts)
#     print(df)

# todo: below args should be moved to def zip_himawari
def zip_file(list_url, out_file_name, dir_tempfile_head='data/temp', dir_parent_s3='data/JAXA_HIMAWARI/gtiff_zip',
             multiprocessing=False, crop=True, lon=127.8, lat=26.3, array_size=(1028, 1028), band=1):
    dir_dst = os.path.join(dir_tempfile_head, out_file_name)
    list_local_temp_url = []
    for url in list_url:
        path_local = download_from_http(url_src=url, dir_dst=dir_dst)
        if crop:
            get_cropped_gtiff(path_img=path_local,
                              path_out=path_local,
                              lon=lon, lat=lat, array_size=array_size, band=band)
        list_local_temp_url.append(path_local)
    shutil.make_archive(dir_dst, 'zip', dir_dst)
    path_zip = dir_dst + '.zip'
    dir_dst_s3 = os.path.join(dir_parent_s3, os.path.basename(path_zip))

    copy_to_s3(path_zip, path_dst_s3=dir_dst_s3, overwrite=False, remove_local_file=True,
               multiprocessing=multiprocessing)
    shutil.rmtree(dir_dst)
    return


def zip_himawari(df: pd.DataFrame, col_datetime: str = 'observation_start_datetime', col_path: str = 'url_s3',
                 interval_days: int = 7, interval_min=30, processes=1):
    col_doy = 'doy'
    col_year = 'year'
    col_group = 'group'
    col_outname = 'out_name'
    df[col_datetime] = pd.to_datetime(df[col_datetime])
    if interval_min is not None:
        sr_bool = df[col_datetime].dt.minute.apply(lambda x: True if x % interval_min == 0 else False)
        df = df[sr_bool]

    df = df.sort_values(by=col_datetime).reset_index(drop=True)
    df[col_doy] = df[col_datetime].apply(lambda x: x.dayofyear)
    df[col_year] = df[col_datetime].apply(lambda x: x.year)
    df[col_group] = df[col_doy].apply(lambda x: x // interval_days)

    df_group = df.groupby(by=[col_year, col_group])[col_path].apply(list).reset_index()

    def name_add(row):
        year = row[col_year]
        date_start = datetime.date(year=year, month=1, day=1) + datetime.timedelta(row[col_group] - 1)
        date_end = datetime.date(year=year, month=1, day=1) + datetime.timedelta(row[col_group] + interval_days - 2)
        if date_end.year != date_start.year:
            date_end = datetime.date(year=year, month=12, day=31)

        return "{0}-{1}".format(date_start.strftime('%Y%m%d'), date_end.strftime('%Y%m%d'))

    df_group[col_outname] = df_group.apply(name_add, axis=1)

    if processes == 1:
        for i, row in tqdm(df_group.iterrows(), total=len(df_group)):
            list_url = row[col_path]
            out_file_name = row[col_outname]
            zip_file(list_url, out_file_name, multiprocessing=False)
    else:
        dir_tempfile_head = 'data/temp'
        dir_parent_s3 = 'data/JAXA_HIMAWARI/gtiff_zip'
        func_args = [(zip_file, row[col_path], row[col_outname], dir_tempfile_head, dir_parent_s3, True) for i, row in
                     df_group.iterrows()]
        urls_src = imap_unordered_bar(argwrapper, func_args, processes, extend=False)

    return


if __name__ == '__main__':
    path = '../data/JAXA_HIMAWARI/gtiff/file_meta_list.csv'
    # path = 'https://nict-ets9.s3-ap-northeast-1.amazonaws.com/data/JAXA_HIMAWARI/gtiff/file_meta_list.csv'
    df = pd.read_csv(path)
    processes = 1
    zip_himawari(df, processes=processes)
