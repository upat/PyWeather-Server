#!/usr/bin/env python3
# coding: UTF-8
import subprocess, re, shutil, datetime
from pathlib import Path

# 実行ファイルの絶対パスの親ディレクトリ×2+出力ファイルの相対パス
FILE_NAME = Path( Path( Path( __file__ ).resolve().parent ).parent, 'log/hdd_log.txt' )

# 処理内容      ：HDD情報取得
# 引数          ：要求, 応答テキスト
# 戻り値        ：要求, 応答テキスト
# 備考          ：デバイス名から有効なパスを取得、HDD情報を出力
# 依存ライブラリ：subprocess, re, pathlib, datetime
def read_hdd_data( req, rcv_txt ):
	# HDDデバイス名
	##### ↓↓↓使用環境により適宜編集↓↓↓ #####
	HDD_NAME = 'WD20EZRX'
	##### ↑↑↑使用環境により適宜編集↑↑↑ #####
	
	# HDD情報辞書
	hdd_info = {
		'total' : '-1', # HDDの全容量
		'free'  : '-1', # HDDの空き容量
		'rs_ct' : '-1', # 代替処理済のセクタ数
		'temp'  : '-1', # HDD温度情報
		'cps'   : '-1', # 代替処理保留中のセクタ数
		'err'   : True  # コマンド実行結果
	}
	
	# partedコマンドでディスク情報一覧を取得
	parted_run = subprocess.run( ['sudo', 'parted', '-l'], capture_output=True, text=True )
	if parted_run.returncode != 0: # 実行エラー
		return hdd_info
	parted_stdout = parted_run.stdout.split( '\n' )
	
	device_path = ''
	# partedコマンド結果からHDD_NAMEを含む行の次の行(ディスク名)を取得(indexを逆引きで取得)
	for txt in parted_stdout:
		if HDD_NAME in re.sub( ' ', '', txt ): # WD20EZRXは『WD 20EZRX』で読み出されるため半角スペース除去
			device_path = parted_stdout[ parted_stdout.index( txt ) + 1 ]
			device_path = device_path.split( ' ' )[1][:-1] # 半角スペースで分割+末尾のコロン除去
			break
	
	# 有効なパスであれば処理続行
	if ( device_path is not '' ) and ( Path( device_path ).exists() ):
		# ディスクのマウント場所を取得(開発環境では2番目が多いためディスク名末尾に固定で2を追加)
		findmnt_run = subprocess.run( ['findmnt', device_path + '2'], capture_output=True, text=True )
		if findmnt_run.returncode != 0: # 実行エラー
			return hdd_info
		findmnt_stdout = findmnt_run.stdout.split( '\n' )
		
		# 1番目のパス名(マウント先)を取得
		device_mnt = [ txt for txt in findmnt_stdout if txt.startswith( '/' ) ]
		device_mnt = device_mnt[0].split( ' ' )[0] # 半角スペースで分割
		
		# 有効なパスであれば処理続行
		if ( device_mnt is not '' ) and ( Path( device_mnt ).exists() ):
			# SMART情報取得
			hdd_info.update( read_smart( device_path ) )
			# 容量情報取得
			hdd_info.update( read_disk_size( device_mnt ) )
	
	# 現在日時取得
	log_time = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
	
	# 代替処理済のセクタ数または代替処理保留中のセクタ数が0より大きい
	if ( int( hdd_info['rs_ct'] ) > 0 ) or ( int( hdd_info['cps'] ) > 0 ):
		hdd_err = 'error'
	else:
		hdd_err = 'normal'
	
	# ログ出力(空き容量、HDD温度、エラー有無)
	if not hdd_info['err']:
		if Path( FILE_NAME ).exists():
			# 既にファイルが存在する場合は追記
			with open( FILE_NAME, mode='a') as f:
				write_log = log_time + ' Free:' + hdd_info['free'].ljust( 8 ) + ' Temp:' + ( hdd_info['temp'] + '℃' ).ljust( 3 ) + ' Status:' + hdd_err + '\n'
				f.write( write_log )
		else:
			# 存在しない場合は新規作成
			# フォルダが無い場合作成(作成済みでもok)
			Path( Path( FILE_NAME ).parent ).mkdir( exist_ok=True )
			# ファイルを新規作成
			with open( FILE_NAME, mode='w') as f:
				write_log = log_time + ' Free:' + hdd_info['free'].ljust( 8 ) + ' Temp:' + ( hdd_info['temp'] + '℃' ).ljust( 3 ) + ' Status:' + hdd_err + '\n'
				f.write( write_log )
	else:
		# 情報取得に失敗した場合は実行ログに何も残さない
		req = ''

	return req, rcv_txt

# 処理内容      ：SMART情報取得
# 引数          ：ドライブパス
# 備考          ：指定ドライブのSMART情報を取得
# 依存ライブラリ：subprocess, re
def read_smart( device_path ):
	# smartmontoolsよりHDD温度情報の取得
	# sudo smartctl -a [デバイス名] -d sat
	smartctl_run = subprocess.run( ['sudo', 'smartctl', '-a', device_path, '-d', 'sat'], capture_output=True, text=True )
	if smartctl_run.returncode != 0:
		# エラー有り
		data = { 'err' : True }
		return data
	smartctl_stdout = smartctl_run.stdout.split( '\n' )
	
	# 代替処理済のセクタ数の数値のみトリミング
	rs_ct = [ x for x in smartctl_stdout if x.startswith( '  5 Reallocated_Sector_Ct' ) ]
	rs_ct = re.sub( ' ', '', rs_ct[0][-3:] )
	
	# HDD温度情報の数値のみトリミング
	temp = [ x for x in smartctl_stdout if x.startswith( '194 Temperature_Celsius' ) ]
	temp = re.sub( ' ', '', temp[0][-3:] )
	
	# 代替処理保留中のセクタ数の数値のみトリミング
	cps = [ x for x in smartctl_stdout if x.startswith( '197 Current_Pending_Sector' ) ]
	cps = re.sub( ' ', '', cps[0][-3:] )
	
	data = { 'rs_ct' : rs_ct, 'temp' : temp, 'cps' : cps, 'err' : False }
	
	return data
	
# 処理内容      ：容量情報取得
# 引数          ：ドライブパス
# 備考          ：指定ドライブの総容量、空き容量を取得
# 依存ライブラリ：shutil
def read_disk_size( device_path ):	
	# HDDの総容量
	total = shutil.disk_usage( device_path ).total
	total = round( total / ( 1024 * 1024 * 1024 ), 1 )
	total = str( total ) + 'GB'
	
	# HDDの空き容量
	free = shutil.disk_usage( device_path ).free
	free = round( free / ( 1024 * 1024 * 1024 ), 1 )
	free = str( free ) + 'GB'
	
	data = { 'total' : total, 'free' : free }
	
	return data
