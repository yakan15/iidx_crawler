# Beatmania IIDX用スコアクローラー
## requirements
```
selenium==3.14.0
lxml==4.2.4
```
また、Google Chrome及び対応する[ChromeDriver](https://chromedriver.chromium.org)が必要。  

## ログイン設定
`config/config.json`のID, Passwordには, 自分が使用するログインID, Passwordを記述する。

## 機能
- ユーザーID取得
- ユーザーの詳細プレイヤー情報（プレイヤーページトップに記載された情報）取得
- ユーザーの難易度別スコア情報取得

なお、プロフィール非公開のユーザーのデータは取得できない。

各機能別の呼び出しスクリプトは作成していないため、使用してみたい場合は適宜main関数を書き換えるべし。

## 実行
```
python3 iidx_crawler.py iidx27
```
`iidx27`の項目の引数は、config/config.jsonのkeyの名前。
pullしたまま使用した場合、`player_data/sample.json`をもとに、各プレイヤーのレベル12のスコア取得を開始する。
