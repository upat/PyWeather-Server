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
logtxt_path = r'/home/linaro/Documents/server/log/python_log.txt'
wnews_path  = r'/home/linaro/Documents/server/json/wnews.json'
dlist_path  = r'/home/linaro/Documents/server/json/datelist.json'
jma_path    = r'/home/linaro/Documents/server/json/jma.json'

# 気象庁 アメダス
jma_url	  = "https://www.jma.go.jp/jp/amedas_h/today-51106.html?areaCode=000&groupCode=36"
# ウェザーニュース HTML版
wnews_url = "https://weathernews.jp/onebox/35.1802/136.9067/temp=c&lang=ja"

# マイコン向け変数(IP+PORT)
# SSD1306+ESP8266用
udp_addr1 = '192.168.0.13'
udp_port1 = 9000
# ILI9341+ESP32用
udp_addr2 = '192.168.0.14'
udp_port2 = 9200
