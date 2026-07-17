#!/usr/bin/env python3
# coding: UTF-8
import json, urllib.request
from bs4 import BeautifulSoup
from pathlib import Path, PureWindowsPath
from mutagen import File

##### ↓↓↓使用環境により適宜編集↓↓↓ #####
# 実行ファイルの絶対パスの親ディレクトリ×2+出力ファイルの相対パス
FILE_NAME = Path(__file__).resolve().parent.parent / 'json' / 'nowplaying.json'
# 再生中の楽曲情報URL
NOWPLAYING_URL = 'http://127.0.0.1:13579/variables.html'
##### ↑↑↑使用環境により適宜編集↑↑↑ #####
AUDIO_EXTS = {'.mp3', '.flac'}

# 処理内容      ：データ書き込み関数
# 引数          ：アーティスト名, タイトル名
# 戻り値        ：-
# 備考          ：-
# 依存ライブラリ：json, pathlib
def write(artist, title):
	# JSONデータ作成
	write_data = {
		'artist' : artist,
		'title' : title
	}
	# 差分があれば書き込む
	if load() != write_data:
		# フォルダが無い場合作成(作成済みでもok)
		FILE_NAME.parent.mkdir(parents=True, exist_ok=True)
		# JSONファイルへ出力(新規作成 or 上書き)
		with open(FILE_NAME, mode='w', encoding='utf-8') as f:
			json.dump(write_data, f, indent=4, ensure_ascii=False)

# 処理内容      ：データ読み出し関数
# 引数          ：-
# 戻り値        ：JSONオブジェクト
# 備考          ：-
# 依存ライブラリ：json, pathlib
def load():
	# 読み出し失敗時の初期値
	default_data = {
		'artist' : 'no data',
		'title' : 'no data'
	}
	# 読み出し失敗(空ファイル、破損ファイル含む)の場合は初期値を返す
	try:
		with open(FILE_NAME, 'r', encoding='utf-8') as f:
			return json.load(f) # loadsはJSON文字列をPythonオブジェクト化
	except (json.JSONDecodeError, OSError):
		return default_data

# 処理内容      ：Webページアクセス、データ抽出・保存
# 引数          ：-
# 戻り値        ：-
# 備考          ：MPC-HCのウェブインターフェースを使用
# 依存ライブラリ：urllib, bs4, mutagen, pathlib
def update():
	# 出力変数の初期化
	artist_str = 'no data'
	title_str = 'no data'
	
	# URLにアクセス
	try:
		with urllib.request.urlopen(NOWPLAYING_URL, timeout=3) as res:
			html_src = res.read()
	except Exception:
		write(artist_str, title_str)
		return
		
	# HTMLから再生しているWindowsファイルパスを取得
	bs_htmlsrc = BeautifulSoup(html_src, 'html.parser')
	bs_pfilepath = bs_htmlsrc.find('p', id='filepath')
	if bs_pfilepath is not None:
		bs_pfilepath = bs_pfilepath.get_text()
		# パースしてWindowsファイルパスからドライブレターを抜く
		winpath = PureWindowsPath(bs_pfilepath)
		winpath_parts = winpath.parts[1:]
		# 結合してunixファイルパスに変換
		unixpath = Path('/mnt/hdd', *winpath_parts)
		# パスが存在し、指定した拡張子であればタグ読み出し
		if unixpath.exists() and (unixpath.suffix.lower() in AUDIO_EXTS):
			try:
				tag_info = File(unixpath, easy=True)
			except Exception:
				tag_info = None # 破損ファイル読み出しを考慮
			if tag_info is not None:
				artist_str = tag_info.get('artist', [''])[0]
				title_str = tag_info.get('title', [''])[0]
	# 書き込み
	write(artist_str, title_str)
