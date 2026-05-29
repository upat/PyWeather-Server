#!/usr/bin/env python3
# coding: UTF-8
import re, json, datetime
from bs4 import BeautifulSoup
from pathlib import Path
from dataclasses import dataclass
# chromium用 Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
# chromium用 Selenium 待機時間用インポート
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

##### ↓↓↓使用環境により適宜編集↓↓↓ #####
# 実行ファイルの絶対パスの親ディレクトリ×2+出力ファイルの相対パス
FILE_NAME = Path(__file__).resolve().parent.parent / 'json' / 'jma.json'
# 気象庁 アメダス(10分毎)URL
JMA_10MIN_URL = 'https://www.jma.go.jp/bosai/amedas/#area_type=offices&area_code=130000&amdno=44132&format=table10min&elems=53414'
# 再読み出し許可の時間(300秒=5分)
INTERVAL_SECOND = 300
##### ↑↑↑使用環境により適宜編集↑↑↑ #####
# 日時フォーマット
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
# 日時初期値(テキスト、datetimeオブジェクト)
INIT_DATE = '2000-01-01 00:00:00'
INIT_DATETIME = datetime.datetime.strptime(INIT_DATE, DATE_FORMAT)
# 正規表現PATTERN
TEMP_PATTERN = re.compile('^-?[0-9]+\.?[0-9]*$') # 温度(氷点下温度も考慮)
HUMI_PATTERN = re.compile("^\d+\.?\d*\Z")        # 湿度
BARO_PATTERN = re.compile("^\d+\.?\d*\Z")        # 気圧
# 文字列デフォルト値
DEFAULT_TIME = '--:--'
DEFAULT_TEMP = '--.-'
DEFAULT_HUMI = '--'
DEFAULT_BARO = '----.-'

# 気象データdataclass
@dataclass
class WeatherData:
	time_data : str = DEFAULT_TIME
	temp_data : str = DEFAULT_TEMP
	humi_data : str = DEFAULT_HUMI
	baro_data : str = DEFAULT_BARO
	
	# 処理内容      ：気象庁アメダス データセットHelper関数
	# 引数          ：bs4オブジェクト
	# 戻り値        ：一部データ設定したクラスオブジェクト
	# 備考          ：-
	# 依存ライブラリ：-
	@classmethod
	def create(cls, bs_amdtabletr):
		return cls(
			time_data = bs_amdtabletr.find_all('td')[1].get_text(),
			temp_data = bs_amdtabletr.find('td', attrs={'class': 'td-temp'}).get_text(),
			humi_data = bs_amdtabletr.find('td', attrs={'class': 'td-humidity'}).get_text(),
			baro_data = bs_amdtabletr.find('td', attrs={'class': 'td-normalPressure'}).get_text(),
		)
	
	# 処理内容      ：データチェック関数
	# 引数          ：-
	# 戻り値        ：-
	# 備考          ：数値ではなかった場合の処理(時々発生する気象庁の測定ミス対策)
	# 依存ライブラリ：-
	def check(self):
		if self.time_data.find(':') == -1:
			self.time_data = DEFAULT_TIME
		if not bool(TEMP_PATTERN.match(self.temp_data)):
			self.temp_data = DEFAULT_TEMP
		if not bool(HUMI_PATTERN.match(self.humi_data)):
			self.humi_data = DEFAULT_HUMI
		if not bool(BARO_PATTERN.match(self.baro_data)):
			self.baro_data = DEFAULT_BARO
		
		return self
	
	# 処理内容      ：データ書き込み関数
	# 引数          ：処理開始時間
	# 戻り値        ：-
	# 備考          ：-
	# 依存ライブラリ：datetime, json, pathlib
	def write(self, start_time = INIT_DATE):
		# JSONデータ作成(ページの読み出しが全て失敗した場合、前回更新日時or初期日時と全てハイフンのデータをセット)
		write_data = {
			'last_update' : {
				'timestamp' : start_time
			},
			'weather' : {
				'time' : self.time_data,
				'temp' : self.temp_data,
				'humi' : self.humi_data,
				'baro' : self.baro_data
			}
		}
		# フォルダが無い場合作成(作成済みでもok)
		FILE_NAME.parent.mkdir(parents=True, exist_ok=True)
		# JSONファイルへ出力(新規作成 or 上書き)
		with open(FILE_NAME, mode='w') as f:
			json.dump(write_data, f, indent=4)

