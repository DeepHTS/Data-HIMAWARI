import os
import datetime
from tqdm import tqdm

import pandas as pd
import pytz
import boto3

from src.helper import transfer_to_s3

S3_BUCKET_NAME = 'nict-ets9'
FILE_NAME_HEAD = 'file_meta_list'

EXT = ['.h5', '.hdf', '.HDF', '.tif']
DICT_SAT = {
    'H08': 'Himawari-8',
    'H09': 'Himawari-9',
}

DICT_META = {
    'tbb_07': {
        'offset': 273.14999,
        'long_name': 'Brightness temperature of band 07',
        'nodata': -32768,
        'scale': 0.0099999998,
        'unit': 'K'
    },
    'tbb_14': {
        'offset': 273.14999,
        'long_name': 'Brightness temperature of band 14',
        'nodata': -32768,
        'scale': 0.0099999998,
        'unit': 'K'
    },
    'tbb_15': {
        'offset': 273.14999,
        'long_name': 'Brightness temperature of band 15',
        'nodata': -32768,
        'scale': 0.0099999998,
        'unit': 'K'
    },
}


def get_meta_list_himawari(s3_bucket_name, s3_dir_parent):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(s3_bucket_name)
    s3_cl = boto3.client('s3')
    bucket_location = s3_cl.get_bucket_location(Bucket=s3_bucket_name)
    url_s3_head = "https://{0}.s3-{1}.amazonaws.com".format(
        s3_bucket_name,
        bucket_location['LocationConstraint']
    )

    list_dict_meta = []
    for bucket_object in bucket.objects.filter(Prefix=s3_dir_parent):
        path = bucket_object.key
        filename = os.path.basename(path)
        s3_url = os.path.join(url_s3_head, path)
        if os.path.splitext(filename)[-1] not in EXT:
            continue
        filename_part = filename.split('_')
        satellite_name = DICT_SAT[filename_part[1]]
        observation_start_datetime = datetime.datetime.strptime(filename_part[2] + filename_part[3],
                                                                '%Y%m%d%H%M').replace(tzinfo=pytz.utc)
        cover_area = filename_part[4]
        band_name = filename_part[7] + '_' + filename_part[8]
        offset = DICT_META[band_name]['offset']
        long_name = DICT_META[band_name]['long_name']
        nodata = DICT_META[band_name]['nodata']
        scale = DICT_META[band_name]['scale']
        unit = DICT_META[band_name]['unit']
        dict_info = {
            'filename': filename,
            'satellite_name': satellite_name,
            'observation_start_datetime': observation_start_datetime,
            'cover_area': cover_area,
            'band_name': band_name,
            'offset': offset,
            'long_name': long_name,
            'nodata': nodata,
            'scale': scale,
            'unit': unit,
            'url_s3': s3_url
        }
        list_dict_meta.append(dict_info)
    if len(list_dict_meta) == 0:
        return None
    df = pd.DataFrame(list_dict_meta)
    return df


def main():
    s3_dir_parent = 'data/JAXA_HIMAWARI/gtiff'

    if not os.path.exists(s3_dir_parent):
        os.makedirs(s3_dir_parent)

    df = get_meta_list_himawari(S3_BUCKET_NAME, s3_dir_parent)
    path_local_csv = os.path.join(s3_dir_parent, FILE_NAME_HEAD + '.csv')
    df.to_csv(path_local_csv, index=False)
    print(path_local_csv)
    url_s3 = transfer_to_s3(path_local=path_local_csv,
                            dir_local_parent=s3_dir_parent,
                            dir_s3_parent=s3_dir_parent,
                            remove_local_file=False,
                            multiprocessing=False,
                            s3_bucket_name=S3_BUCKET_NAME)
    print(url_s3)


if __name__ == "__main__":
    main()
