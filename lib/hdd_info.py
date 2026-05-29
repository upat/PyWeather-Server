#!/usr/bin/env python3
# coding: UTF-8
import subprocess, shutil, datetime, time
from pathlib import Path

# 実行ファイルの絶対パスの親ディレクトリ×2+出力ファイルの相対パス
FILE_NAME = Path(__file__).resolve().parent.parent / 'log' / 'hdd_log.txt'
# HDDデバイス名
##### ↓↓↓使用環境により適宜編集↓↓↓ #####
HDD_NAME = 'WD20EZRX'
##### ↑↑↑使用環境により適宜編集↑↑↑ #####

# 処理内容      ：HDD情報取得
# 引数          ：-
# 戻り値        ：実行結果
# 備考          ：HDDのSMART情報と容量情報を取得して出力
# 依存ライブラリ：subprocess, pathlib, datetime
def log_info():
	# HDD情報辞書
	hdd_info = {
		'total'  : 0.0,          # HDDの全容量
		'free'   : 0.0,          # HDDの空き容量
		'usage'  : 0.0,          # HDDの使用率
		'status' : 'no_device',  # HDD健康状態
		'temp'   : 0,            # HDD温度情報
		'result' : True          # コマンド実行結果
	}
	
	# HDDパス取得
	(dev_path, mnt_path) = find_mntpath()
	if dev_path:
		# SMART情報取得
		hdd_info.update(get_smart(dev_path))
		# 容量情報取得
		hdd_info.update(get_usage(mnt_path))
	
	# ログ出力(空き容量、HDD温度、エラー有無)
	if hdd_info['result']:
		# フォルダが無い場合作成(作成済みでもok)
		FILE_NAME.parent.mkdir(parents=True, exist_ok=True)
		# ファイルを新規作成、既にファイルが存在する場合は追記
		with open(FILE_NAME, mode='a') as f:
			log_txt = (
				f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]" # 現在日時
				f" Free:{hdd_info['free']:>6}/{hdd_info['total']:>6}GB({hdd_info['usage']:>5}%)"
				f" Temp:{hdd_info['temp']:>2}℃"
				f" Status:{hdd_info['status']}\n"
			)
			f.write(log_txt)
	else:
		# 情報取得に失敗した場合
		return False
	
	return True

# 処理内容      ：SMART情報取得
# 引数          ：HDDのデバイス名
# 戻り値        ：処理結果
# 備考          ：指定ドライブのSMART情報を取得
# 依存ライブラリ：subprocess
def get_smart(dev_path):
	# smartmontoolsよりHDD温度情報の取得
	# sudo smartctl -a [HDDのデバイス名] -d sat
	smartctl_run = subprocess.run(['sudo', 'smartctl', '-a', dev_path, '-d', 'sat'], capture_output=True, text=True)
	# smartctlのコマンド実行エラーだけを拾う
	if smartctl_run.returncode & 0x03:
		# エラー有り
		data = {
			'result' : False,
			'status' : 'no_data'
		}
		return data
	smartctl_stdout = smartctl_run.stdout.splitlines()
	
	try:
		# 代替処理済のセクタ数の数値のみトリミング
		rsc = [x for x in smartctl_stdout if x.startswith('  5 Reallocated_Sector_Ct')]
		rsc = int(rsc[0].split()[-1]) # 末尾の生の値
		# HDD温度情報の数値のみトリミング
		temp = [x for x in smartctl_stdout if x.startswith('194 Temperature_Celsius')]
		temp = int(temp[0].split()[-1]) # 末尾の生の値
		# 代替処理保留中のセクタ数の数値のみトリミング
		cps = [x for x in smartctl_stdout if x.startswith('197 Current_Pending_Sector')]
		cps = int(cps[0].split()[-1]) # 末尾の生の値
		# 回復不能セクタ数の数値のみトリミング
		ou = [x for x in smartctl_stdout if x.startswith('198 Offline_Uncorrectable')]
		ou = int(ou[0].split()[-1]) # 末尾の生の値
	except Exception:
		# エラー有り
		data = {
			'result' : False,
			'status' : 'no_data'
		}
		return data
	
	# いずれかの生の値が0で無ければエラー判定
	if (rsc + cps + ou) > 0:
		status = 'error'
	else:
		status = 'normal'
	
	data = {
		'status' : status,
		'temp'   : temp,
		'result' : True
	}
	
	return data
	
