"""FIFOの定数時間配置計算を、タイルごとに進める参照計算と全入力で照合する。"""
import json

CAPACITY=1505


def reference(head,size):
    origin=head
    start=head+(head%256==0)
    cursor=start
    for index in range(size):
        if index:
            if cursor==CAPACITY:cursor=0
            if cursor%256==0:cursor+=1
        cursor+=1
    wrapped=cursor<start
    end=cursor+(2048 if wrapped else 0)
    cost=cursor-start+(CAPACITY if wrapped else 0)+(start-origin)
    return start,start&0xff00,cursor%CAPACITY,end,cost


def fast(head,size):
    origin=head
    start=head+(head%256==0)
    base=start&0xff00
    cursor=start+size
    boundary=base+256
    for _ in range(2):
        if boundary>=CAPACITY:break
        if boundary<cursor:cursor+=1
        boundary+=256
    if cursor>=CAPACITY+1:
        cursor=cursor-CAPACITY+1
        if cursor>=257:cursor+=1
        end=cursor+2048
        cost=cursor+CAPACITY-start
    else:
        end=cursor
        cost=cursor-start
    return start,base,cursor%CAPACITY,end,cost+(start-origin)


def allocate(span,head,size):
    result=span(head,size)
    if result[3]-result[1]>1024:
        result=span(0,size)
        result=(*result[:4],result[4]+CAPACITY-head)
    return result


def main():
    count=0
    for head in range(CAPACITY):
        for size in range(352):
            expected=allocate(reference,head,size)
            actual=allocate(fast,head,size)
            assert actual==expected,(head,size,actual,expected)
            assert actual[3]-actual[1]<=1024
            count+=1
    print(json.dumps(dict(checked=count,capacityTiles=CAPACITY,maxFrameTiles=351)))


if __name__=='__main__':main()
