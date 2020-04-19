#!/usr/bin/env python3
# coding: UTF-8
import requests, socket, re
import os, json, datetime, subprocess
from requests_oauthlib import OAuth1Session
from http.server import HTTPServer, SimpleHTTPRequestHandler
from bs4 import BeautifulSoup
import collections as cl

from py_var.var import *

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
	now_time    = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
	last_update = now_time
	last_access = now_time
	
	read_hour = 255
	now_hour  = datetime.datetime.strptime( now_time, '%Y-%m-%d %H:%M:%S' ).hour
	
	temp_data = ''
	humi_data = ''
	baro_data = ''

	# 日時データ取得
	if os.path.isfile( jma_path ):
		with open( jma_path, mode='r') as f:
			# 最終保存時刻を取得
			rjson_data = json.load( f )
			last_update = rjson_data[ 'last_update' ][ 'timestamp' ]
			read_hour = datetime.datetime.strptime( last_update, '%Y-%m-%d %H:%M:%S' ).hour
	
	if ( read_hour == 255 ) or ( read_hour != now_hour ):
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
	else:
		with open( jma_path, mode='r') as f:
			# 最終保存時刻を取得
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

	# 送信用データの作成
	send_data1 = humi_data + '%  ' + temp_data
	send_data2 = baro_data + 'hPa ' + humi_data + '% ' + temp_data

	# UDP送信
	with socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) as sock:
		sock.sendto( send_data1.encode(), ( udp_addr1, udp_port1 ) )

	with socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) as sock:
		sock.sendto( send_data2.encode(), ( udp_addr2, udp_port2 ) )

# 処理内容      ：Webページアクセス、JSON保存
# 備考          ：天気予報データを取得後、JSONファイルへ保存
#                 ページレイアウトが変更される場合があるので都度修正が必要
# 依存ライブラリ：requests, bs4, json, collections
def create_wnewsdata():
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

		# JSONファイルへ出力(新規作成 or 上書き)
		with open( wnews_path, mode='w' ) as f:
			# f.write( json.dumps( json_data ) ) # 運用向け(インデント無し)
			f.write( json.dumps( json_data, indent=4 ) )

# 処理内容      ：テキストデータをTwitterへ投稿
# 備考          ：temp_alertにて使用
# 依存ライブラリ：requests_oauthlib
def tweet( text ):
	if ( CK != '' ) and ( CS != '' ) and ( AT != '' ) and ( ATS != '' ):
		# 認証
		twitter = OAuth1Session( CK, CS, AT, ATS )
		# データ作成
		text = { 'status' : text }
		# ツイートする
		req_media = twitter.post( url_text, params = text )

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

# 処理内容      ：サーバー処理
# 備考          ：ESP系マイコンの動作により適宜変更を行う
# 依存ライブラリ：http.server, datetime, os
class MyHandler( SimpleHTTPRequestHandler ):
	def common_response( self, txt = '0' ):
		self.send_response( 200 )
		self.send_header( 'Content-Type', 'text/plain' )
		self.end_headers()
		self.wfile.write( txt.encode( 'utf-8' ) ) # 動作確認用の応答

	# 基本GETは使用しない(通常動作)
	#def do_GET( self ):
	#	self.common_response()

	# 主にcurlとesp系ボードからのリクエスト用
	def do_POST( self ):
		content_length = int( self.headers.get( 'content-length', 0 ) )
		request = self.rfile.read( content_length )
		request = request.decode( 'utf-8' )
		
		# IP取得
		host, port = self.client_address[:2]
		# 現在日時取得
		log_time = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
		
		# 各リクエスト別の処理
		if 'weather' == request:
			self.common_response() # UDPで応答するため先にレスポンス応答
			send_jmadata()
		
		if 'temp_alert' == request:
			self.common_response() # レスポンス応答を使用しないため先に処理
			temp_alert( log_time )

		if 'wnews' == request:
			create_wnewsdata()
			self.common_response()

		if 'datelist' == request:
			self.common_response( res_datelist() )

		# 日付+IP+リクエストでログ書き込み
		if os.path.isfile( logtxt_path ):
			with open( logtxt_path, mode='a') as f:
				f.write( log_time + ' ' + 'IP=' + str( host ).ljust( 13 ) + ' ' + 'POST=' + request + '\n' )

# サーバー起動
httpd = HTTPServer( ( '', 8080 ), MyHandler )
httpd.serve_forever()

