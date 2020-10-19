import datetime

from src.download import DataManagerJaxaHimawari

def main():
    date_start = datetime.datetime(year=2019, month=1, day=1)
    date_stop = datetime.datetime(year=2019, month=1, day=15)
    datatype = 'r14'
    product = 'jma.netcdf'
    layer_name = ['tbb_07', 'tbb_14', 'tbb_15'] #None #['tbb_07', 'tbb_14', 'tbb_15']
    convert_to_gtiff = True
    save_s3 = True
    remove_local_files = True
    processes = 13

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
