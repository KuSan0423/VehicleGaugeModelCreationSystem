"""画面プレビューと保存PNGで同一の図面を使用する。"""
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .geometry import dimensions, formation, polygons, point, separation, tangent_gap
from .configuration import validate

INK='#243746'; GRAY='#607582'; BLUE='#dceaf6'; GREEN='#d8eee9'; PURPLE='#eadcf1'

@lru_cache(maxsize=64)
def font(size,bold=False):
    paths=[Path('C:/Windows/Fonts')/('meiryob.ttc' if bold else 'meiryo.ttc'),
           Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for path in paths:
        if path.exists(): return ImageFont.truetype(str(path),size)
    return ImageFont.load_default()

class Paper:
    def __init__(self,w=2400,h=1820,bg='white'):
        self.image=Image.new('RGB',(w,h),bg); self.d=ImageDraw.Draw(self.image)
    def text(self,x,y,s,size=28,color=INK,anchor='left',bold=False):
        f=font(size,bold); width=self.d.textlength(str(s),font=f)
        if anchor=='middle': x-=width/2
        elif anchor=='right': x-=width
        box=self.d.textbbox((0,0),str(s),font=f)
        self.d.text((x,y-box[1]),str(s),font=f,fill=color)
    def line(self,a,b,color=INK,width=2,dash=False):
        if not dash: self.d.line([a,b],fill=color,width=width);return
        import math
        n=max(1,int(math.dist(a,b)/10))
        for i in range(0,n,2):
            self.d.line([(a[0]+(b[0]-a[0])*t/n,a[1]+(b[1]-a[1])*t/n) for t in (i,min(i+1,n))],fill=color,width=width)
    def rect(self,x,y,w,h,fill,outline=INK):
        self.d.rectangle((min(x,x+w),y,max(x,x+w),y+h),fill=fill,outline=outline,width=2)
    def dim(self,a,b,y,label,ext=None,size=26):
        self.line((a,y),(b,y))
        for x in (a,b):
            self.line((x-7,y+7),(x+7,y-7))
            if ext is not None:self.line((x,ext),(x,y+10),'#a6b3bb',1)
        self.text((a+b)/2,y-38,label,size,anchor='middle')

def mm(value):
    return f'{value*1000:,.1f}'.removesuffix('.0')

def dimension_image(config,selected=0):
    config=validate(config)
    d=dimensions(config); cars=d['cars']; selected=min(selected,len(cars)-1)
    p=Paper(); p.text(90,55,f'{config["name"]}｜寸法プレビュー',42,bold=True)
    p.text(90,120,'単位：mm  /  直線状態・長手方向の配置図（幅・高さ方向は模式表示）',27,GRAY)
    p.text(90,186,f'01  {len(cars)}両全体',32,bold=True)
    scale=2100/d['length']; left=d['projections'][0]
    X=lambda m:150+(m+left)*scale
    for i,c in enumerate(cars):
        p.rect(X(c['start']),350,c['length']*scale,100,BLUE if i%2==0 else GREEN)
        size=max(12,min(25,int(c['length']*scale/11)))
        p.text(X(c['center']),380,f'{i+1}号車 {mm(c["length"])}',size,anchor='middle',bold=True)
    for i,e in enumerate(d['equipment']):
        x=cars[i]['end']+config['gaps_mm'][i]/1000*config['joint_fractions'][i]
        p.rect(X(x-e['left']),356,(e['left']+e['right'])*scale,88,PURPLE)
    for x,proj in ((0,-d['projections'][0]),(d['body_span'],d['projections'][1])):
        if proj:p.rect(X(x),385,proj*scale,30,'#92a4af')
    nodes=[cars[0]['center']+cars[0]['a']]+[c['center']+c['b'] for c in cars]
    for i,x in enumerate(nodes):
        p.line((X(x),330),(X(x),535),GRAY,dash=True)
        p.rect(X(x)-24,462,48,32,'#bdcbd3'); p.rect(X(x)-4,474,8,8,INK)
        p.text(X(x),515,'通常台車' if config['normal_ends'] and i in (0,len(nodes)-1) else '連接台車',18,GRAY,'middle')
    p.dim(X(-left),X(d['body_span']+d['projections'][1]),280,
          ('両端の連結面間 ' if config['normal_ends'] else '編成車体端間 ')+mm(d['length']),345)
    for i,c in enumerate(cars):
        p.dim(X(nodes[i]),X(nodes[i+1]),600+(i%2)*48 if len(cars)>5 else 600,
              '台車中心間 '+mm(c['spacing']),535,size=max(12,min(26,int(c['spacing']*scale/13))))
    gaps=' / '.join(mm(x/1000) for x in config['gaps_mm'])
    p.text(90,675,'連接部の車体間隔：'+(gaps if len(gaps)<110 else gaps[:107]+'…'),25)
    p.line((90,730),(2310,730),'#c7d0d6')
    c=cars[selected]; a,b=c['a'],c['b']; length=c['length']; lo=-length/2; hi=length/2
    proj_left=d['projections'][0] if selected==0 else 0
    proj_right=d['projections'][1] if selected==len(cars)-1 else 0
    xmin=min(a,lo-proj_left); xmax=max(b,hi+proj_right)
    sx=1900/(xmax-xmin); P=lambda x:250+(x-xmin)*sx
    p.text(90,755,f'02  {selected+1}号車の詳細',32,bold=True)
    p.rect(P(lo),965,length*sx,125,BLUE if selected%2==0 else GREEN)
    if proj_left:p.rect(P(lo-proj_left),1010,proj_left*sx,30,'#92a4af')
    if proj_right:p.rect(P(hi),1010,proj_right*sx,30,'#92a4af')
    p.text(P(0),1003,'車体長 '+mm(length),31,anchor='middle',bold=True)
    left_label='通常台車中心' if config['normal_ends'] and selected==0 else '共有台車中心'
    right_label='通常台車中心' if config['normal_ends'] and selected==len(cars)-1 else '共有台車中心'
    for x,label in ((a,left_label),(b,right_label)):
        p.line((P(x),930),(P(x),1150),GRAY,dash=True)
        p.rect(P(x)-35,1100,70,30,'#bdcbd3');p.text(P(x),1160,label,24,GRAY,'middle')
    if config['normal_ends'] and selected==0:
        p.dim(P(lo-proj_left),P(b),850,'連結面 → 共有台車中心 '+mm(b-lo+proj_left),950)
        p.dim(P(lo-proj_left),P(a),1230,mm(a-lo+proj_left),1180)
    elif config['normal_ends'] and selected==len(cars)-1:
        p.dim(P(a),P(hi+proj_right),850,'共有台車中心 → 連結面 '+mm(hi+proj_right-a),950)
        p.dim(P(b),P(hi+proj_right),1230,mm(hi+proj_right-b),1180)
    p.dim(P(a),P(b),910,'台車中心間 '+mm(b-a),950)
    p.dim(P(lo),P(hi),963,'車体端 → 車体端 '+mm(length),965)
    p.text(120,1250,f'左車体端 → 左台車中心：{mm(a-lo)}',27)
    p.text(1230,1250,f'右台車中心 → 右車体端：{mm(hi-b)}',27)
    p.text(120,1300,'負値は台車中心が車体端より外側にあることを示します。',25,GRAY)
    p.rect(90,1380,2220,337,'#f3f6f8','#c7d0d6')
    p.text(120,1405,'寸法の整理・確認事項',29,bold=True)
    p.text(120,1460,f'車体長 ＝ {mm(b-a)} ＋ ({mm(a-lo)}) ＋ ({mm(hi-b)}) ＝ {mm(length)}',31,'#b34526',bold=True)
    p.text(120,1520,f'編成全長：{mm(d["length"])}  /  車体数：{len(cars)}  /  機器設計最小半径：R{d["radius_min"]:g}m',27)
    p.text(120,1575,'パンタグラフ：各車体中央、長さ2,000・幅1,300・高さ225（レール上4,290～4,515）',25)
    p.text(120,1630,'図は寸法確認用です。接触・建築限界の判定は「接触試験」で更新してください。',25)
    p.text(90,1760,'台車・連結器は位置を示す記号です。断面はVer2.0固定。カントなし・動揺なし。',23,GRAY)
    return p.image

def verification_image(config,report):
    config=validate(config)
    d=dimensions(config); r=config['radius_m']; arr=formation(d,r,config['direction'])
    p=Paper(1800,900,'#f4f7fb')
    p.text(48,35,f'{config["name"]}｜'+(f'R{r:g}一定半径' if r else '直線')+'の接触検証',34)
    p.text(48,90,'連接部1を上から表示。高さ2mの水平断面。分離余裕は平面評価の下限です。',23,GRAY)
    origin=arr['nodes'][1]; yaw=arr['equipment_poses'][0][2]
    import math
    def local(pt):
        x,y=pt[0]-origin[0],pt[1]-origin[1]
        return (math.cos(yaw)*x+math.sin(yaw)*y,-math.sin(yaw)*x+math.cos(yaw)*y)
    for index,(kind,title) in enumerate([('gauge','車両限界同士'),('body','車体外形同士'),('body','連接台車の機器配置限界')]):
        x=40+585*index
        p.d.rounded_rectangle((x,140,x+550,825),radius=14,fill='white',outline='#d4e0f0',width=2)
        p.text(x+20,168,title,24)
        p.text(x+20,211,'車体端・共有台車の配置',21,GRAY)
        tile=Image.new('RGB',(510,470),'#f5f8fc'); td=ImageDraw.Draw(tile)
        for k in range(0,510,40):td.line((k,0,k,470),fill='#e0e7ef')
        for k in range(0,470,40):td.line((0,k,510,k),fill='#e0e7ef')
        ps=polygons(d,arr,kind); targets=[(ps[0],'#efb477'),(ps[1],'#76ade0')]
        if index==2: targets.append((ps[len(d['cars'])],'#b285c7'))
        span=max(3.6,config['gaps_mm'][0]/1000+2)
        scale=470/span
        for poly,color in targets:
            pts=[local(pt) for pt in poly]
            td.polygon([(255+a*scale,235-b*scale) for a,b in pts],fill=color,outline=INK,width=2)
        td.rectangle((251,231,259,239),fill=INK);p.image.paste(tile,(x+20,252))
        value=tangent_gap(ps[0],ps[1],yaw) if index<2 else min(separation(ps[j],ps[len(d['cars'])]) for j in (0,1))
        p.text(x+20,750,f'分離余裕 {value*1000:,.2f} mm',27,'#087657' if value>=0 else '#b34526')
        p.text(x+20,795,'未試験' if report is None else '全試験結果は検証結果.jsonに記録',18,GRAY)
    p.text(48,855,'カント・揺れなし / 曲線進入・S字は対象外 / 車体接触と車両限界の重なりは別判定',21,GRAY)
    return p.image
