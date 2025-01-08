#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import configparser
# import jqdatasdk
import os

class DataFeed(object):
    def __init__(self, config_path, local_data_dir):
        self.is_jq_auth = False
        self.config_path = config_path
        self.local_data_dir = local_data_dir

#     def _auth_jq(self):
#         if not self.is_jq_auth:
#             config = configparser.ConfigParser()
#             config.read(self.config_path)
#             user, passwd = config.get('joinquant', 'user'), \
#                            config.get('joinquant', 'passwd')

#             jqdatasdk.auth(user, passwd)

#             count = jqdatasdk.get_query_count()
#             print('Data Query Amount: ', count)
#             self.is_jq_auth = True

    def query_tushare_data(self):
        """ 查询 Tushare 的数据 """
        pass

    def query_joinquant_data(self, security, start, end, freq):
        """ 查询 Joinquant 的数据 """
        # self._auth_jq()
        data = get_price(security, start_date=start, end_date=end,
                                   frequency=freq, fields=None, skip_paused=False,
                                   fq='pre', panel=True)
        data['date'] = data.index.to_series().apply(lambda x: str(x)[:10])
        if freq == 'daily':
            data['time'] = '23:59:59'
        else:
            data['time'] = data.index.to_series().apply(lambda x: str(x)[11:])
        data = data.reset_index(drop=True)
        print('下载完成~ 数据条数:{}, first_dt:{} {}, last_dt: {} {}'.format( data.shape[0],
                                                                           data['date'].values[0],
                                                                           data['time'].values[0],
                                                                           data['date'].values[-1],
                                                                           data['time'].values[-1]
                                                                           ))
        return data

    def query_jq_data_save_local(self, security, start, end, freq):
        """ 查询joinquant数据并保存到本地 """
        print('开始查询JoinQuant数据~')
        jq_data = self.query_joinquant_data(security, start, end, freq)
        print('数据查询成功，开始保存到本地~')
        if self.save_data_to_local(jq_data, security, freq):
            print('文件已成功保存到本地~')

    def get_local_data_path(self, security):
        """ 获取Local Data File的Path """
        local_data_path = os.path.join(self.local_data_dir, '{}.h5'.format(security))
        return local_data_path

    def get_local_data_keys(self, security):
        """ 查询Local Data File的keys """
        local_data_path = self.get_local_data_path(security)
        if not os.path.exists(local_data_path):
            print('未找到对应Local Data File：{}'.format(local_data_path))
            return
        else:
            store = pd.HDFStore(local_data_path)
            store_keys = store.keys()
            store.close()
            return store_keys

    def save_data_to_local(self, data, security, freq):
        """ 保存数据到本地 """
        local_data_path = self.get_local_data_path(security)
        if os.path.exists(local_data_path):
            print('本地已有Local Data File：{}'.format(local_data_path))
            local_data_keys = self.get_local_data_keys(security)
            print(local_data_keys)
            if '/{}'.format(freq) in local_data_keys:
                print('Local Data中已存在对应分区：{}，将更新文件'.format(freq))
                pre_data = self.load_local_data(security, freq)
                new_data = pd.concat([pre_data, data])
                new_data = new_data.drop_duplicates(['date','time']).sort_values(['date', 'time'])
                new_data.reset_index(drop=True, inplace=True)
            else:
                print('Local Data中未找到对应分区：{}，将新建文件'.format(freq))
                new_data = data
        else:
            print('本地未找到Local Data File：{}，将新建'.format(local_data_path))
            new_data = data
        # 保存文件到HDFS文件的freq分区
        new_data.to_hdf(local_data_path, freq)
        return True

    def load_local_data(self, security, freq,
                              str_datetime_start=None, str_datetime_end=None):
        """ 加载本地数据 """
        local_data_path = self.get_local_data_path(security)
        local_data_keys = self.get_local_data_keys(security)
        if '/{}'.format(freq) not in local_data_keys:
            print('未在local data file中找到对应分区:{}'.format(freq))
            return
        else:
            data = pd.read_hdf(local_data_path, freq)
            if str_datetime_start:
                dt_s = pd.Series(['{} {}'.format(d, t) for d, t in zip(data['date'], data['time'])])
                data = data[dt_s >= str_datetime_start]
            if str_datetime_end:
                dt_s = pd.Series(['{} {}'.format(d, t) for d, t in zip(data['date'], data['time'])])
                data = data[dt_s <= str_datetime_end]
            if str_datetime_start or str_datetime_end:
                data = data.sort_values(['date', 'time']).reset_index(drop=True)
            print('数据加载完成~ \n'
                  'first_dt:{} {}, \n'
                  'last_dt:{} {}'.format(data['date'].values[0],
                                         data['time'].values[0],
                                         data['date'].values[-1],
                                         data['time'].values[-1]
                                        ))
            return data

if __name__ == '__main__':
    datafeed = DataFeed(config_path='../quantitative_research_report',
                        local_data_dir='../quantitative_research_report/data')
    """ 下载joinquant数据到本地 """
    datafeed.query_jq_data_save_local('000300.XSHG',
                                     '2020-12-01', '2022-01-31',
                                     'daily')
    """ 读取本地数据 """
    data = datafeed.load_local_data('000300.XSHG', 'daily')
    print(data.head())
