"""寸法の連立一次方程式。入力は拘束、Noneは未知数として扱う。

共有台車位置は隙間の左右距離U,Vを未知数にすることで、比率も
既知なら (1-f)U-fV=0、未知なら解いたU/(U+V)として扱える。
"""
import copy
import math

OPTIONAL_LISTS = ('lengths_mm', 'bogie_spacings_mm', 'gaps_mm',
                  'joint_fractions', 'outer_insets_mm', 'coupler_mm')
OPTIONAL_SCALARS = ('total_length_mm',)

def defaults(config):
    c = copy.deepcopy(config)
    c.setdefault('car_count', len(c.get('lengths_mm', [])))
    n = c['car_count']
    if not isinstance(n, int) or isinstance(n, bool) or not 2 <= n <= 20:
        raise ValueError('車体数は2～20の整数で指定してください。')
    c.setdefault('bogie_spacings_mm', [None]*n)
    c.setdefault('total_length_mm', None)
    for key, count in [('lengths_mm', n), ('bogie_spacings_mm', n), ('gaps_mm', n-1),
                       ('joint_fractions', n-1), ('outer_insets_mm', 2), ('coupler_mm', 2)]:
        if c.get(key) is None:
            c[key] = [None]*count
        if not isinstance(c[key], list) or len(c[key]) != count:
            labels={'lengths_mm':'車体長', 'bogie_spacings_mm':'台車中心間', 'gaps_mm':'車体間隔',
                    'joint_fractions':'共有台車位置比率', 'outer_insets_mm':'通常台車の内側距離', 'coupler_mm':'連結器突出'}
            raise ValueError(f'{labels[key]}は{count}個必要です。空欄の位置もカンマで区切ってください。')
        for v in c[key]:
            if v is not None and (not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v)):
                raise ValueError('寸法には有限の数値、または空欄（JSONではnull）を指定してください。')
    total = c['total_length_mm']
    if total is not None and (not isinstance(total,(int,float)) or isinstance(total,bool) or not math.isfinite(total)):
        raise ValueError('編成全長は有限の数値、または空欄にしてください。')
    if not isinstance(c['normal_ends'], bool):
        raise ValueError('normal_ends はtrueまたはfalseです。')
    for f in c['joint_fractions']:
        if f is not None and not 0 < f < 1:
            raise ValueError('共有台車位置比率は0より大きく1未満です。')
    return c

