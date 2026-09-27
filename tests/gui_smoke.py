"""ウィンドウを非表示で生成し、実際の入力変数と更新処理をテストする。"""
import time
import tkinter as tk
from rail_clearance.gui import App
from rail_clearance.geometry import dimensions

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
    app.vars['lengths_mm'].set('')
    app.vars['bogie_spacings_mm'].set('11750,11000,11750')
    app.vars['total_length_mm'].set('41000');app.update_preview()
    assert app.current['lengths_mm']==[None,None,None]
    assert dimensions(app.current)['length']==41
    assert '14,250' in app.calculated_vars['lengths_mm'].get()
    assert app.vars['lengths_mm'].get()==''
    app.vars['total_length_mm'].set('40000');app.update_preview()
    assert app.current is None and '矛盾' in app.error.get()
    assert str(app.test_button['state'])=='disabled'
    app.vars['total_length_mm'].set('41000')
    app.vars['bogie_spacings_mm'].set('');app.update_preview()
    assert app.current is None and '条件不足' in app.error.get()
    app.vars['lengths_mm'].set(',10000,14250');app.update_preview()
    assert app.current is not None and app.error.get()==''
    assert dimensions(app.current)['length']==41
    app.vars['total_length_mm'].set('')
    app.vars['lengths_mm'].set(',10000,')
    app.vars['coupling_face_to_shared_mm'].set('15000,15000');app.update_preview()
    assert app.current is not None and dimensions(app.current)['length']==41
    assert '15,000' in app.calculated_vars['coupling_face_to_shared_mm'].get()
    app.vars['lengths_mm'].set('14250,10000,14250')
    app.vars['coupling_face_to_shared_mm'].set('15500,15000');app.update_preview()
    assert app.current is None and '矛盾' in app.error.get()
    app.vars['coupling_face_to_shared_mm'].set('');app.update_preview()
    assert app.current is not None and app.error.get()==''
    assert app.vars['coupling_face_to_shared_mm'].get()==''
    print('GUI: live update, face distance constraints, conflicts, underconstraint, recovery OK')
finally:
    root.destroy()
