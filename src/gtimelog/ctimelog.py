import datetime
import io

from prompt_toolkit import HTML
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import FormattedTextToolbar

from gtimelog.settings import Settings
from gtimelog.timelog import TimeLog, different_days, as_minutes


def format_duration(duration):
    h, m = divmod(as_minutes(duration), 60)
    return '%s h %02d min' % (h, m)


class LogControl(FormattedTextControl):

    def render(self):
        self.output = io.StringIO()
        window = TIMELOG.window_for_day(today)
        total = datetime.timedelta(0)
        prev = None
        for item in window.all_entries():
            first_of_day = prev is None or different_days(
                prev, item.start, TIMELOG.virtual_midnight)
            if first_of_day and prev is not None:
                self.w('\n')
            tag = 'slacking' if first_of_day else None
            self.write_item(item, tag)
            total += item.duration
            prev = item.start
        self.text = HTML(self.output.getvalue())

    def write_item(self, item, tag=None):
        self.w(format_duration(item.duration), 'duration')
        self.w(' ')
        period = '({0:%H:%M}-{1:%H:%M})'.format(item.start, item.stop)
        self.w(period, 'time')
        self.w(' ')
        tag = ('slacking' if '**' in item.entry else tag)
        self.w(item.entry + '\n', tag)

    TAGS = {
        'duration': 'red',
        'time': 'green',
        'slacking': 'blue',
    }

    def w(self, text, tag=None):
        if tag:
            text = '<ansi{color}>{text}</ansi{color}>'.format(
                text=text, color=self.TAGS[tag])
        self.output.write(text)


class Statusbar(FormattedTextToolbar):

    def __init__(self):
        super(Statusbar, self).__init__('')

    def render(self):
        window = TIMELOG.window_for_day(today)
        total_work, total_slacking = window.totals()
        time_left = self.time_left_at_work(total_work)
        time_to_leave = datetime.datetime.now() + time_left
        if time_left < datetime.timedelta(0):
            time_left = datetime.timedelta(0)
        weekly_window = TIMELOG.window_for_week(today)
        week_total_work, week_total_slacking = weekly_window.totals()

        self.content.text = HTML(
            'Work done: <ansired>%s</ansired> '
            '(<ansigreen>%s</ansigreen> this week) '
            'Time left: <ansired>%s</ansired> '
            '(till <ansigreen>%s</ansigreen>)' % (
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


@InputControl.keys.add('enter')
def add_entry(event):  # Does not seem to support methods, sigh.
    entry = InputToolbar.content.input_buffer.text
    if not entry:
        return
    InputToolbar.content.input_buffer.text = ''
    TIMELOG.append(entry, now=None)
    LogWindow.content.render()


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
