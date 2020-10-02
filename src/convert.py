import os
from copy import deepcopy
from ftplib import FTP
import datetime
from tqdm import tqdm
import urllib


import numpy as np
from osgeo import gdal, osr
import rasterio
from rasterio.mask import mask
from shapely.geometry import box
from fiona.crs import from_epsg
import geopandas as gpd

ESPG_GRID = 4326
DICT_GDT = {
    'uint16': gdal.GDT_UInt16,
    'uint8': gdal.GDT_Byte,
    'complex64': gdal.GDT_CFloat64,
    'float32': gdal.GDT_Float32,
    'float64': gdal.GDT_Float64,
    'int16': gdal.GDT_Int16,
    'int32': gdal.GDT_Int32,
    'uint32': gdal.GDT_UInt32,
}


def get_layer_name(path_local):
    hdf_ds = gdal.Open(path_local)
    try:
        sub_datasets = hdf_ds.GetSubDatasets()
    except AttributeError:
        print("can't open sub datasets by GDAL \n {}".format(path_local))
        return
    return [dataset[0].split(':')[-1] for dataset in sub_datasets]


def get_tup_transform(dict_meta, file_type='jma'):
    if file_type == 'jma':
        resolution = float(dict_meta['NC_GLOBAL#grid_interval'])
        uly = float(dict_meta['NC_GLOBAL#upper_left_latitude'])
        ulx = float(dict_meta['NC_GLOBAL#upper_left_longitude'])
    else:
        return

    return (ulx, resolution, 0.0, uly, 0.0, resolution * -1.0)


def add_meta_data(path_grid, dict_meta, layer_name, file_type='jma'):
    dict_meta_info = {
        'path_local': path_grid,
        'layer': layer_name,
    }
    if file_type == 'jma':
        offsets = float(dict_meta['{0}#{1}'.format(layer_name, 'add_offset')])
        long_name = dict_meta['{0}#{1}'.format(layer_name, 'long_name')]
        nodata = int(dict_meta['{0}#{1}'.format(layer_name, 'missing_value')])
        scales = float(dict_meta['{0}#{1}'.format(layer_name, 'scale_factor')])
        unit_name = dict_meta['{0}#{1}'.format(layer_name, 'units')]
        # valid_max = int(dict_meta['{0}#{1}'.format(layer_name, 'valid_max')])
        # valid_min = int(dict_meta['{0}#{1}'.format(layer_name, 'valid_min')])

        with rasterio.open(path_grid, 'r+') as src:
            src.offsets = (offsets,)
            src.descriptions = (long_name,)
            src.nodata = nodata
            src.scales = (scales,)
            src.units = (unit_name,)

        dict_meta_info.update(
            offset=offsets,
            long_name=long_name,
            nodata=nodata,
            scale=scales,
            unit=unit_name
        )
    return dict_meta_info


def get_single_layer_gtiff(path_local, layer_name=None, dir_save=None, dict_meta_info_raw=None):
    espg_grid = int(ESPG_GRID)
    dict_gdt = DICT_GDT

    filename_head = os.path.splitext(os.path.basename(path_local))[0]

    hdf_ds = gdal.Open(path_local)
    try:
        sub_datasets = hdf_ds.GetSubDatasets()
    except AttributeError:
        print("can't open sub datasets by GDAL \n {}".format(path_local))
        return

    list_dict_meta_info = []
    for dataset in sub_datasets:
        layer = dataset[0].split(':')[-1]

        if (layer_name is not None) and (layer not in layer_name):
            continue

        band_ds = gdal.Open(dataset[0], gdal.GA_ReadOnly)
        band_array = band_ds.ReadAsArray()
        # todo: check left log
        try:
            data_type = band_array.dtype.name
        except AttributeError:
            print('nodata', path_local)
            continue

        # band_array = np.flipud(band_array.T)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(espg_grid)

        dict_meta = band_ds.GetMetadata()
        tup_transform = get_tup_transform(dict_meta, file_type='jma')

        filename_grid = filename_head + '_' + layer + '_4326.tif'
        path_grid = os.path.join(dir_save, filename_grid)

        out_ds = gdal.GetDriverByName('GTiff').Create(path_grid,
                                                      band_ds.RasterXSize,
                                                      band_ds.RasterYSize,
                                                      1,  # Number of bands
                                                      dict_gdt.get(data_type, gdal.GDT_Unknown),
                                                      ['TILED=YES'])
        out_ds.SetGeoTransform(tup_transform)
        out_ds.SetProjection(srs.ExportToWkt())
        out_ds.GetRasterBand(1).WriteArray(band_array)
        out_ds.FlushCache()
        out_ds = None

        dict_meta_info = add_meta_data(path_grid, dict_meta, layer, file_type='jma')
        if dict_meta_info_raw is not None:
            dict_meta_info_raw.update(dict_meta_info)
            dict_meta_info = deepcopy(dict_meta_info_raw)

        list_dict_meta_info.append(dict_meta_info)

    return list_dict_meta_info


def main():
    path_local = 'notebook/data/NC_H08_20160714_0000_r14_FLDK.02701_02601.nc'
    list_layer = get_layer_name(path_local)
    print(list_layer)
    list_dict_meta_info = get_single_layer_gtiff(path_local, layer_name=None, dir_save='notebook/data')
    print(list_dict_meta_info)

if __name__ == "__main__":
    main()
# todo: upload to s3 in new def