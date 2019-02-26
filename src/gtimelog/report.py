from datetime import datetime, time
import argparse
import sys

from gtimelog.settings import Settings
from gtimelog.timelog import TimeLog, Reports


def weekly_report():
    parser = argparse.ArgumentParser(
        description=u'Show the progress of the current week')
    parser.add_argument(
        '--day',
        metavar='YYYY-MM-DD',
        default=datetime.today().strftime('%Y-%m-%d'),
        help='Day of the week the progress should be calculated for. '
             '(default: today)')
    args = parser.parse_args()
    date = datetime.strptime(args.day, '%Y-%m-%d')

    SETTINGS = Settings()
    SETTINGS.load()
    TIMELOG = TimeLog(SETTINGS.get_timelog_file(), time(0, 0))
    window = TIMELOG.window_for_week(date)
    reports = Reports(window, email_headers=False)
    reports.weekly_report_categorized(sys.stdout, '', '')
