#!/usr/bin/env python3
# coding: UTF-8
import time, datetime
import collections as cl
from flask import Flask, render_template, request, jsonify
from pathlib import Path

from py_func.jma import *
from py_func.wnews import *
from py_func.datelist import *
from py_func.alert import *

# 実行ファイルの絶対パスの親ディレクトリ+出力ファイルの相対パス
FILE_NAME = Path( Path( __file__ ).resolve().parent, 'log/python_log.txt' )
# 関数辞書(リクエストをキーにして呼び出し)
func_dict = {
	'get_jma'      : get_jma,
	'get_jma_l'    : get_jma_l,
	'update_jma'   : update_jma,
	'get_wnews'    : get_wnews,
	'update_wnews' : update_wnews,
	'datelist'     : res_datelist,
	'temp_alert'   : temp_alert,
	'inv_datelist' : inversion_datelist
}

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
		
		# 関数とのデータ交換用
		func_res = [ req, rcv_txt ]
		
		# リクエストをキーにして関数呼び出し
		if req in func_dict:
			func_res = func_dict[req]( *func_res ) # リストを分解して渡す
		else:
			func_res[0] = ''
		
		# 処理時間計測(終了)
		proc_time = time.time() - proc_time
		proc_time = str( '{:.3f}'.format( proc_time ) ) + 's' # 小数点以下を3桁まで表示
		
		# リストを分解
		( req, rcv_txt ) = func_res

		# 正常な要求があった場合
		if req != '':
			# 日付+IP+リクエストでログ書き込み
			if Path( FILE_NAME ).exists():
				# 既にファイルが存在する場合は追記
				with open( FILE_NAME, mode='a') as f:
					write_log = log_time + ' ' + 'IP=' + host.ljust( 13 ) + ' ' + 'POST=' + str( req ).ljust( 19 ) + ' ' + 'TIME=' + proc_time + '\n'
					f.write( write_log )
			else:
				# 存在しない場合は新規作成
				# フォルダが無い場合作成(作成済みでもok)
				Path( Path( FILE_NAME ).parent ).mkdir( exist_ok=True )
				# ファイルを新規作成
				with open( FILE_NAME, mode='w') as f:
					write_log = log_time + ' ' + 'IP=' + host.ljust( 13 ) + ' ' + 'POST=' + str( req ).ljust( 19 ) + ' ' + 'TIME=' + proc_time + '\n'
					f.write( write_log )
	
	return rcv_txt

# サーバー起動
if __name__ == '__main__':
	app.run( debug=True, host='0.0.0.0', port=8080, threaded=True )
