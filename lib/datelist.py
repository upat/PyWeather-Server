#!/usr/bin/env python3
# coding: UTF-8
import json, datetime, calendar
from pathlib import Path
from icalendar import Calendar, Event

# 実行ファイルの絶対パスの親ディレクトリ×2+出力ファイルの相対パス
JSON_FILE = Path(__file__).resolve().parent.parent / 'json' / 'datelist.json'
ICS_FILE = Path(__file__).resolve().parent.parent / 'ics' / 'datelist.ics'
# 日本語曜日
WEEKDAY_STR = ['月', '火', '水', '木', '金', '土', '日']

# 処理内容      ：JSONファイル読み出し
# 引数          ：-
# 戻り値        ：読み出しデータまたはNone
# 備考          ：-
# 依存ライブラリ：json, pathlib
def load_file():
	# ファイルが無い時
	if not JSON_FILE.exists():
		return None
	
	with open(JSON_FILE, 'r', encoding='utf-8') as f:
		# 一度文字列で読み出し、空ファイルでなければ中身を返す
		text = f.read().strip()
		if not text:
			return None
		
		return json.loads(text) # loadsはJSON文字列をPythonオブジェクト化

# 処理内容      ：ファイル書き込み
# 引数          ：書き込むファイルのパス(pathlib)、書き込むデータ
# 戻り値        ：書き込み結果
# 備考          ：-
# 依存ライブラリ：json, pathlib
def write_file(path, data):
	try:
		# フォルダが無い場合作成(作成済みでもok)
		path.parent.mkdir(parents=True, exist_ok=True)
		# bytes型(icsファイル)かチェック
		if isinstance(data, bytes):
			with open(path, mode='wb') as f:
				f.write(data)
		else:
			with open(path, mode='w', encoding='utf-8') as f:
				f.write(data)
		
		return True
	except Exception:
		# 書き込み失敗で空のファイルが生成されていたら削除
		path.unlink(missing_ok=True)
		return False

# 処理内容      ：日時データ取得
# 引数          ：-
# 戻り値        ：実行結果, テキスト
# 備考          ：ESP系マイコンへスリープ可否(0または1)を通知
# 依存ライブラリ：datetime
def get_dl():
	# 現在日時取得
	now = datetime.datetime.now()
	# ファイル有無確認して読み出し
	json_data = load_file()
	if json_data is None:
		# 無ければ作成して再読み出し
		if not create_dl(now.year):
			return False, '1'
		json_data = load_file()
	
	# 月・日から対象のデータを抽出(0(許可)または1(禁止))
	return True, json_data[str(now.month)][str(now.day)]

# 処理内容      ：日時データ作成
# 引数          ：処理対象の年
# 戻り値        ：実行結果
# 備考          ：現在の年よりESP系マイコン通知用のデータを作成
# 依存ライブラリ：pathlib, json, icalendar
def create_dl(year):
	# 月曜日始めでオブジェクト作成
	cal = calendar.Calendar(firstweekday=6)
	# コレクション作成
	date_list = {}
	# 出力年を保存
	date_list['year'] = str(year)
	# 月ごと(1～12)でループ
	for month in range(1, 13):
		# 日付格納リスト
		day_list = {}
		# 月ごとの(日付, 曜日)のタプルが入ったリストでループ
		for day, weekday in cal.itermonthdays2(year, month):
			# 0埋めされた存在しない日にちは除外
			if day == 0:
				continue
			# 初期値(スリープ許可)をセット
			day_list[str(day)] = '0'
		
		# 月ごとに格納
		date_list[str(month)] = day_list
	
	# JSONファイルへ出力(新規作成 or 上書き)
	if not write_file(JSON_FILE, json.dumps(date_list, indent=4)):
		return False
	
	return True


# 処理内容      ：HTML表示用データ取得
# 引数          ：表示対象の月
# 戻り値        ：表示データ
# 備考          ：GET/POST共通処理
# 依存ライブラリ：datetime
def get_html(month):
	# 月制限(min→maxで比較)
	month = max(1, min(month, 12))

	json_data = load_file()
	if json_data is None:
		return {
			'status' : False,
			'message': 'JSONファイルが存在しません'
		}

	year = int(json_data['year'])
	# 指定した月の日にち(キー)を数字変換し、最大値(月末)を取得
	last_day = max(map(int, json_data[str(month)]))

	day_list = []
	for day in range(1, last_day + 1):
		weekday = datetime.date(year, month, day).weekday()
		day_list.append({
			'day'    : day,
			'weekday': WEEKDAY_STR[weekday],
			'checked': (json_data[str(month)][str(day)] == '1') # '1'ならTrue(チェック)
		})

	return {
		'status'    : True,
		'year'      : year,
		'month'     : month,
		'prev_month': 12 if month == 1 else month - 1, # 現在値が1なら前の値を12に設定
		'next_month': 1 if month == 12 else month + 1, # 現在地が12なら次の値を1に設定
		'day_list'  : day_list
	}


# 処理内容      ：チェック状態更新
# 引数          ：月、POSTデータ
# 戻り値        ：実行結果、更新メッセージ
# 備考          ：POST用処理
# 依存ライブラリ：datetime, json
def update_html(month, post_data):
	# 読み出し
	json_data = load_file()
	if json_data is None:
		return False, 'JSONファイルが存在しません'
	# POSTで取得したデータで更新
	month_str = str(month)
	for day_str in json_data[month_str]:
		if post_data.get(day_str):
			json_data[month_str][day_str] = '1'
		else:
			json_data[month_str][day_str] = '0'
	# 書き込み
	if not write_file(JSON_FILE, json.dumps(json_data, indent=4)):
		return False, 'JSON保存に失敗しました'
	# ics更新、rcloneで同期
	if not create_ics():
		return False, 'ICS生成に失敗しました'
	
	return True, '更新しました'

# 処理内容      ：icsデータ作成
# 引数          ：-
# 戻り値        ：実行結果
# 備考          ：icsファイルを生成
# 依存ライブラリ：pathlib, icalendar
def create_ics():
	# ファイル有無確認して読み出し
	json_data = load_file()
	if json_data is None:
		return False
	
	cal = Calendar()
	# VCALENDAR部分
	cal.add('CALSCALE', 'GREGORIAN')
	cal.add('PRODID', '-//upat//JP')
	cal.add('VERSION', '2.0')
	cal.add('METHOD', 'PUBLISH')
	cal.add('X-WR-CALNAME', 'schedule calendar by upat')
	cal.add('X-WR-TIMEZONE', 'Asia/Tokyo')
	# 以下はiPhone用
	cal.add('X-PUBLISHED-TTL', 'PT12H')
	cal.add('REFRESH-INTERVAL;VALUE=DURATION', 'PT12H')
	
	# 年だけ先に取得
	year = int(json_data.pop('year'))
	for month_str, days in json_data.items():
		# 月
		month = int(month_str)
		# 日
		for day_str, value in days.items():
			# 1以外はスキップ
			if value != '1':
				continue
			
			day = int(day_str)
			schedule_start = datetime.date(year, month, day)
			schedule_end = schedule_start + datetime.timedelta(days=1) # 1日足す(終日)

			event = Event()
			# UID固定化（再生成でも同一イベント扱い）
			event.add('UID', f'{schedule_start.isoformat()}@upat')
			event.add('SUMMARY', '休み')
			# 終日イベント
			event.add('DTSTART', schedule_start)
			event.add('DTEND', schedule_end)
			# データ追加
			cal.add_component(event)

	# ICSファイルへ出力(新規作成 or 上書き)
	if not write_file(ICS_FILE, cal.to_ical()):
		return False
	
	return True
