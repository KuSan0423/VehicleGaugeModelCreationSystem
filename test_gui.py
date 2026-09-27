"""ウィンドウを非表示で生成し、実際の入力変数と更新処理をテストする。"""
import time
import tkinter as tk
from gui import App
from geometry import dimensions

root=tk.Tk();root.withdraw();app=App(root)
try:
    app.update_preview();root.update_idletasks()
    assert dimensions(app.current)['length']==41
    original=app.preview.tobytes()
    app.vars['lengths_mm'].set('15000, 10000, 14250')
    # Exercise the real debounce event rather than only calling the drawing function.
    root.after(350,root.quit);root.mainloop()
    assert dimensions(app.current)['length']==41.75
    assert app.preview.tobytes()!=original
    app.vars['gaps_mm'].set('100, 100');app.update_preview()
    assert app.current is None
    assert str(app.test_button['state'])=='disabled'
    app.vars['gaps_mm'].set('1000, 1000');app.update_preview()
    assert app.current is not None
    app.selected.set('2');app.update_preview();root.update_idletasks()
    print('GUI: live update, invalid input, recovery, car selection OK')
finally:
    root.destroy()
