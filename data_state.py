# stores state of the program including name ip port connections isconnected
# python builtin container types set{,} dict{:,:}, list[,], tuple(,)

import sys

class State:
    # instance variables
    # myconn: connection object with my own information
    # conns: the list of levels
    # lastlevel: the list of connections at last level
    # lock: a write lock

    def __init__(self,ip,port,name,lowRange=0,highRange=0):
        self.myconn=Conn(ip,port,name,lowRange,highRange)
        self.conns=[]
        self.lastlevel=[self.myconn]
        self.lock=False
        self.isAlive = True
        self.timeStamp = {}
        self.lowRange = 0
        self.highRange = 1023
        return

    def addlevel(self,list):
        self.conns.append(list)

    def chklvuni(self,list):
        chklist=sorted(list,key=lambda x:(x.addr,x.port))
        last=None
        for item in chklist:
            if item==last:
                #sys.stdout.write("LEVEL ChECK: LEVEL "+str(level)+" IS NOT UNIQUE")
                return False
            last=item
        return True

    def chkstate(self):
        for i in range(0,len(self.conns)):
            if not len(self.conns[i])==4:
                sys.stdout.write("STATE ERROR: WRONG NUMBER PEERS\n")
            if not self.myconn in self.conns[i]:
                sys.stdout.write("STATE ERROR: NO SELF REFERENCE\n")
            if not self.chklvuni(self.conns[i]):
                sys.stdout.write("LEVEL ChECK: LEVEL "+str(i)+" IS NOT UNIQUE\n")
        if not (len(self.lastlevel)<8 and 
                self.myconn in self.lastlevel):
            sys.stdout.write("STATE ERROR: LAST LEVEL WRONG STATE\n")

    def printinfo(self):
        sys.stdout.write("START STATE PRINT\n")
        for i in range(0,len(self.conns)):
            sys.stdout.write("level"+str(i)+": "+str(len(self.conns[i]))+"hosts\n")
            for j in range(0,len(self.conns[i])):
                conn=self.conns[i][j]
                sys.stdout.write(conn.addr+" "+str(conn.port)+" "+conn.name+"\n")
        sys.stdout.write("lastlevel: "+str(len(self.lastlevel))+"hosts\n")
        for j in range(0,len(self.lastlevel)):
            conn=self.lastlevel[j]
            sys.stdout.write(conn.addr+" "+str(conn.port)+" "+conn.name+"\n")
        sys.stdout.write("END STATE PRINT\n")

    def lock(self):
        while True:
            while self.lock==True:
                None
            if self.lock==False:
                self.lock=True
                break
        return

    def unlock(self):
        self.lock=False
        return

class Conn:
    def __init__(self,ip,port,name=None, lowRange=0, highRange=0):
        self.addr=ip
        self.port=port
        self.name=name
        self.lowRange=lowRange
        self.highRange=highRange

    def __eq__(self,y):
        if not isinstance(y,Conn):
            return False
        if ((self.addr==y.addr)and
            (self.port==y.port)and
            (self.name==y.name)):
            return True
        return False