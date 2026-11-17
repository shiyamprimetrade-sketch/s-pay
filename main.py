"""S-Pay offline Android prototype. All funding actions are simulations."""
from pathlib import Path
from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from database import Store, breakdown, dollars

BLACK = (0.071, 0.071, 0.071, 1)
GOLD = (0.831, 0.686, 0.216, 1)
GREEN = (0, 0.902, 0.463, 1)
WHITE = (0.95, 0.95, 0.95, 1)

class SwipeButton(Button):
    def __init__(self, on_swipe=None, **kwargs):
        super().__init__(**kwargs)
        self._start = None
        self.on_swipe_right = on_swipe

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._start = touch.pos
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._start and self.collide_point(*touch.pos) and touch.x - self._start[0] > dp(85):
            self._start = None
            if self.on_swipe_right:
                self.on_swipe_right()
            return True
        self._start = None
        return super().on_touch_up(touch)

class SPay(App):
    def build(self):
        Window.clearcolor = BLACK
        self.store = Store(Path(self.user_data_dir) / 'spay.db')
        self.user = None
        self.root_box = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        self.show_auth()
        return self.root_box

    def label(self, text, color=WHITE, height=45):
        return Label(text=text, color=color, size_hint_y=None, height=dp(height), halign='center', valign='middle', text_size=(Window.width-dp(40),None))

    def btn(self, text, action, color=GOLD):
        b = Button(text=text, size_hint_y=None, height=dp(52), background_normal='', background_color=color, color=BLACK)
        b.bind(on_release=lambda *_: action())
        return b

    def field(self, hint, password=False):
        return TextInput(hint_text=hint, multiline=False, password=password, size_hint_y=None, height=dp(52), background_color=(.16,.16,.16,1), foreground_color=WHITE, hint_text_color=(.65,.65,.65,1))

    def page(self, heading):
        self.root_box.clear_widgets()
        self.root_box.add_widget(self.label('S-PAY  |  OFFLINE DEMO', GOLD, 45))
        self.root_box.add_widget(self.label(heading, WHITE, 48))
        scroll = ScrollView()
        self.body = BoxLayout(orientation='vertical', spacing=dp(12), size_hint_y=None)
        self.body.bind(minimum_height=self.body.setter('height'))
        scroll.add_widget(self.body)
        self.root_box.add_widget(scroll)
        self.message = self.label('No real payments or bank transfers occur.', GREEN, 55)
        self.root_box.add_widget(self.message)

    def notice(self, message):
        self.message.text = message

    def show_auth(self):
        self.page('Choose a demo profile')
        name = self.field('Username (not a secure login)')
        role = Spinner(text='poster', values=('poster','billionaire'), size_hint_y=None, height=dp(52))
        self.body.add_widget(name)
        self.body.add_widget(role)
        self.body.add_widget(self.btn('Create local demo profile', lambda: self.register(name.text,role.text)))
        self.body.add_widget(self.btn('Open existing demo profile', lambda: self.login(name.text)))
        self.body.add_widget(self.label('Demo profiles have NO password authentication. Do not enter real bank details.', height=85))

    def register(self, username, role):
        try:
            self.store.register(username,role)
            self.login(username)
        except ValueError as e:
            self.notice(str(e))

    def login(self, username):
        user = self.store.login(username)
        if user is None:
            self.notice('Profile not found')
            return
        self.user = dict(user)
        self.dashboard()

    def dashboard(self):
        if self.user['role'] == 'poster':
            self.poster()
        else:
            self.feed()

    def nav(self):
        self.body.add_widget(self.btn('Revenue ledger (demo)', self.ledger))
        self.body.add_widget(self.btn('Switch profile', self.show_auth))

    def poster(self):
        self.page('Poster: ' + self.user['username'])
        title = self.field('Bill title')
        amount = self.field('Requested USD amount, e.g. 100.00')
        desc = self.field('Description (no sensitive data)')
        self.body.add_widget(title)
        self.body.add_widget(amount)
        self.body.add_widget(desc)
        preview = self.label('Enter an amount to preview the fee', GOLD, 75)
        self.body.add_widget(preview)
        def refresh(*_):
            try:
                base, fee, total = breakdown(amount.text)
                preview.text = f'Requested: {dollars(base)}\nSupporter fee (2%): {dollars(fee)} | Total: {dollars(total)}'
            except ValueError:
                preview.text = 'Enter a valid USD amount'
        amount.bind(text=refresh)
        self.body.add_widget(self.btn('Post demo bill', lambda: self.post(title.text,desc.text,amount.text)))
        self.body.add_widget(self.label('My bills', GOLD))
        for bill in self.store.bills(poster_id=self.user['id']):
            self.body.add_widget(self.label(f"#{bill['id']} {bill['title']} · {dollars(bill['base_cents'])} · {bill['status']}",height=60))
        self.nav()

    def post(self, title, desc, amount):
        try:
            self.store.create_bill(self.user['id'],title,desc,amount)
            self.poster()
            self.notice('Demo bill saved locally. No funds requested from a bank.')
        except ValueError as e:
            self.notice(str(e))

    def feed(self):
        self.page('Supporter: ' + self.user['username'])
        bills = self.store.bills(pending_only=True)
        if not bills:
            self.body.add_widget(self.label('No pending demo bills', height=75))
        for bill in bills:
            self.body.add_widget(self.label(f"{bill['title']} · by {bill['poster']}\n{bill['description']}\nRequested {dollars(bill['base_cents'])} + fee {dollars(bill['fee_cents'])} = {dollars(bill['total_cents'])}",height=130))
            bill_id = bill['id']
            swipe = SwipeButton(text='Swipe right or tap to DEMO FUND', size_hint_y=None, height=dp(62), background_normal='', background_color=GREEN, color=BLACK, on_swipe=lambda bid=bill_id: self.fund(bid))
            swipe.bind(on_release=lambda _btn, bid=bill_id: self.fund(bid))
            self.body.add_widget(swipe)
        self.nav()

    def fund(self, bill_id):
        try:
            self.store.demo_fund(self.user['id'],bill_id)
            self.feed()
            self.notice('SIMULATED ONLY. No charge, donation or settlement occurred.')
        except ValueError as e:
            self.notice(str(e))

    def ledger(self):
        self.page('Simulation ledger — NOT revenue')
        summary = self.store.summary()
        self.body.add_widget(self.label(f"Demo funding events: {summary['n']}\nSimulated bill allocations: {dollars(summary['base'])}\nSimulated service fees: {dollars(summary['fees'])}", GOLD, 130))
        self.body.add_widget(self.label('All values are illustrative. Actual disbursed donations and earned revenue: $0.00.',height=100))
        self.body.add_widget(self.btn('Back to dashboard', self.dashboard))

if __name__ == '__main__':
    SPay().run()
