# PyWeather-Server

概要
---
ESP系マイコン等からPOSTリクエストを受信し、天気予報データ等のやりとりを行う

機能
---
- 気象庁のページからスクレイピングした温度・湿度・気圧のデータをJSONファイルへ出力後、マイコンへUDP送信
- 消費電力軽減のため、日にち毎にスリープの可否をマイコンへ通知(時間についてはマイコン側で判断)
- マイコンからの室温アラートを受けるとX(旧Twitter)へテキスト投稿後、サーバーのシャットダウン
- ウェザーニュースのページからスクレイピングした1時間毎の天気予報をJSONファイルへ出力後、送信

開発・動作環境
---
- Raspberry Pi 3 Model B+(サーバー)
    - Raspberry Pi OS 6.1.63-v7
    - Python 3.7.3
        - beautifulsoup4    4.12.2
        - Flask             2.2.5
        - requests          2.31.0
        - requests-oauthlib 1.3.1
- ESP32+ILI9341(クライアント)
    - [ntp_clock_tft_esp32](https://github.com/upat/ntp_clock_tft_esp32)
- ESP8266+SSD1306(クライアント)
    - [ntp_clock](https://github.com/upat/ntp_clock)

使い方
---
1. pyserver.pyの依存ライブラリをpip等から取得
1. `run.sh` `py_func内のコード`を環境に合わせて編集
1. ```./run.sh``` を実行

ファイル・フォルダ構成
---
- json(実行時自動作成)
    - JSONファイルの保存先
- log(実行時自動作成)
    - pyserver.pyの動作ログ保存先
- py_func
    - pyserver.pyからPOSTリクエストにより呼び出される関数の定義
- LICENCE
    - ライセンスファイル
- pyserver.py
    - 実行ファイル
- README.md
    - このファイル
- run.sh
    - pyserver.pyをバックグラウンド動作させるスクリプト

使用上の注意
---
外部サーバーへのリクエスト送信処理が過剰にならないよう注意してください

ライセンス
---
MIT Licence
