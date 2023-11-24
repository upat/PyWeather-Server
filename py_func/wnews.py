#!/usr/bin/env python3
# coding: UTF-8
import requests, json, datetime
from bs4 import BeautifulSoup
import collections as cl
from pathlib import Path

# 実行ファイルの絶対パスの親ディレクトリ×2+出力ファイルの相対パス
FILE_NAME = Path( Path( Path( __file__ ).resolve().parent ).parent, 'json/wnews.json' )

# 処理内容      ：Webページアクセス、JSON保存
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：天気予報データを取得後、JSONファイルへ保存
#                 ページレイアウトが変更される場合があるので都度修正が必要
# 依存ライブラリ：requests, bs4, json, collections, pathlib, datetime
def update_wnews( req, rcv_txt ):
	# ウェザーニュース HTML版
	##### ↓↓↓使用環境により適宜編集↓↓↓ #####
	WNEWS_URL = 'https://weathernews.jp/onebox/35.6904811111111/139.706551111111/'
	##### ↑↑↑使用環境により適宜編集↑↑↑ #####

	# レスポンス
	res = False
	# データ取得
	html = requests.get( WNEWS_URL, timeout=5.0 )

	# リスト初期化
	time_list = []
	temp_list = []
	img_list  = []

	# html読み込み
	src = BeautifulSoup( html.text, 'html.parser' )
	
	# 必要な箇所のみ抽出
	src = src.find( 'div', attrs={ 'class':'switchContent__item act' } )
	src = src.find( 'div', attrs={ 'class':'wTable__body' } ) # このclassは2つ存在する

	# 時間リスト作成
	for time_txt in src.find_all( attrs={ 'class':'wTable__item time' } ):
		time_list.append( time_txt.string )
	# 気温リスト作成
	for temp_txt in src.find_all( attrs={ 'class':'wTable__item t' } ):
		temp_txt.select_one( 'span' ).decompose()
		temp_list.append( temp_txt.string )
	# 天気アイコンURLリスト作成
	for img_txt in src.find_all( 'img', attrs={ 'class':'wIcon' } ):
		img_list.append( img_txt[ 'src' ] )   # 本日データのアイコンURL
	
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
			if time_list[cnt] in json_data:
				break
			json_data[ time_list[cnt] ] = cl.OrderedDict( { 'temp':temp_list[cnt], 'weather':img_list[cnt] } )
		
		# フォルダが無い場合作成(作成済みでもok)
		Path( Path( FILE_NAME ).parent ).mkdir( exist_ok=True )

		# JSONファイルへ出力(新規作成 or 上書き)
		with open( FILE_NAME, mode='w' ) as f:
			# f.write( json.dumps( json_data ) ) # 運用向け(インデント無し)
			f.write( json.dumps( json_data, indent=4 ) )

		# レスポンス
		res = True
	
	if not res:
		req = req + '(fail)'
	
	return req, rcv_txt

# 処理内容      ：データ送信
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：JSONファイルを読み出し、読みだしたテキストを返す
# 依存ライブラリ：json, pathlib
def get_wnews( req, rcv_txt ):
	if Path( FILE_NAME ).exists():
		# 日時データ取得
		with open( FILE_NAME, mode='r') as f:
			# jsonファイルよりデータ取得
			rcv_txt = f.read()
			rcv_txt = rcv_txt.encode( 'utf-8' )

	return req, rcv_txt
