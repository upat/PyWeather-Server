# PyWeather-Server

概要
---
気象庁データの取得と接続デバイスの管理を行う簡易HTTPサーバー

機能
---
- 任意のタイミングで以下の処理を実行
    - 指定した観測地点の気象庁アメダス(10分毎)のページから取得した温度・湿度・気圧のデータをJSONファイルへ保存
    - HDDのSMART情報を取得し、結果を保存
    - 日にち毎のスリープ可否情報を使用して、HDD(接続デバイス)をアンマウント＆電源断
    - (初回起動時や年末を想定)日にち毎のスリープ可否情報を生成
- 保存した温度・湿度・気圧のデータを返す
- 指定した日の日にち毎のスリープ可否情報を返す。マイコン側はこれを利用してスリープ可否を判定する
- ルートディレクトリにWebアクセスすると、日にち毎のスリープ可否情報を編集可能
- 編集した日にち毎のスリープ可否情報をicalendar形式で出力し、同一ネットワーク内の端末からカレンダーとして参照できるようにする

開発・動作環境
---
- Raspberry Pi 3 Model B+(サーバー)
    - Raspberry Pi OS (Debian 12 Bookworm, 64-bit), Linux 6.12.87+rpt-rpi-v8
    - chromedriver 147.0.7727.101
    - smartctl 7.3
    - hub-ctrl
    - Python 3.11.2
        | Package | Version |
        |---------|---------|
        | beautifulsoup4 | 4.14.3 |
        | Flask | 3.1.3 |
        | icalendar | 7.1.2 |
        | selenium | 4.44.0 |
- ESP32+ILI9341(クライアント)
    - [ntp_clock_tft_esp32](https://github.com/upat/ntp_clock_tft_esp32)
- ESP8266+SSD1306(クライアント)
    - [ntp_clock](https://github.com/upat/ntp_clock)

使い方(あくまで参考例のため、ファイルパスやIPアドレスの編集必須)
---
1. 各種必要パッケージのインストール(Pythonは仮想環境で構成)
1. `run.sh` 、 `hdd_info.py` のデバイス名、 `jma.py` のアメダスURL を環境に合わせて編集
1. ```./run.sh``` を実行
- crontab(タスクスケジューラ)を使用する場合は以下のようにする(参考)
```
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=""
*/10 * * * * bash -l -c 'curl -XPOST http://127.0.0.1:8080/update_jma'
0 7,19 * * * bash -l -c 'curl -XPOST http://127.0.0.1:8080/hdd_info'
55 23 31 12 * bash -l -c 'curl -XPOST http://127.0.0.1:8080/create_dl'
20 8 * * * bash -l -c 'curl -XPOST http://127.0.0.1:8080/umount_hdd'
@reboot bash -l -c 'run.sh'
55 17 * * * sudo /sbin/reboot
```

ファイル・フォルダ構成
---
- json(実行時自動作成)
    - JSONファイルの保存先
- log(実行時自動作成)
    - `pyserver.py` の動作ログ、 `hdd_info.py` のデバイス情報の保存先
- ics(実行時自動作成)
    - icalendarファイルの保存先
- templates
    - Flaskで使用するテンプレートhtml
- lib
    - pyserver.pyからHTTPリクエストにより呼び出されるモジュール
- LICENSE
    - ライセンスファイル
- pyserver.py
    - 実行ファイル
- README.md
    - このファイル
- run.sh
    - pyserver.pyをバックグラウンド動作させるスクリプト

使用上の注意
---
スクレイピングの最低取得間隔は300sで設定しています。
取得元サーバーへの負荷を考慮して設定してください。

ライセンス
---
MIT License
