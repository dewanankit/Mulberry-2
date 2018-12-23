#!/usr/bin/python
import argparse
from sys import stdout
from twisted.internet import reactor

from handler_server import *
from handler_client import *
from data_state import State, Conn

def main():
    parser = argparse.ArgumentParser("The Mulberry peer to peer network")
    parser.add_argument('-c', '--connect', nargs=1, type=str,
        metavar='remoteaddress', help='address to connect to')
    parser.add_argument('-p', '--port', nargs=1, type=int,
        metavar='remoteport', help='port to connect to')
    parser.add_argument('listen', nargs=1, type=int,
        metavar='localport', help='port to listen on')
    parser.add_argument('name', nargs=1, type=str,
        metavar='localname', help='name of this machine')
    parser.add_argument('-e', '--exit', nargs=1, type=int,
        metavar='exittimer', help='send exit after specified seconds')
    
    argresult = parser.parse_args()
    #if not first node:
        #try to connect to another node
    #set up port for connection
    def printargresult(argresult):
        stdout.write('arguments:\n')
        tobeprinted=''
        if argresult.connect!=None:
            tobeprinted=tobeprinted+'connect= \t'+argresult.connect[0]+'\n'
        if argresult.port!=None:
            tobeprinted=tobeprinted+'port=    \t'+str(argresult.port[0])+'\n'
        if argresult.listen!=None:
            tobeprinted=tobeprinted+'listen=  \t'+str(argresult.listen[0])+'\n'
        if argresult.name!=None:
            tobeprinted=tobeprinted+'name=    \t'+argresult.name[0]+'\n'
        if argresult.exit!=None:
            tobeprinted=tobeprinted+'exit=    \t'+str(argresult.exit[0])+'\n'
        stdout.write(tobeprinted)
    printargresult(argresult)
    #if argresult.listen==None:
        #stdout.write('no port to listen on')
        #exit()
    state=State('127.0.0.1',argresult.listen[0],argresult.name[0])
    state.lock=True
    if argresult.connect!=None and argresult.port!=None:
        client=setupclient(state,argresult.connect[0],argresult.port[0])
    server=setupserver(state)
    if argresult.exit!=None:
        reactor.callLater((argresult.exit[0]), (server.exitinit))
    reactor.run()
    return 0

def setupclient(state,ip,port):
    client=ClientHandler(state,Conn(ip,port),'join')
    client.startup()
    return client

def setupserver(state):
    server=ServerHandler(state)
    server.startup()
    return server

main()
