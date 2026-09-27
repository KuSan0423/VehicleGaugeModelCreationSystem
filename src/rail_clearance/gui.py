"""Tk設定画面。画像・寸法計算はdrawing/geometryへ分離。"""
import copy
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from PIL import Image,ImageTk
from .configuration import PRESETS,preset,save,load,validate
from .paths import PRESETS_DIR
from .dimension_solver import defaults,OPTIONAL_LISTS,OPTIONAL_SCALARS
from .geometry import dimensions
from .drawing import dimension_image
from .runner import generate,find_blender

FIELDS=[('name','編成名',str),('car_count','車体数',int),
        ('lengths_mm','車体長 [mm]（各車・空欄は自動）',list),
        ('bogie_spacings_mm','台車中心間 [mm]（各車・空欄は自動）',list),
        ('total_length_mm','編成全長 [mm]（空欄は自動）',float),
        ('coupling_face_to_shared_mm','外側連結面 → 内側共有台車中心 [mm]（左,右）',list),
        ('gaps_mm','車体間隔 [mm]（各連接部）',list),
        ('joint_fractions','共有台車位置比率（左車端から）',list),
        ('outer_insets_mm','通常台車：外側車端から内側 [mm]（左,右）',list),
        ('coupler_mm','外端連結器の突出 [mm]（左,右）',list),
        ('radius_m','プレビュー用曲線半径 [m]（0=直線）',float),
        ('test_radii_m','試験半径 [m]（直線は自動追加）',list),
        ('equipment_reserve_mm','機器の端面余裕 [mm]',float),
        ('reference_spacing_m','20m級台車間 [m]（最小,最大,刻み）',list)]

