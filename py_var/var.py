#!/usr/bin/env python3
# coding: UTF-8

# TwitterAPIキー
CK  = ''
CS  = ''
AT  = ''
ATS = ''
# TwitterAPIエンドポイント
url_text = 'https://api.twitter.com/1.1/statuses/update.json'

# 各種データ保存用ファイルパス(使用環境によって適宜変更)
logtxt_path = r'log/python_log.txt' # 処理ログファイルパス
log_path    = r'log'                # 処理ログフォルダパス
wnews_path  = r'json/wnews.json'    # ウェザーニュースデータファイルパス
dlist_path  = r'json/datelist.json' # 日時データファイルパス
json_path   = r'json'               # jsonフォルダパス
jma_path    = r'json/jma.json'      # 気象庁データファイルパス

# 気象庁 東京アメダス
jma_url	  = "https://www.jma.go.jp/bosai/amedas/#area_type=offices&area_code=130000&amdno=44132&format=table1h"
# ウェザーニュース 東京都新宿区(HTML版)
wnews_url = "https://weathernews.jp/onebox/35.6904811111111/139.706551111111/"
