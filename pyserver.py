#!/usr/bin/env python3
# coding: UTF-8
import requests, socket, re, time
import os, json, datetime, subprocess, calendar
from requests_oauthlib import OAuth1Session
from bs4 import BeautifulSoup
import collections as cl
from flask import Flask, render_template, request, jsonify

# chromium用 Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# chromium用 Selenium 待機時間用インポート
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# chromium用 Selenium タイムアウト例外用
from selenium.common.exceptions import TimeoutException

from py_var.var import *

app = Flask( __name__ )

@app.route( '/', methods=[ 'POST' ] ) # POSTメソッドを明示
def RcvPost():
	# 処理時間計測(開始)
	proc_time = time.time()
	# 応答用テキスト
	rcv_txt = '0'
	rcv_txt = rcv_txt.encode( 'utf-8' )
	
	if request.method == 'POST':
		# リクエスト取得(処理後に処理結果と共にログ出力)
		req = request.get_data()
		req = req.decode( 'utf-8' )
		
		# IP取得
		host = request.remote_addr
		# 現在日時取得
		log_time = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
		
		# 各リクエスト別の処理
		# 気象庁データ送信
		if 'get_jma' == req:
			if os.path.isfile( jma_path ):
				# 日時データ取得
				with open( jma_path, mode='r') as f:
					# jsonファイルよりデータ取得
					json_txt = json.load( f )

					# 応答データ作成
					rcv_txt = str( json_txt['weather']['baro'] ) + 'hPa ' \
								+ str( json_txt['weather']['humi'] ) + '% ' \
								+ str( json_txt['weather']['temp'] )
					rcv_txt = rcv_txt.encode()
			else:
				# ファイルが存在しない場合
				rcv_txt = '----.-hPa ---% ---.-'	
				req = req + ( '(fail)' )
				
		# 気象庁データ送信(応答データ縮小版)
		elif 'get_jma_l' == req:
			if os.path.isfile( jma_path ):
				# 日時データ取得
				with open( jma_path, mode='r') as f:
					# jsonファイルよりデータ取得
					json_txt = json.load( f )
					
					# 応答データ作成
					rcv_txt = str( json_txt['weather']['humi'] ) + '%  ' \
								+ str( json_txt['weather']['temp'] )
					rcv_txt = rcv_txt.encode()
			else:
				# ファイルが存在しない場合
				rcv_txt = '---%  ---.-'
				req = req + ( '(fail)' )
			
		elif 'update_jma' == req:
			req = req + ( '(' + update_jma() + ')' )

		elif 'get_wnews' == req:
			if os.path.isfile( wnews_path ):
				# 日時データ取得
				with open( wnews_path, mode='r') as f:
					# jsonファイルよりデータ取得
					rcv_txt = f.read()
					rcv_txt = rcv_txt.encode( 'utf-8' )
					
		elif 'update_wnews' == req:
			if not update_wnews():
				req = req + ( '(fail)' )

		elif 'datelist' == req:
			rcv_txt = res_datelist()
			rcv_txt = rcv_txt.encode( 'utf-8' )
		
		elif 'create' == req:
			req = req + create_dlist()
		
		elif 'temp_alert' == req:
			temp_alert( log_time )
		
		# 処理時間計測(終了)
		proc_time = time.time() - proc_time
		proc_time = str( '{:.3f}'.format( proc_time ) ) + 's' # 小数点以下を3桁まで表示

		# 日付+IP+リクエストでログ書き込み
		if os.path.isfile( logtxt_path ):
			# 既にファイルが存在する場合は追記
			with open( logtxt_path, mode='a') as f:
				write_log = log_time + ' ' + 'IP=' + host.ljust( 13 ) + ' ' + 'POST=' + str( req ).ljust( 19 ) + ' ' + 'TIME=' + proc_time + '\n'
				f.write( write_log )
		else:
			# 存在しない場合は新規作成
			# フォルダが無い場合作成(作成済みでもok)
			os.makedirs( log_path, exist_ok=True )
			# ファイルを新規作成
			with open( logtxt_path, mode='w') as f:
				write_log = log_time + ' ' + 'IP=' + host.ljust( 13 ) + ' ' + 'POST=' + str( req ).ljust( 19 ) + ' ' + 'TIME=' + proc_time + '\n'
				f.write( write_log )
	
	return rcv_txt

