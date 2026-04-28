"""
ひふみ旅館 週次KPIチェックスクリプト
毎週月曜日にGitHub Actionsから実行される

処理内容：
1. 今週（月〜日）の稼働率・売上実績をStayseeから取得
2. 前年同週の日別売上を曜日タイプ別に取得・補正
3. 目標値（前年曜日補正 × 105%）と比較
4. 目標の90%を下回っていたらLINEに通知
"""

import os
import sys
import json
import requests
import jpholiday
from datetime import date, timedelta, datetime
from collections import defaultdict