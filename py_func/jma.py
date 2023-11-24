#!/usr/bin/env python3
# coding: UTF-8
import re, json, datetime
from bs4 import BeautifulSoup
import collections as cl
from pathlib import Path
# chromium用 Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# chromium用 Selenium 待機時間用インポート
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# chromium用 Selenium タイムアウト例外用
from selenium.common.exceptions import TimeoutException

# 実行ファイルの絶対パスの親ディレクトリ×2+出力ファイルの相対パス
FILE_NAME = Path( Path( Path( __file__ ).resolve().parent ).parent, 'json/jma.json' )

# 処理内容      ：Webページアクセス、データ抽出・保存
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：温度・湿度・気圧のテキストデータを抽出後、JSONファイルへ保存
#                 ただし、同一時間内のWebページアクセスは5分経過するまで不可(JSONファイル保存データで制御)
# 依存ライブラリ：re, datetime, json, collections, selenium, bs4, pathlib
def update_jma( req, rcv_txt ):
	# 気象庁 アメダス(10分毎)URL
	##### ↓↓↓使用環境により適宜編集↓↓↓ #####
	JMA_10MIN_URL = 'https://www.jma.go.jp/bosai/amedas/#area_type=offices&area_code=130000&amdno=44132&format=table10min&elems=53414'
	##### ↑↑↑使用環境により適宜編集↑↑↑ #####
	
	# 現在時刻を取得
	objc_NowTime = datetime.datetime.now()
	# 日時初期値(テキスト、datetimeオブジェクト)
	strc_InitTime = '2000-01-01 00:00:00'
	objc_InitTime = datetime.datetime.strptime( strc_InitTime, '%Y-%m-%d %H:%M:%S' )
	# 再読み出し許可の時間(300秒=5分)
	u2c_IntervalSec = 300
	
	# レスポンス用テーブル
	# OK      : 正常処理(エラー無し)
	# Fail    : その他エラー(構文エラーを想定)
	# NotUpdt : 最終更新からu2c_IntervalSec経過していないため未実施
	strc_ResText = [ 'OK', 'Fail', 'NotUpdt' ]
	
	# 最終更新日時
	strt_last_update = strc_InitTime
	# 時間比較用(読み出し変数は失敗時を想定し、存在しない時間の初期値)
	objt_read_time = objc_InitTime
	# 気象データ格納変数
	strt_time_data = '--:--'  # 取得時間
	strt_temp_data = '--.-'   # 温度
	strt_humi_data = '--'     # 湿度
	strt_baro_data = '----.-' # 気圧
	# レスポンス用Index
	u1t_res_idx = 2

	# フォルダが無い場合作成(作成済みでもok)
	Path( Path( FILE_NAME ).parent ).mkdir( exist_ok=True )

	# 日時データ取得
	if Path( FILE_NAME ).exists():
		with open( FILE_NAME, mode='r') as f:
			# 最終保存時刻を取得
			objt_rjson_data = json.load( f )
			strt_last_update = objt_rjson_data[ 'last_update' ][ 'timestamp' ]
			objt_read_time = datetime.datetime.strptime( strt_last_update, '%Y-%m-%d %H:%M:%S' )
			
	# 時間差の算出(objc_NowTime > objt_read_timeの前提)
	objt_subt_time = objc_NowTime - objt_read_time
	
	# 5分以上経過していること(And条件は読み出し日時が現在日時より先の場合の考慮)
	# 初回実行時は00:00～00:05の間、処理不可
	if( u2c_IntervalSec < objt_subt_time.seconds ) and ( 0 <= objt_subt_time.days ):
		
		# chrome設定
		objt_options = Options()
		objt_options.add_argument( '--headless' )    # ヘッドレスモード有効(画面表示を行わない)(必須)
		objt_options.add_argument( '--disable-gpu' ) # GPUを使用しない(無いと不安定になる)
		
		# 読み出し実行
		try:
			# ChromeのWebDriverオブジェクトを作成する。
			objt_driver = webdriver.Chrome( options=objt_options )
			# ページ読み込み
			objt_driver.get( JMA_10MIN_URL )
			# objt_driver.get()後の描画で指定class(湿度データ)が読み込まれるまでの待機時間(20s)
			# objt_driver.get()以前に実施すると描画前のhtml読み出しの状態でclass待機するので注意
			WebDriverWait( objt_driver, 20 ).until( EC.presence_of_element_located( ( By.CLASS_NAME, 'td-normalPressure' ) ) )
			
			### タイムアウトしなかった場合、以下処理続行 ###
			
			# ページのソース取得
			strt_html = objt_driver.page_source
			objt_bs_src = BeautifulSoup( strt_html, 'html.parser' )

			# table要素を取得し、tr要素のclass名から目的のデータ(行)を検索
			objt_bs_src = objt_bs_src.find( 'table', attrs={ 'class':'amd-table-seriestable' } )
			for objt_tr_tag in objt_bs_src.find_all( 'tr' ):
				if 'amd-table-tr-' in objt_tr_tag['class'][0]:
					objt_bs_src = objt_tr_tag
					break
			
			# 気象データ読み出し
			strt_time_data = objt_bs_src.find_all( 'td' )[1].get_text()
			strt_temp_data = objt_bs_src.find( 'td', attrs={ 'class':'td-temp' } ).get_text()
			strt_humi_data = objt_bs_src.find( 'td', attrs={ 'class':'td-humidity' } ).get_text()
			strt_baro_data = objt_bs_src.find( 'td', attrs={ 'class':'td-normalPressure' } ).get_text()
			
			# 数値ではなかった場合の処理(読み出しデータの不備)
			if strt_time_data.find( ':' ) == -1:
				strt_time_data = '--:--'
			
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
			
			# 正常終了
			u1t_res_idx = 0
		
		# 読み出し失敗(リトライも書き込みもせず終了)
		except:
		
			# chromiumを閉じる
			objt_driver.quit()
			# レスポンス用Indexへエラーの値セット
			u1t_res_idx = 1
			# 初期値に戻す
			strt_time_data = '--:--'  # 取得時間
			strt_temp_data = '--.-'   # 温度
			strt_humi_data = '--'     # 湿度
			strt_baro_data = '----.-' # 気圧
		
		# JSONデータ作成(ページの読み出しが全て失敗した場合、前回更新日時or初期日時と全てハイフンのデータをセット)
		objt_wjson_data = cl.OrderedDict()
		objt_wjson_data[ 'last_update' ] = cl.OrderedDict( { 'timestamp':strt_last_update } )
		objt_wjson_data[ 'weather' ]     = cl.OrderedDict( { 'time':strt_time_data, 'temp':strt_temp_data, 'humi':strt_humi_data, 'baro':strt_baro_data } )
		
		# JSONファイルへ出力(新規作成 or 上書き)
		with open( FILE_NAME, mode='w' ) as f:
			f.write( json.dumps( objt_wjson_data, indent=4 ) )

	# レスポンス
	req = req + ( '(' + strc_ResText[u1t_res_idx] + ')' )
	return req, rcv_txt

# 処理内容      ：データ送信
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：JSONファイルを読み出し、読みだしたテキストを返す
# 依存ライブラリ：json, pathlib
def get_jma( req, rcv_txt ):
	if Path( FILE_NAME ).exists():
		# 日時データ取得
		with open( FILE_NAME, mode='r') as f:
			# jsonファイルよりデータ取得
			json_txt = json.load( f )

			# 応答データ作成
			rcv_txt = str( json_txt['weather']['baro'] ) + 'hPa ' \
						+ str( json_txt['weather']['humi'] ) + '% ' \
						+ str( json_txt['weather']['temp'] )
			rcv_txt = rcv_txt.encode( 'utf-8' )
	else:
		# ファイルが存在しない場合
		rcv_txt = '----.-hPa ---% ---.-'	
		req = req + ( '(fail)' )
	
	return req, rcv_txt

# 処理内容      ：データ送信(縮小版)
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：JSONファイルを読み出し、読みだしたテキストを返す
# 依存ライブラリ：json, pathlib
def get_jma_l( req, rcv_txt ):
	if Path( FILE_NAME ).exists():
		# 日時データ取得
		with open( FILE_NAME, mode='r') as f:
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

	return req, rcv_txt