# 処理内容      ：Webページアクセス、データ抽出・保存
# 備考          ：温度・湿度・気圧のテキストデータを抽出後、JSONファイルへ保存
#                 ただし、同一時間内のWebページアクセスは15分経過するまで不可(JSONファイル保存データで制御)
# 依存ライブラリ：re, datetime, json, collections, selenium, bs4
def update_jma():
	# 日時初期値(テキスト、datetimeオブジェクト)
	strc_InitTime = '2000-01-01 00:00:00'
	objc_InitTime = datetime.datetime.strptime( strc_InitTime, '%Y-%m-%d %H:%M:%S' )
	# 再読み出し許可の時間(900秒=15分)
	u2c_IntervalSec = 900
	# 読み出しリトライ上限値
	u1c_RetryCnt = 3
	# 現在時刻を取得
	objc_NowTime = datetime.datetime.now()
	# レスポンス用テーブル
	strc_ResText = [ 'OK', 'OK_Err1', 'OK_Err2', 'Fail', 'NotUpdt', 'OthErr' ]
	
	# 最終更新日時
	strt_last_update = strc_InitTime
	# 時間比較用(読み出し変数は失敗時を想定し、存在しない時間の初期値)
	objt_read_time = objc_InitTime
	
	# 気象データ格納変数
	strt_temp_data = '--.-'   # 温度
	strt_humi_data = '--'     # 湿度
	strt_baro_data = '----.-' # 気圧
	
	# レスポンス用Index
	u1t_res_idx = 4

	# フォルダが無い場合作成(作成済みでもok)
	os.makedirs( json_path, exist_ok=True )

	# 日時データ取得
	if os.path.isfile( jma_path ):
		with open( jma_path, mode='r') as f:
			# 最終保存時刻を取得
			objt_rjson_data = json.load( f )
			strt_last_update = objt_rjson_data[ 'last_update' ][ 'timestamp' ]
			objt_read_time = datetime.datetime.strptime( strt_last_update, '%Y-%m-%d %H:%M:%S' )
			
	# 時間差の算出(objc_NowTime > objt_read_timeの前提)
	obj_subt_time = objc_NowTime - objt_read_time
	
	# 15分以上経過していること(And条件は読み出し日時が現在日時より先の場合の考慮)
	if( u2c_IntervalSec < obj_subt_time.seconds ) and ( 0 <= obj_subt_time.days ):
	
		# 読み出しリトライカウンタ初期化
		u1t_retry_cnt = 0
		
		# chromedriverによる読み出し開始
		objt_options = Options()
		
		objt_options.add_argument( '--headless' )    # ヘッドレスモード有効(画面表示を行わない)(必須)
		objt_options.add_argument( '--disable-gpu' ) # GPUを使用しない(無いと不安定になる)
		#options.add_argument( '--no-sandbox' )
		#options.add_argument( '--disable-dev-shm-usage' )
		#options.add_argument( '--disable-features=VizDisplayCompositor' )
		
		for u1t_loopcnt in range( u1c_RetryCnt ):
			try:
				# ChromeのWebDriverオブジェクトを作成する。
				objt_driver = webdriver.Chrome( options=objt_options )
				# ページ読み込み
				objt_driver.get( jma_url )
				# objt_driver.get()後の描画で指定class(湿度データ)が読み込まれるまでの待機時間(15s)
				# objt_driver.get()以前に実施すると描画前のhtml読み出しの状態でclass待機するので注意
				WebDriverWait( objt_driver, 15 ).until( EC.presence_of_element_located( ( By.CLASS_NAME, 'td-normalPressure' ) ) )
				
				### タイムアウトしなかった場合、以下処理続行 ###
				
				# ページのソース取得
				html = objt_driver.page_source
				src = BeautifulSoup( html, 'html.parser' )
				# 必要な箇所のみ抽出
				src = src.find( 'tr', attrs={ 'class':'amd-table-tr-onthedot' } )
				# 気象データ読み出し
				strt_temp_data = src.find( 'td', attrs={ 'class':'td-temp' } ).get_text()
				strt_humi_data = src.find( 'td', attrs={ 'class':'td-humidity' } ).get_text()
				strt_baro_data = src.find( 'td', attrs={ 'class':'td-normalPressure' } ).get_text()
				
				# 数値ではなかった場合の処理(読み出しデータの不備)
				if not bool( re.compile( '^-?[0-9]+\.?[0-9]*$' ).match( strt_temp_data ) ): # 氷点下(マイナス値)を考慮
					strt_temp_data = '--.-'

				if not bool( re.compile( "^\d+\.?\d*\Z" ).match( strt_humi_data ) ):
					strt_humi_data = '--'

				if not bool( re.compile( "^\d+\.?\d*\Z" ).match( strt_baro_data ) ):
					strt_baro_data = '----.-'
				
				# chromiumを閉じる
				objt_driver.quit()
				
				# 最終更新日時を現在時刻に設定
				strt_last_update = objc_NowTime.strftime( '%Y-%m-%d %H:%M:%S' )
				
				# 読み出し正常終了時
				break
			except TimeoutException as te:
				# 読み出し失敗時(全て失敗しても書き込みは実施)
				
				# chromiumを閉じる
				objt_driver.quit()
				# 読み出しリトライカウンタ加算
				u1t_retry_cnt = u1t_retry_cnt + 1
				# 5秒待ち
				time.sleep( 5 )
				# 3回までリトライ
				continue
			except Exception as e:
				# その他のエラー要因(リトライも書き込みもせず終了)
				
				# chromiumを閉じる
				objt_driver.quit()
				u1t_res_idx = 5
				return strc_ResText[u1t_res_idx]
				
		# リトライ回数をレスポンス用Indexへセット(0～3)
		u1t_res_idx = u1t_retry_cnt
		
		# JSONファイル作成(ページの読み出しが全て失敗した場合、前回更新日時or初期日時と全てハイフンのデータをセット)
		objt_wjson_data = cl.OrderedDict()
		objt_wjson_data[ 'last_update' ] = cl.OrderedDict( { 'timestamp':strt_last_update } )
		objt_wjson_data[ 'weather' ]     = cl.OrderedDict( { 'temp':strt_temp_data, 'humi':strt_humi_data, 'baro':strt_baro_data } )
		
		# JSONファイルへ出力(新規作成 or 上書き)
		with open( jma_path, mode='w' ) as f:
			f.write( json.dumps( objt_wjson_data, indent=4 ) )
		
	# レスポンス
	return strc_ResText[u1t_res_idx]


