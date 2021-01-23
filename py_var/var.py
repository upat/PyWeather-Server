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

# 気象庁 名古屋アメダス
jma_url	  = "https://www.jma.go.jp/jp/amedas_h/today-51106.html?areaCode=000&groupCode=36"
# ウェザーニュース 名古屋市中区(HTML版)
wnews_url = "https://weathernews.jp/onebox/35.1802/136.9067/temp=c&lang=ja"

# マイコン向け変数(IP+PORT)
# SSD1306+ESP8266用
udp_addr1 = '192.168.0.13'
udp_port1 = 9000
# ILI9341+ESP32用
udp_addr2 = '192.168.0.14'
udp_port2 = 9200
