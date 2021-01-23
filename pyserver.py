#!/usr/bin/env python3
# coding: UTF-8
import requests, socket, re, time
import os, json, datetime, subprocess, calendar
from requests_oauthlib import OAuth1Session
from bs4 import BeautifulSoup
import collections as cl
from flask import Flask, render_template, request, jsonify

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
		# リクエスト取得
		req = request.get_data()
		req = req.decode( 'utf-8' )
		
		# IP取得
		host = request.remote_addr
		# 現在日時取得
		log_time = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
		
		# 各リクエスト別の処理
		if 'weather' == req:
			req = req + send_jmadata()
		
		if 'temp_alert' == req:
			temp_alert( log_time )

		if 'wnews' == req:
			if create_wnewsdata() and os.path.isfile( wnews_path ):
				# 日時データ取得
				with open( wnews_path, mode='r') as f:
					# jsonファイルよりデータ取得
					rcv_txt = json.load( f )

		if 'datelist' == req:
			rcv_txt = res_datelist()
			rcv_txt = rcv_txt.encode( 'utf-8' )
		
		if 'create' == req:
			req = req + create_dlist()
		
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

# 処理内容      ：Webページアクセス、コード出力
# 備考          ：Webページ取得後、HTMLを1行ずつ出力
#                 send_jmadataにて使用
# 依存ライブラリ：requests
def get_jmahtml():
	html = requests.get( jma_url, timeout=5.0 )
	
	for line in html.text.splitlines():
		yield line

# 処理内容      ：Webページアクセス、データ抽出、UDP送信
# 備考          ：温度・湿度・気圧のテキストデータを抽出後、設定したIPアドレスへUDP送信
#                 ただし、同一時間内のWebページアクセスは一度まで(JSONファイル保存データで制御)
# 依存ライブラリ：socket, re, datetime, json, collections
def send_jmadata():
	# 現在時刻を初期値に設定
	now_time    = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
	last_update = now_time
	last_access = now_time
	
	# 時間比較用(読み出し変数は失敗時を想定し、存在しない時間の初期値)
	read_hour = 32
	now_hour  = datetime.datetime.strptime( now_time, '%Y-%m-%d %H:%M:%S' ).hour
	
	# 気象データ格納変数
	temp_data = '' # 温度
	humi_data = '' # 湿度
	baro_data = '' # 気圧
	
	# レスポンス
	res = ''

	# フォルダが無い場合作成(作成済みでもok)
	os.makedirs( json_path, exist_ok=True )

	# 日時データ取得
	if os.path.isfile( jma_path ):
		with open( jma_path, mode='r') as f:
			# 最終保存時刻を取得
			rjson_data = json.load( f )
			last_update = rjson_data[ 'last_update' ][ 'timestamp' ]
			read_hour = datetime.datetime.strptime( last_update, '%Y-%m-%d %H:%M:%S' ).hour
	
	# jsonファイルが未作成 or 最終更新時間が現在の時間ではない
	if ( read_hour == 32 ) or ( read_hour != now_hour ):
		tag_pre = ''

		for tag in get_jmahtml():
			if -1 < tag.find( '<td class="block middle">' ):
				start = tag.find( '>' ) + 1
				goal  = tag.find( '</td>' )
				data  = tag[ start : goal ]

				# 空白があったら終了
				if data == '&nbsp;':
					break
				
				tag_pre   = tag  # 湿度データ用に前回のhtmlソースを保持
				temp_data = data

		# 気圧データの切り抜き
		baro_data = tag_pre[ tag_pre.rfind( '">' ) + 2 : tag_pre.rfind( '</td>' ) ]

		# 湿度データの切り抜き
		tag_pre = tag_pre[ 0 : tag_pre.rfind( '</td><' ) ]
		humi_data = tag_pre[ tag_pre.rfind( '>' ) + 1 : ]
		
		# 数値ではなかった場合の処理
		if not bool( re.compile( '^-?[0-9]+\.?[0-9]*$' ).match( temp_data ) ): # 氷点下(マイナス値)を考慮
			temp_data = '--.-'

		if not bool( re.compile( "^\d+\.?\d*\Z" ).match( humi_data ) ):
			humi_data = '--'

		if not bool( re.compile( "^\d+\.?\d*\Z" ).match( baro_data ) ):
			baro_data = '----.-'
		
		# JSONファイル作成
		last_update = last_access
		wjson_data = cl.OrderedDict()
		wjson_data[ 'last_update' ] = cl.OrderedDict( { 'timestamp':last_update } )
		wjson_data[ 'last_access' ] = cl.OrderedDict( { 'timestamp':last_access } )
		wjson_data[ 'weather' ]     = cl.OrderedDict( { 'temp':temp_data, 'humi':humi_data, 'baro':baro_data } )
		
		# JSONファイルへ出力(新規作成 or 上書き)
		with open( jma_path, mode='w' ) as f:
			# f.write( json.dumps( json_data ) ) # 運用向け(インデント無し)
			f.write( json.dumps( wjson_data, indent=4 ) )
		
		# レスポンス
		res = '(update)'
	
	# jsonファイルが作成済み and 最終更新時間が現在の時間である
	else:
		# jsonファイルが作成済みであるため読み出しの失敗は想定しない
		with open( jma_path, mode='r') as f:
			# 保存済みのデータを取得
			rjson_data = json.load( f )
			temp_data = rjson_data[ 'weather' ][ 'temp' ]
			humi_data = rjson_data[ 'weather' ][ 'humi' ]
			baro_data = rjson_data[ 'weather' ][ 'baro' ]
		
		wjson_data = cl.OrderedDict()
		wjson_data[ 'last_update' ] = cl.OrderedDict( { 'timestamp':last_update } )
		wjson_data[ 'last_access' ] = cl.OrderedDict( { 'timestamp':last_access } )
		wjson_data[ 'weather' ]     = cl.OrderedDict( { 'temp':temp_data, 'humi':humi_data, 'baro':baro_data } )
		
		# JSONファイルへ出力(新規作成 or 上書き)
		with open( jma_path, mode='w' ) as f:
			# f.write( json.dumps( json_data ) ) # 運用向け(インデント無し)
			f.write( json.dumps( wjson_data, indent=4 ) )
		
		# レスポンス
		res = '(not update)'

	# 送信用データの作成
	send_data1 = humi_data + '%  ' + temp_data
	send_data2 = baro_data + 'hPa ' + humi_data + '% ' + temp_data

	# UDP送信
	with socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) as sock:
		sock.sendto( send_data1.encode(), ( udp_addr1, udp_port1 ) )

	with socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) as sock:
		sock.sendto( send_data2.encode(), ( udp_addr2, udp_port2 ) )
	
	return res

# 処理内容      ：Webページアクセス、JSON保存
# 備考          ：天気予報データを取得後、JSONファイルへ保存
#                 ページレイアウトが変更される場合があるので都度修正が必要
# 依存ライブラリ：requests, bs4, json, collections
def create_wnewsdata():
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
