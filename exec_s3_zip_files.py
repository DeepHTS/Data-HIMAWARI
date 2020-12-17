import pandas as pd
from src.s3_zip_files import zip_himawari
import datetime, pytz


if __name__ == '__main__':
    # path = '../data/JAXA_HIMAWARI/gtiff/file_meta_list.csv'
    path = 'https://nict-ets9.s3-ap-northeast-1.amazonaws.com/data/JAXA_HIMAWARI/gtiff/file_meta_list.csv'
    df = pd.read_csv(path)
    processes = 14
    start_datetime = datetime.datetime(year=2018, month=1, day=1, tzinfo=pytz.utc)
    zip_himawari(df, processes=processes, start_datetime=start_datetime)
