#!/usr/bin/env python3
# coding: UTF-8
import json, datetime, calendar
import collections as cl
from pathlib import Path

# 実行ファイルの絶対パスの親ディレクトリ×2+出力ファイルの相対パス
FILE_NAME = Path( Path( Path( __file__ ).resolve().parent ).parent, 'json/datelist.json' )

# 処理内容      ：日時データ取得
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：ESP系マイコンへスリープ可否(0または1)を通知
# 依存ライブラリ：json, datetime, pathlib
def res_datelist( req, rcv_txt ):
	# ファイル有無確認
	if not Path( FILE_NAME ).exists():
		create_dlist()
		req = req + '(Create)'
		# ファイル生成確認
		if not Path( FILE_NAME ).exists():
			# エラー時
			rcv_txt = '1'
			req = req + '(NG)'
			return req, rcv_txt
	
	# 日時データ取得
	dlist_data = open( FILE_NAME, 'r' )
	json_data = json.load( dlist_data )
	# 現在日時取得
	now = datetime.datetime.now()
	
	# 現在の年と異なる場合、日時データ再作成チェック
	if json_data['year'] != str( now.year ):
		# 日時データ作成
		create_dlist()
		# 辞書を初期化して再読み込み
		json_data = cl.OrderedDict()
		dlist_data = open( dlist_path, 'r' )
		json_data = json.load( dlist_data )
	
	# 月・日から対象のデータを抽出(0(許可)または1(禁止))
	rcv_txt = json_data[str( now.month )][str( now.day )]
	
	return req, rcv_txt

# 処理内容      ：日時データ作成
# 備考          ：現在の年よりESP系マイコン通知用のデータを作成
# 依存ライブラリ：pathlib, json, datetime, collections, calendar
def create_dlist():
	# フォルダが無い場合作成(作成済みでもok)
	Path( Path( FILE_NAME ).parent ).mkdir( exist_ok=True )
	
	# 月曜日始めでオブジェクト作成
	cal = calendar.Calendar( firstweekday=6 )

	# コレクション作成
	date_list = cl.OrderedDict()
	# 現在の年を取得
	year = datetime.datetime.now()
	year = year.year
	# 出力年を保存
	date_list['year'] = str( year )
	
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
	with open( FILE_NAME, mode='w' ) as f:
		# f.write( json.dumps( json_data ) ) # 運用向け(インデント無し)
		f.write( json.dumps( date_list, indent=4 ) )

# 処理内容      ：日時データ反転
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：ESP系マイコンへのスリープ可否(0または1)を反転させる
#                 サーバー時間で上書きするため、サーバーの時間設定に注意すること
# 依存ライブラリ：json, datetime, pathlib
def inversion_datelist( req, rcv_txt ):
	# ファイル有無確認
	if not Path( FILE_NAME ).exists():
		# 応答テキスト(エラー時)
		rcv_txt = 'fail(not file)'
		req = req + '(NG)'
		return req, rcv_txt
	
	# 日時データ取得
	dlist_data = open( FILE_NAME, 'r' )
	json_data = json.load( dlist_data )
	# 現在日時取得
	now = datetime.datetime.now()
	
	# 現在の年と同じ
	if json_data['year'] == str( now.year ):
		# 日時データ反転(1(禁止)の場合0(許可)、それ以外は1(禁止))
		if '1' == json_data[str( now.month )][str( now.day )]:
			json_data[str( now.month )][str( now.day )] = '0'
			# 応答テキスト
			rcv_txt = 'inversion(1->0)'
		else:
			json_data[str( now.month )][str( now.day )] = '1'
			# 応答テキスト
			rcv_txt = 'inversion(*->1)'
		
		# JSONファイルへ出力(新規作成 or 上書き)
		with open( FILE_NAME, mode='w' ) as f:
			# f.write( json.dumps( json_data ) ) # 運用向け(インデント無し)
			f.write( json.dumps( json_data, indent=4 ) )
	else:
		# 応答テキスト(エラー時)
		rcv_txt = 'fail(old)'
		req = req + '(NG)'
	
	return req, rcv_txt
