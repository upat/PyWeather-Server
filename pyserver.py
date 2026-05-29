#!/usr/bin/env python3
# coding: UTF-8
import time, datetime
from dataclasses import dataclass
from typing import ClassVar
from flask import Flask, render_template, request, send_file
from pathlib import Path

from lib import jma
from lib import datelist
from lib import hdd_info

# ログ出力用dataclass
@dataclass
class LogData:
	# 実行ファイルの絶対パスの親ディレクトリ+出力ファイルの相対パス
	FILE_NAME: ClassVar[Path] = (
		Path(__file__).resolve().parent
		/ 'log'
		/ 'python_log.txt'
	)
	
	start_time : float = 0.0
	timestamp  : str   = ''
	path       : str   = ''
	ip_addr    : str   = ''
	method     : str   = ''
	
	# 処理内容      ：GET/POSTメソッド 関数処理前 データセットHelper関数
	# 引数          ：flask.requestオブジェクト
	# 戻り値        ：一部データ設定したクラスオブジェクト
	# 備考          ：-
	# 依存ライブラリ：time, datetime
	@classmethod
	def create(cls, request):
		return cls(
			start_time = time.perf_counter(),            # 処理開始時間
			timestamp  = datetime.datetime.now().strftime('[%Y-%m-%d %H:%M:%S]'), # タイムスタンプ
			path       = request.full_path.rstrip('?'),  # 接続パス(pathだと階層のみ)
			ip_addr    = request.remote_addr,            # 接続元IP
			method     = request.method,                 # メソッド
		)
	
	# 処理内容      ：GET/POSTメソッド 関数処理後 ログ出力関数
	# 引数          ：関数処理結果
	# 戻り値        ：-
	# 備考          ：-
	# 依存ライブラリ：time, pathlib
	def write_log(self, result):
		# 処理時間算出
		execution_time = time.perf_counter() - self.start_time
		# 処理結果TrueならOK、FalseならNG
		result_txt = 'OK' if result else 'NG'
		
		# ログ用テキスト作成
		log_text = (
			f'{self.timestamp} '       # タイムスタンプ
			f'{self.ip_addr:<13} '     # 接続元IP(最大文字数:15-2)
			f'{self.method:<4} '       # メソッド(最大文字数:4)
			f'{self.path:<15} '        # 接続パス(最大文字数:15)
			f'{result_txt:<3} '        # 実行結果(最大文字数:3)
			f'{execution_time:.3f}s\n' # 処理時間(小数点以下3桁まで表示)
		)
		
		# フォルダが存在しなければ作成(作成済みでもok)
		self.FILE_NAME.parent.mkdir(parents=True, exist_ok=True)
		# 追記(なければ新規作成)で書き込み
		with open(self.FILE_NAME, mode='a', encoding='utf-8') as f:
			f.write(log_text)

app = Flask(__name__)

# web表示処理
@app.route('/', methods=['GET', 'POST'])
def exec_index():
	# ログ出力用クラス
	logdata = LogData.create(request)
	# POST処理(update_html)結果+処理結果
	result = True

	# 月取得
	default_month = datetime.datetime.now().month  # デフォルトは今月
	month = request.args.get('month', default=default_month, type=int)

	# POST
	update_result = None
	if request.method == 'POST':
		(result, update_result) = datelist.update_html(month, request.form)

	# GET/POST共通 表示データ取得
	html_data = datelist.get_html(month)
	# エラーチェック
	if not (html_data['status'] and result):
		result = False

	# ログ出力
	logdata.write_log(result)
	# レスポンス
	return render_template(
		'index.html',
		html_data=html_data,
		update_result=update_result
	)

# 気象データ更新 POSTメソッド
@app.route('/update_jma', methods=['POST'])
def exec_updatejma():
	# ログ出力用クラス
	logdata = LogData.create(request)

	# メイン処理
	result = jma.update_jma()

	# ログ出力
	logdata.write_log(result)
	# レスポンス
	return '', 204 # No Contentで返す

# HDD切断処理 POSTメソッド
@app.route('/umount_hdd', methods=['POST'])
def exec_umounthdd():
	# ログ出力用クラス
	logdata = LogData.create(request)
	
	# 日付取得
	(dl_result, dl_response) = datelist.get_dl()
	# メイン処理
	result = hdd_info.umount_hdd(dl_response)

	# ログ出力
	logdata.write_log(result)
	# レスポンス
	return '', 204 # No Contentで返す

# HDD情報取得 POSTメソッド
@app.route('/hdd_info', methods=['POST'])
def exec_hddinfo():
	# ログ出力用クラス
	logdata = LogData.create(request)

	# メイン処理
	result = hdd_info.log_info()

	# ログ出力
	logdata.write_log(result)
	# レスポンス
	return '', 204 # No Contentで返す

# 来年用スリープ可否フラグ新規作成 POSTメソッド
@app.route('/create_dl', methods=['POST'])
def exec_createdl():
	# ログ出力用クラス
	logdata = LogData.create(request)

	# 処理したい年を取得
	now = datetime.datetime.now()
	# メイン処理(年を+1する)
	result = datelist.create_dl(now.year + 1)

	# ログ出力
	logdata.write_log(result)
	# レスポンス
	return '', 204 # No Contentで返す

# icsファイル作成 POSTメソッド
@app.route('/create_ics', methods=['POST'])
def exec_createics():
	# ログ出力用クラス
	logdata = LogData.create(request)

	# メイン処理
	result = datelist.create_ics()

	# ログ出力
	logdata.write_log(result)
	# レスポンス
	return '', 204 # No Contentで返す

# 気象データ取得 GETメソッド
@app.route('/get_jma', methods=['GET'])
def exec_getjma():
	# ログ出力用クラス
	logdata = LogData.create(request)

	# 短縮フラグ設定
	if request.args.get("short") is not None:
		short_flag = True
	else:
		short_flag = False
	# メイン処理
	(result, response) = jma.get_jma(short_flag)

	# ログ出力
	logdata.write_log(result)
	# レスポンス
	return response

# スリープ可否フラグ取得 GETメソッド
@app.route('/get_dl', methods=['GET'])
def exec_getdl():
	# ログ出力用クラス
	logdata = LogData.create(request)

	# メイン処理
	(result, response) = datelist.get_dl()

	# ログ出力
	logdata.write_log(result)
	# レスポンス
	return response

# icsファイル取得
@app.route('/datelist.ics')
def exec_getics():
	# ログ出力用クラス
	logdata = LogData.create(request)
	
	# 存在チェック
	result =  datelist.ICS_FILE.exists()
	
	# ログ出力
	logdata.write_log(result)
	# レスポンス
	if not result:
		return '', 404 # Not Foundで返す
	return send_file(datelist.ICS_FILE, mimetype='text/calendar')

# サーバー起動
if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)