# 処理内容      ：容量情報取得
# 引数          ：HDDのパス
# 戻り値        ：処理結果
# 備考          ：HDDの容量関連の情報を取得
# 依存ライブラリ：shutil
def get_usage(mnt_path):
	# デバイス情報取得
	usage_info = shutil.disk_usage(mnt_path)
	# HDDの総容量
	total = usage_info.total
	total = round(total / (1024 ** 3), 1)
	# HDDの空き容量
	free = usage_info.free
	free = round(free / (1024 ** 3), 1)
	# HDDの使用率
	usage = round((1 - (free / total)) * 100, 1)
	
	# コマンドは実行していないので実行結果は更新しない
	data = {
		'total' : total,
		'free'  : free,
		'usage' : usage
	}
	
	return data

# 処理内容      ：HDDパス取得
# 引数          ：-
# 戻り値        ：HDDデバイス名、パス
# 備考          ：HDDのデバイス名とパスを取得する
# 依存ライブラリ：subprocess
def find_mntpath():
	# /dev/disk/by-id直下のシンボリックリンクからデバイス名を取得
	path_list = []
	for p in Path('/dev/disk/by-id').iterdir():
		# 指定した文字列を含むシンボリックリンクを検索
		if HDD_NAME in p.name:
			path_list.append(str(p.resolve())) # デバイス名のリストを作成
	# デバイス名のリストが空でなければ続行
	if path_list:
		for p in path_list:
			# デバイス名からパスを取得(オプションでヘッダー非表示、TARGETのみ表示を指定)
			# コマンド実行エラーが拾えない(該当なしでもreturncode != 0になる)
			findmnt_run = subprocess.run(['findmnt', '-n', '-o', 'TARGET', p], capture_output=True, text=True)
			findmnt_res = findmnt_run.stdout.strip()
			# 基本的に1デバイスで1つのパスしか設定しない運用のため、先頭のものを使用
			if findmnt_res:
				return p, findmnt_res
	
	# 何も見つけられなかった時
	return '', ''

# 処理内容      ：HDDスリープ処理
# 引数          ：実行フラグ
# 戻り値        ：実行結果
# 備考          ：HDDをアンマウントし、HDDの電源も落とす
# 依存ライブラリ：subprocess, time
def umount_hdd(flag):
	# 0なら実行
	if flag == '0':
		# HDDパス取得
		(dev_path, mnt_path) = find_mntpath()
		if dev_path:
			# syncコマンド
			sync_run = subprocess.run(['sync'], capture_output=True, text=True)
			if sync_run.returncode != 0:
				return False
			time.sleep(1) # 1s待ち
			# umountコマンド
			umount_run = subprocess.run(['sudo', 'umount', mnt_path], capture_output=True, text=True)
			if umount_run.returncode != 0:
				return False
			time.sleep(1) # 1s待ち
			#unbindコマンド
			unbind_run = subprocess.run(
				['sudo', 'tee', '/sys/bus/usb/drivers/usb/unbind'],
				input='1-1.1.3', # udevadm info --query=path --name=dev_pathで確認可
				capture_output=True,
				text=True
			)
			if unbind_run.returncode != 0:
				return False
			# hub-ctrlコマンド(lsusb -tで確認可)
			hubctrl_run = subprocess.run(
				['sudo', 'hub-ctrl', '-b', '1', '-d', '3', '-P', '3', '-p', '0'],
				capture_output=True,
				text=True
			)
			if hubctrl_run.returncode != 0:
				return False
		else:
			return False
	
	return True
