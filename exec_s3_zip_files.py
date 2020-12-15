import pandas as pd
from src.s3_zip_files import zip_himawari


if __name__ == '__main__':
    # path = '../data/JAXA_HIMAWARI/gtiff/file_meta_list.csv'
    path = 'https://nict-ets9.s3-ap-northeast-1.amazonaws.com/data/JAXA_HIMAWARI/gtiff/file_meta_list.csv'
    df = pd.read_csv(path)
    processes = 12
    zip_himawari(df, processes=processes)
