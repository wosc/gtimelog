import datetime

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import FormattedTextToolbar

from gtimelog.settings import Settings
from gtimelog.timelog import TimeLog, different_days, as_minutes


def format_duration(duration):
    h, m = divmod(as_minutes(duration), 60)
    return '%s h %02d min' % (h, m)


class LogControl(BufferControl):

    def __init__(self):
        self.log_buffer = Buffer()
        super(LogControl, self).__init__(buffer=self.log_buffer)

    def render(self):
        window = TIMELOG.window_for_day(today)
        total = datetime.timedelta(0)
        prev = None
        for item in window.all_entries():
            first_of_day = prev is None or different_days(
                prev, item.start, TIMELOG.virtual_midnight)
            if first_of_day and prev is not None:
                self.w("\n")
            self.write_item(item)
            total += item.duration
            prev = item.start

    def write_item(self, item):
        self.w(format_duration(item.duration), 'duration')
        self.w(' ')
        period = '({0:%H:%M}-{1:%H:%M})'.format(item.start, item.stop)
        self.w(period, 'time')
        self.w(' ')
        tag = ('slacking' if '**' in item.entry else None)
        self.w(item.entry + '\n', tag)

    def w(self, text, tag=None):
        self.log_buffer.text += text



class Statusbar(FormattedTextToolbar):

    def __init__(self):
        super(Statusbar, self).__init__('', style='reverse')

    def render(self):
        window = TIMELOG.window_for_day(today)
        total_work, total_slacking = window.totals()
        time_left = self.time_left_at_work(total_work)
        time_to_leave = datetime.datetime.now() + time_left
        if time_left < datetime.timedelta(0):
            time_left = datetime.timedelta(0)
        weekly_window = TIMELOG.window_for_week(today)
        week_total_work, week_total_slacking = weekly_window.totals()

        self.content.text = (
            'Work done: %s (%s this week), Time left: %s (till %s)' % (
                format_duration(total_work),
                format_duration(week_total_work),
                format_duration(time_left),
                time_to_leave.strftime('%H:%M')))

    def time_left_at_work(self, total_work):
        total_time = total_work  # + self.get_current_task_work_time()
        return datetime.timedelta(hours=SETTINGS.hours) - total_time


class InputControl(BufferControl):

    keys = KeyBindings()

    def __init__(self):
        self.input_buffer = Buffer(multiline=False)
        super(InputControl, self).__init__(
            buffer=self.input_buffer,
            key_bindings=self.keys)


LogWindow = Window(LogControl())
StatusToolbar = Statusbar()
InputToolbar = Window(InputControl(), dont_extend_height=True, height=1)

today = datetime.date.today()
root = HSplit([
    FormattedTextToolbar(
        ' ctimelog: %s (week %02d)' % (
            today.strftime('%A, %Y-%m-%d'), int(today.strftime('%W')) + 1),
        style='reverse'),
    LogWindow,
    StatusToolbar,
    InputToolbar,
])
layout = Layout(root)
global_keys = KeyBindings()


@global_keys.add('c-q')
def quit(event):
    event.app.exit()


TIMELOG = None


def main():
    global TIMELOG, SETTINGS
    SETTINGS = Settings()
    TIMELOG = TimeLog(SETTINGS.get_timelog_file(), datetime.time(0, 0))
    app = Application(layout=layout, full_screen=True, key_bindings=global_keys)
    LogWindow.content.render()
    StatusToolbar.render()
    layout.focus(InputToolbar)
    app.run()