# 処理内容      ：Webページアクセス、JSON保存
# 備考          ：天気予報データを取得後、JSONファイルへ保存
#                 ページレイアウトが変更される場合があるので都度修正が必要
# 依存ライブラリ：requests, bs4, json, collections
def update_wnews():
	# レスポンス
	res = False
	# データ取得
	html = requests.get( wnews_url, timeout=5.0 )

	# リスト初期化
	time_list = []
	temp_list = []
	img_list  = []

	# html読み込み
	src = BeautifulSoup( html.text, 'html.parser' )
	
	# 必要な箇所のみ抽出
	src = src.find( 'div', attrs={ 'class':'weather-day__body' } )

	# 時間リスト作成
	for time_txt in src.find_all( attrs={ 'class':'weather-day__time' } ):
		time_list.append( time_txt.string )
	# 気温リスト作成
	for temp_txt in src.find_all( attrs={ 'class':'weather-day__t' } ):
		temp_list.append( temp_txt.string[ :-1 ] )
	# 天気アイコンURLリスト作成
	for img_txt in src.find_all( 'img' ):
		try:
			img_list.append( img_txt[ 'data-original' ] ) # 明日データのアイコンURL
		except:
			img_list.append( img_txt[ 'src' ] )           # 本日データのアイコンURL
	
	# 天気アイコンURLのリストからファイル名のみ抽出、天気毎にパターン分け
	#
	# 晴れ(0)
	# 550:猛暑
	# 100,500,600:晴れ
	#
	# 曇り(1)
	# 200:曇り
	#
	# 雨(2)
	# 300:雨
	# 650:小雨
	# 850:豪雨
	#
	# 雪(3)
	# 400,450:雪
	#
	# 未使用・未定義(4)
	# 350:雨
	for index, img_txt in enumerate( img_list ):
		if -1 < img_txt.rfind( '/' ) and -1 < img_txt.rfind( '.' ):
			temp = int( img_txt[ ( img_txt.rfind( '/' ) + 1 ):img_txt.rfind( '.' ) ] )
			
			if ( 100 == temp ) or ( 500 <= temp <= 600 ):
				img_list[ index ] = '0'
			elif 200 == temp:
				img_list[ index ] = '1'
			elif 300 == temp or 600 <= temp:
				img_list[ index ] = '2'
			elif 400 <= temp < 500:
				img_list[ index ] = '3'
			else:
				img_list[ index ] = '4'
		else:
			img_list[index] = '4'

	# JSONファイル作成処理
	if len( time_list ) == len( temp_list ) == len( img_list ):
		# JSONデータ初期化(辞書の格納順を保持)
		json_data = cl.OrderedDict()
		
		# 扱いやすくするため先頭にデータ挿入
		json_data[ 'info' ] = cl.OrderedDict( { 'timestamp':datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' ), 'start':time_list[0] } )

		# JSONデータ作成(辞書の格納順を保持)
		for cnt in range( len( time_list ) ):
			json_data[ time_list[cnt] ] = cl.OrderedDict( { 'temp':temp_list[cnt], 'weather':img_list[cnt] } )

		# フォルダが無い場合作成(作成済みでもok)
		os.makedirs( json_path, exist_ok=True )

		# JSONファイルへ出力(新規作成 or 上書き)
		with open( wnews_path, mode='w' ) as f:
			# f.write( json.dumps( json_data ) ) # 運用向け(インデント無し)
			f.write( json.dumps( json_data, indent=4 ) )

		# レスポンス
		res = True
	
	return res

# 処理内容      ：テキストデータをTwitterへ投稿
# 備考          ：temp_alertにて使用
# 依存ライブラリ：requests_oauthlib
def tweet( text ):
	try:
		# 認証
		twitter = OAuth1Session( CK, CS, AT, ATS )
		# データ作成
		text = { 'status' : text }
		# ツイートする
		req_media = twitter.post( url_text, params = text )
	except:
		pass

# 処理内容      ：テキストデータをTwitterへ投稿、シャットダウン処理
# 備考          ：ESP系マイコンが高温を検出時に使用
#                 tweetとの統合を検討
# 依存ライブラリ：subprocess
def temp_alert( now_time ):
	# ツイート
	tweet( 'temp_alert=' + str( now_time ) + '\n∩(´･ω･`)つ―*:.｡. .｡.:*･゜ﾟ･*　もうどうにでもな～れ' )
	# シャットダウン
	flag = subprocess.check_output( 'sudo shutdown -h now &', shell=True )

# 処理内容      ：日時データ取得
# 備考          ：ESP系マイコンへスリープ可否(0または1)を通知
# 依存ライブラリ：json, datetime
def res_datelist():
	try:
		# 日時データ取得
		dlist_data = open( dlist_path, 'r' )
		json_data = json.load( dlist_data )
		# 現在日時取得
		now = datetime.datetime.now()
		# 月・日から対象のデータを抽出(0または1)
		return json_data[str( now.month )][str( now.day )]
	except:
		# エラー時
		return '1'

# 処理内容      ：日時データ作成
# 備考          ：現在の年よりESP系マイコン通知用のデータを作成
# 依存ライブラリ：os, json, datetime, collections, calendar
def create_dlist():
	# フォルダが無い場合作成(作成済みでもok)
	os.makedirs( json_path, exist_ok=True )
	
	# 月曜日始めでオブジェクト作成
	cal = calendar.Calendar( firstweekday=6 )

	# コレクション作成
	date_list = cl.OrderedDict()
	# 現在の年を取得
	year = datetime.datetime.now()
	year = year.year

	# 月ごと(1～12)でループ
	for month in range( 1, 13 ):
		# 月ごとの(日付, 曜日)のタプルが入ったリスト
		temp_list = cal.itermonthdays2( year, month )
		
		# 日付格納リスト
		day_list = cl.OrderedDict()

		# 日にちごとでループ
		for day in temp_list:
			if 0 < day[0]:
				if -1 < day[1] < 5: # 月～金曜日か判定
					day_list[str( day[0] )] = '0'
				else:
					day_list[str( day[0] )] = '1'

		date_list[str( month )] = day_list

	# JSONファイルへ出力(新規作成 or 上書き)
	with open( dlist_path, mode='w' ) as f:
		# f.write( json.dumps( json_data ) ) # 運用向け(インデント無し)
		f.write( json.dumps( date_list, indent=4 ) )
	
	# レスポンス
	return '(' + str( year ) + ')'

# サーバー起動
if __name__ == '__main__':
	app.run( debug=True, host='0.0.0.0', port=8080, threaded=True )