class App:
    def __init__(self,root):
        self.root=root;self.root.title('連接車｜寸法プレビュー・生成・接触試験')
        root.geometry('1440x960');root.minsize(1060,720)
        self.busy=False;self.after_id=None;self.messages=queue.Queue();self.current=None;self.last_result=None
        self.vars={};self.calculated_vars={};self.error=tk.StringVar()
        self.normal=tk.BooleanVar();self.direction=tk.StringVar(value='左曲線')
        self.selected=tk.StringVar(value='1');self.zoom=tk.StringVar(value='全体表示')
        self.blender=tk.StringVar();self.status=tk.StringVar(value='設定を読み込み中')
        pane=ttk.Panedwindow(root,orient='horizontal');pane.pack(fill='both',expand=True)
        control_frame=ttk.Frame(pane);viewer=ttk.Frame(pane);pane.add(control_frame,weight=0);pane.add(viewer,weight=1)
        control_canvas=tk.Canvas(control_frame,width=390,highlightthickness=0)
        control_scroll=ttk.Scrollbar(control_frame,orient='vertical',command=control_canvas.yview)
        control_canvas.configure(yscrollcommand=control_scroll.set)
        control_scroll.pack(side='right',fill='y');control_canvas.pack(side='left',fill='both',expand=True)
        controls=ttk.Frame(control_canvas,padding=12)
        controls_id=control_canvas.create_window(0,0,window=controls,anchor='nw')
        controls.bind('<Configure>',lambda e:control_canvas.configure(scrollregion=control_canvas.bbox('all')))
        control_canvas.bind('<Configure>',lambda e:control_canvas.itemconfigure(controls_id,width=e.width))
        ttk.Label(controls,text='編成の設定',font=('Meiryo',15,'bold')).pack(anchor='w')
        presets=ttk.Combobox(controls,values=PRESETS,state='readonly',width=37);presets.set(PRESETS[-1]);presets.pack(fill='x',pady=6)
        presets.bind('<<ComboboxSelected>>',lambda e:self.apply(preset(presets.get())))
        for key,label,kind in FIELDS:
            ttk.Label(controls,text=label).pack(anchor='w',pady=(6,0))
            var=tk.StringVar();self.vars[key]=var
            entry=ttk.Entry(controls,textvariable=var,width=44);entry.pack(fill='x')
            var.trace_add('write',self.schedule)
            if key in OPTIONAL_LISTS+OPTIONAL_SCALARS:
                result=tk.StringVar();self.calculated_vars[key]=result
                ttk.Label(controls,textvariable=result,wraplength=350,foreground='#087657').pack(anchor='w')
        ttk.Label(controls,text='寸法欄の空欄は自動計算。例：, 10000,\n欄全体が空なら全車自動。半径など試験条件は必須。\n比率0.5＝隙間の中央。',foreground='#607582').pack(anchor='w',pady=6)
        ttk.Checkbutton(controls,text='編成両端を通常台車にする',variable=self.normal,command=self.schedule).pack(anchor='w')
        ttk.Combobox(controls,textvariable=self.direction,values=['左曲線','右曲線'],state='readonly').pack(fill='x',pady=5)
        self.direction.trace_add('write',self.schedule)
        ttk.Label(controls,text='Blender（自動検出／手動指定）').pack(anchor='w',pady=(8,0))
        ttk.Entry(controls,textvariable=self.blender).pack(fill='x')
        ttk.Button(controls,text='Blender参照',command=self.browse_blender).pack(fill='x',pady=3)
        row=ttk.Frame(controls);row.pack(fill='x',pady=5)
        ttk.Button(row,text='設定を開く',command=self.load_config).pack(side='left',expand=True,fill='x')
        ttk.Button(row,text='設定を保存',command=self.save_config).pack(side='left',expand=True,fill='x')
        ttk.Button(controls,text='寸法図をPNG保存',command=self.save_image).pack(fill='x',pady=3)
        self.generate_button=ttk.Button(controls,text='3D生成・画像出力',command=lambda:self.start(False));self.generate_button.pack(fill='x',pady=3)
        self.test_button=ttk.Button(controls,text='3D生成 ＋ 接触試験 ＋ 画像出力',command=lambda:self.start(True));self.test_button.pack(fill='x',pady=3)
        ttk.Label(controls,textvariable=self.status,wraplength=340,foreground='#294d69').pack(fill='x',pady=8)
        self.error_label=ttk.Label(viewer,textvariable=self.error,foreground='#b42318',wraplength=700,padding=8)
        self.error_label.pack(fill='x')
        toolbar=ttk.Frame(viewer,padding=8);toolbar.pack(fill='x')
        ttk.Label(toolbar,text='詳細を表示する車両').pack(side='left')
        self.selector=ttk.Combobox(toolbar,textvariable=self.selected,values=['1','2','3'],width=5,state='readonly');self.selector.pack(side='left',padx=8)
        self.selected.trace_add('write',self.schedule)
        ttk.Combobox(toolbar,textvariable=self.zoom,values=['全体表示','75%','100%'],state='readonly',width=12).pack(side='right')
        self.zoom.trace_add('write',lambda *a:self.paint())
        frame=ttk.Frame(viewer);frame.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(frame,bg='#e5eaf0',highlightthickness=0)
        yscroll=ttk.Scrollbar(frame,orient='vertical',command=self.canvas.yview)
        xscroll=ttk.Scrollbar(frame,orient='horizontal',command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=yscroll.set,xscrollcommand=xscroll.set)
        frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        self.canvas.grid(row=0,column=0,sticky='nsew');yscroll.grid(row=0,column=1,sticky='ns');xscroll.grid(row=1,column=0,sticky='ew')
        self.canvas.bind('<Configure>',lambda e:self.paint())
        self.canvas.bind('<MouseWheel>',lambda e:self.canvas.yview_scroll(-int(e.delta/120),'units'))
        root.protocol('WM_DELETE_WINDOW',self.close)
        try:self.blender.set(find_blender())
        except FileNotFoundError:pass
        self.apply(preset(PRESETS[-1]));root.after(200,self.poll)

    def apply(self,c):
        c=defaults(c)
        for key,_,kind in FIELDS:
            value=c[key];self.vars[key].set(', '.join('' if x is None else f'{x:g}' for x in value) if kind is list else '' if value is None else str(value))
        self.normal.set(c['normal_ends']);self.direction.set('左曲線' if c['direction']==1 else '右曲線')
        self.schedule()

    def read(self):
        c={}
        for key,label,kind in FIELDS:
            text=self.vars[key].get().strip()
            try:
                if kind is list:
                    if not text and key in OPTIONAL_LISTS:
                        n=c['car_count']
                        count=n if key in ('lengths_mm','bogie_spacings_mm') else n-1 if key in ('gaps_mm','joint_fractions') else 2
                        c[key]=[None]*count
                    else:
                        c[key]=[None if not x.strip() and key in OPTIONAL_LISTS else float(x.strip())
                                for x in text.replace('、',',').replace('，',',').split(',')]
                else:c[key]=None if not text and key in OPTIONAL_SCALARS else kind(text)
            except ValueError:raise ValueError(f'「{label}」を確認してください。')
        c['normal_ends']=self.normal.get();c['direction']=1 if self.direction.get()=='左曲線' else -1
        dimensions(c);return c

    def schedule(self,*args):
        if self.after_id:self.root.after_cancel(self.after_id)
        self.after_id=self.root.after(160,self.update_preview)

    def update_preview(self):
        self.after_id=None
        try:
            c=self.read();self.current=c
            resolved=validate(c);self.error.set('')
            for key,var in self.calculated_vars.items():
                if key in ('outer_insets_mm','coupler_mm','coupling_face_to_shared_mm') and not c['normal_ends']:
                    var.set('通常台車なし：この欄は使用しません。');continue
                values=resolved[key] if isinstance(resolved[key],list) else [resolved[key]]
                var.set('計算結果：'+' / '.join(f'{x:,.6f}'.rstrip('0').rstrip('.') for x in values))
            values=[str(i+1) for i in range(len(c['lengths_mm']))];self.selector.configure(values=values)
            if self.selected.get() not in values:self.selected.set('1')
            self.preview=dimension_image(c,int(self.selected.get())-1);self.paint()
            if not self.busy:
                stale=self.last_result is not None and c!=self.last_result[0]
                self.status.set('寸法更新済み。変更前の試験結果です。再試験してください。' if stale else
                                self.result_text(self.last_result) if self.last_result else '寸法更新済み。接触試験はボタンで実行します。')
        except ValueError as exc:
            self.current=None;message=str(exc)+'\n図は直前の有効な設定です。生成・試験は実行できません。'
            self.error.set(message);self.status.set('入力エラー：右上の説明を確認してください。')
            for var in self.calculated_vars.values():var.set('計算結果：未確定')
        state='normal' if self.current and not self.busy else 'disabled'
        self.generate_button.configure(state=state);self.test_button.configure(state=state)

    def paint(self):
        if not hasattr(self,'preview'):return
        w,h=self.preview.size
        scale=min(max(100,self.canvas.winfo_width()-20)/w,max(100,self.canvas.winfo_height()-20)/h) if self.zoom.get()=='全体表示' else float(self.zoom.get().rstrip('%'))/100
        img=self.preview.resize((max(1,int(w*scale)),max(1,int(h*scale))),Image.Resampling.LANCZOS)
        self.photo=ImageTk.PhotoImage(img);self.canvas.delete('all')
        self.canvas.create_image(10,10,image=self.photo,anchor='nw');self.canvas.configure(scrollregion=(0,0,img.width+20,img.height+20))

    def browse_blender(self):
        path=filedialog.askopenfilename(title='blender.exeを選択',filetypes=[('Blender','blender.exe')])
        if path:self.blender.set(path)
    @staticmethod
    def result_text(result):
        _,out,report=result
        if report is None:return f'生成済み・試験未実施\n{out}'
        label=lambda value:'適合' if value else '要確認'
        return f'建築限界：{label(report["building_pass"])} / 車体：{label(report["body_pass"])} / 車両限界：{label(report["gauge_pass"])}\n{out}'
    def load_config(self):
        path=filedialog.askopenfilename(initialdir=PRESETS_DIR,filetypes=[('設定JSON','*.json')])
        if path:
            try:self.apply(load(path))
            except Exception as exc:messagebox.showerror('設定エラー',str(exc))
    def save_config(self):
        try:c=self.read()
        except ValueError as exc:messagebox.showerror('設定エラー',str(exc));return
        path=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('設定JSON','*.json')])
        if path:save(c,path)
    def save_image(self):
        try:c=self.read()
        except ValueError as exc:messagebox.showerror('設定エラー',str(exc));return
        path=filedialog.asksaveasfilename(defaultextension='.png',initialfile='寸法確認図.png')
        if path:dimension_image(c,int(self.selected.get())-1).save(path)
    def start(self,test):
        if self.busy:return
        try:c=self.read();exe=find_blender(self.blender.get())
        except Exception as exc:messagebox.showerror('実行エラー',str(exc));return
        self.busy=True;self.generate_button.configure(state='disabled');self.test_button.configure(state='disabled')
        self.status.set('生成中です。設定を変更しても実行中の条件は変わりません。')
        def work():
            try:
                out,report=generate(copy.deepcopy(c),exe,test=test,progress=lambda s:self.messages.put(('status',s)))
                self.messages.put(('done',(c,out,report)))
            except Exception as exc:self.messages.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        while not self.messages.empty():
            kind,value=self.messages.get()
            if kind=='status':self.status.set(value)
            else:
                self.busy=False
                if kind=='error':self.status.set(value);messagebox.showerror('実行エラー',value)
                else:
                    c,out,report=value;self.last_result=(c,out,report)
                    result='試験未実施' if report is None else f'建築限界：{report["building_pass"]} / 車体非接触：{report["body_pass"]} / 限界非重複：{report["gauge_pass"]}'
                    stale='\n設定が変わっているため、結果は変更前の条件です。' if self.current!=c else ''
                    self.status.set(f'完了：{result}{stale}\n{out}')
                    messagebox.showinfo('出力完了',f'{result}{stale}\n\n保存先：{out}')
                self.generate_button.configure(state='normal' if self.current else 'disabled');self.test_button.configure(state='normal' if self.current else 'disabled')
        self.root.after(200,self.poll)
    def close(self):
        if self.busy:
            messagebox.showinfo('処理中','生成中です。完了後にウィンドウを閉じてください。');return
        self.root.destroy()

def main():
    root=tk.Tk();App(root);root.mainloop()