def solve(config):
    c = defaults(config); n=c['car_count']
    names = ([f'車体長（{i+1}号車）' for i in range(n)] +
             [f'台車中心間（{i+1}号車）' for i in range(n)] +
             [f'連接部{i+1}の左車端～共有台車' for i in range(n-1)] +
             [f'連接部{i+1}の共有台車～右車端' for i in range(n-1)] +
             ['通常台車の内側距離（左）','通常台車の内側距離（右）',
              '連結器突出（左）','連結器突出（右）','編成全長'])
    L=list(range(n)); B=list(range(n,2*n))
    U=list(range(2*n,3*n-1)); V=list(range(3*n-1,4*n-2))
    A=[4*n-2,4*n-1]; P=[4*n,4*n+1]; T=4*n+2
    size=len(names); rows=[]; labels=[]
    def add(terms, rhs, label):
        row=[0.0]*(size+1)
        for index,value in terms: row[index]+=value
        row[-1]=float(rhs)
        labels.append(label);rows.append((row,{len(labels)-1}))
    def fixed(index,value):
        if value is not None:add([(index,1)],value,f'{names[index]}={value:,.6g} mm')
    for indices,key in [(L,'lengths_mm'),(B,'bogie_spacings_mm')]:
        for i,value in zip(indices,c[key]):fixed(i,value)
    for i in range(n-1):
        if c['gaps_mm'][i] is not None:
            add([(U[i],1),(V[i],1)],c['gaps_mm'][i],f'連接部{i+1}の車体間隔={c["gaps_mm"][i]:,.6g} mm')
        f=c['joint_fractions'][i]
        if f is not None:add([(U[i],1-f),(V[i],-f)],0,f'連接部{i+1}の位置比率={f:g}')
    for indices,key in [(A,'outer_insets_mm'),(P,'coupler_mm')]:
        for index,value in zip(indices,c[key]):
            # Inactive dimensions have no geometric effect and must not create free variables.
            fixed(index,value if c['normal_ends'] else 0)
    fixed(T,c['total_length_mm'])
    for i in range(n):
        terms=[(B[i],1),(L[i],-1)]
        if i==0: terms+= [(A[0],1)] if c['normal_ends'] else [(U[0],-1)]
        else:terms.append((V[i-1],-1))
        if i==n-1:terms+= [(A[1],1)] if c['normal_ends'] else [(V[-1],-1)]
        else:terms.append((U[i],-1))
        add(terms,0,f'{i+1}号車の台車配置関係')
    terms=[(T,1)]+[(i,-1) for i in L+U+V]
    if c['normal_ends']:terms += [(i,-1) for i in P]
    add(terms,0,'編成全長＝車体長合計＋車体間隔合計＋外端連結器突出')

    # Reduced row echelon form. Preserve equation provenance for actionable errors.
    matrix=[row[:] for row,_ in rows]; origins=[s.copy() for _,s in rows]
    pivot_columns=[]; rank=0; eps=1e-10
    for col in range(size):
        pivot=max(range(rank,len(matrix)),key=lambda j:abs(matrix[j][col]),default=None)
        if pivot is None or abs(matrix[pivot][col]) < eps:continue
        matrix[rank],matrix[pivot]=matrix[pivot],matrix[rank]
        origins[rank],origins[pivot]=origins[pivot],origins[rank]
        div=matrix[rank][col];matrix[rank]=[x/div for x in matrix[rank]]
        for j in range(len(matrix)):
            if j==rank:continue
            factor=matrix[j][col]
            if abs(factor)>eps:
                matrix[j]=[a-factor*b for a,b in zip(matrix[j],matrix[rank])]
                origins[j]|=origins[rank]
        pivot_columns.append(col);rank+=1
    for j,row in enumerate(matrix):
        if max(abs(x) for x in row[:-1]) < eps and abs(row[-1]) > .001:
            involved=[labels[k] for k in sorted(origins[j])]
            detail=' / '.join(involved[:8])
            if len(involved)>8:detail+=f' / ほか{len(involved)-8}条件'
            raise ValueError('寸法が矛盾しています。入力値を変更するか、自動計算したい欄を空欄にしてください。\n'+
                             '関連条件：'+detail)
    if rank < size:
        free=set(range(size))-set(pivot_columns)
        unresolved=free|{col for row,col in zip(matrix,pivot_columns) if any(abs(row[j])>eps for j in free)}
        affected=[names[i] for i in sorted(unresolved)]
        detail=' / '.join(affected[:8])
        if len(affected)>8:detail+=f' / ほか{len(affected)-8}項目'
        raise ValueError(f'条件不足：寸法が一意に決まりません（あと{size-rank}個の独立した条件が必要）。\n'+
                         '未確定：'+detail)
    solution=[0.0]*size
    for row,col in zip(matrix,pivot_columns):solution[col]=row[-1]
    # Audit against original equations before using values in any geometry.
    for row,_ in rows:
        residual=sum(a*b for a,b in zip(row[:-1],solution))-row[-1]
        if abs(residual)>.001:
            raise ValueError('寸法計算の残差が許容値0.001mmを超えました。入力値を確認してください。')
    c['lengths_mm']=[solution[i] for i in L]
    c['bogie_spacings_mm']=[solution[i] for i in B]
    c['total_length_mm']=solution[T]
    c['gaps_mm']=[solution[u]+solution[v] for u,v in zip(U,V)]
    if any(g<=0 for g in c['gaps_mm']):raise ValueError('計算結果の車体間隔が0以下です。入力寸法を確認してください。')
    c['joint_fractions']=[solution[u]/g for u,g in zip(U,c['gaps_mm'])]
    if c['normal_ends']:
        c['outer_insets_mm']=[solution[i] for i in A];c['coupler_mm']=[solution[i] for i in P]
    else:
        for key in ('outer_insets_mm','coupler_mm'):c[key]=[v if v is not None else 0 for v in c[key]]
    return c