# 処理内容      ：Webページアクセス、データ抽出・保存
# 引数          ：-
# 戻り値        ：実行結果
# 備考          ：温度・湿度・気圧のテキストデータを抽出後、JSONファイルへ保存
#                 ただし、同一時間内のWebページアクセスは5分経過するまで不可(JSONファイル保存データで制御)
# 依存ライブラリ：datetime, json, selenium, bs4
def update_jma():
	# 現在時刻を取得
	now = datetime.datetime.now()
	# 日時データ取得
	try:
		with open(FILE_NAME, mode='r') as f:
			# 最終保存時刻を取得
			read_data = json.load(f)
			read_lasttime = read_data['last_update']['timestamp']
			read_lastdatetime = datetime.datetime.strptime(read_lasttime, DATE_FORMAT)
	except (FileNotFoundError, json.JSONDecodeError):
		read_lastdatetime = INIT_DATETIME
	
	# 前回の実行から5分以上経過していること
	if INTERVAL_SECOND < (now - read_lastdatetime).total_seconds():
		# chrome設定
		chrome_options = Options()
		chrome_options.add_argument('--headless')    # ヘッドレスモード有効(画面表示を行わない)(必須)
		chrome_options.add_argument('--disable-gpu') # GPUを使用しない(無いと不安定になる)
		chrome_service = Service('/usr/bin/chromedriver')
		
		# 読み出し実行
		chrome_webdriver = None
		try:
			# ChromeのWebDriverオブジェクトを作成する。
			chrome_webdriver = webdriver.Chrome(service=chrome_service, options=chrome_options)
			# ページ読み込み
			chrome_webdriver.get(JMA_10MIN_URL)
			# chrome_webdriver.get()後の描画で指定class(湿度データ)が読み込まれるまでの待機時間(20s)
			# chrome_webdriver.get()以前に実施すると描画前のhtml読み出しの状態でclass待機するので注意
			WebDriverWait(chrome_webdriver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'td-normalPressure')))
			# ページのソース取得
			html_src = chrome_webdriver.page_source
		finally: # タイムアウト
			# chromiumを閉じる
			chrome_webdriver.quit()
		
		# HTMLパース
		try:
			# table要素を取得し、tr要素のclass名から目的のデータ(行)を検索
			bs_htmlsrc = BeautifulSoup(html_src, 'html.parser')
			bs_amdtable = bs_htmlsrc.find('table', attrs={'class': 'amd-table-seriestable'})
			for tr in bs_amdtable.find_all('tr'):
				if 'amd-table-tr-' in tr['class'][0]:
					bs_amdtabletr = tr
					break
			# 気象データ読み出し＆データチェック
			weather_data = WeatherData.create(bs_amdtabletr).check()
			# 書き込み
			weather_data.write(now.strftime(DATE_FORMAT))
		except AttributeError:
			# 初期値で書き込み
			weather_data = WeatherData()
			weather_data.write()
			return False
	
	# レスポンス
	return True

# 処理内容      ：データ取得
# 引数          ：短縮モードフラグ
# 戻り値        ：実行結果, テキスト
# 備考          ：JSONファイルを読み出し、読みだしたテキストを返す
# 依存ライブラリ：json, pathlib
def get_jma(short_mode=False):
	if FILE_NAME.exists():
		# 日時データ取得
		with open(FILE_NAME, mode='r') as f:
			# jsonファイルよりデータ取得
			json_txt = json.load(f)
			# 応答データ作成
			if short_mode:
				# 短縮版
				response = (
					f"{json_txt['weather']['humi']}%  "
					f"{json_txt['weather']['temp']}"
				)
			else:
				response = (
					f"{json_txt['weather']['baro']}hPa "
					f"{json_txt['weather']['humi']}% "
					f"{json_txt['weather']['temp']}"
				)
	else:
		# ファイルが存在しない場合
		if short_mode:
			# 短縮版
			response = '---%  ---.-'
		else:
			response = '----.-hPa ---% ---.-'
		# 実行結果
		return False, response
	
	# 実行結果
	return True, response
