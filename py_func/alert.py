#!/usr/bin/env python3
# coding: UTF-8
from requests_oauthlib import OAuth1Session
import subprocess, datetime

# 処理内容      ：テキストデータをTwitterへ投稿
# 引数          ：投稿テキスト
# 備考          ：temp_alertにて使用
# 依存ライブラリ：requests_oauthlib
def tweet( text ):
	# X(旧Twitter) v2 エンドポイント
	ENDPOINT = 'https://api.twitter.com/2/tweets'
	# APIキー
	##### ↓↓↓使用環境により適宜編集↓↓↓ #####
	CK  = ''
	CS  = ''
	AT  = ''
	ATS = ''
	##### ↑↑↑使用環境により適宜編集↑↑↑ #####
	
	try:
		# 認証
		twitter = OAuth1Session( CK, CS, AT, ATS )
		# データ作成
		text = { 'text' : text }
		# ツイートする
		req_text = twitter.post( ENDPOINT, json = text )
	except:
		pass

# 処理内容      ：テキストデータをTwitterへ投稿、シャットダウン処理
# 引数          ：現在時刻(テキスト形式)
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：ESP系マイコンが高温を検出時に使用
#                 tweetとの統合を検討
# 依存ライブラリ：subprocess, datetime
def temp_alert( req, rcv_txt ):
	# 現在時刻取得
	now_time = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
	# ツイート
	tweet( 'alert=' + str( now_time ) + '\n∩(´･ω･`)つ―*:.｡. .｡.:*･゜ﾟ･*　もうどうにでもな～れ' )
	# シャットダウン
	flag = subprocess.check_output( 'sudo shutdown -h now &', shell=True )
	
	return req, rcv_txt
