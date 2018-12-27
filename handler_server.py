from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor
from random import randrange
import random
from sys import stdout
import math
from handler_client import ClientHandler
from data_state import Conn
import time

## comment preceded by '##' is concerned with over structure of code
# comment preceded by '#' is concerned with a specific segment's purpose

class MulSvr(Protocol):
    # instance variables:
    # factory: (factory object)
    # connum: (counter that increment for every message)
    # transport: (object used to send messages)

    def __init__(self, factory, connum):
        self.factory = factory
        self.connum = connum

    def connectionMade(self):
        stdout.write("connection %d made.\n" % self.connum)

    def connectionLost(self, reason):
        stdout.write("connection %d finished.\n" % self.connum)

    def dataReceived(self, data):
        stdout.write("connection %d received data.\n" % self.connum)
        for datum in data.split(";"):
            if datum is None or datum=="":
                continue
            self.factory.serverhandler.processRequest(self, datum)

    def sendMessage(self, data):
        stdout.write("connection %d sent data.\n" % self.connum)
        self.transport.write(data+";")

class MulSvrFactory(Factory):
    # instance variables
    # number: i don't know what this does
    # serverhandler: the server handler, has all the callback methods

    def __init__(self, serverhandler):
        self.number=0
        self.serverhandler=serverhandler

    def buildProtocol(self, addr):
        newsvr = MulSvr(self, self.number)
        self.number = self.number + 1
        return newsvr

class ServerHandler:
    # instance variable
    # state: the state object is used to maintain state of my network view

    def __init__(self,state):
        self.state=state
        self.joinatnormal_stagep=0
        # max number is non inclusive and min number is inclusive
        self.maxnumberofpeeratlastlevel=8
        self.minnumberofpeeratlastlevel=2

    ## code must be used to make twisted work
    def startup(self):
        endpoint = TCP4ServerEndpoint(reactor, self.state.myconn.port)
        endpoint.listen(MulSvrFactory(self))

    ## the main callback method to process everything
    def processRequest(self, protocol, data):
        ## reply a greeting, to test out connection
        print(data)
        if data.startswith('HEARTBEAT'):
            parameters = data.split()
            replymsg = 'HEARTBEAT_RESPONSE '
            lowRange = int(parameters[4])
            highRange = int(parameters[5])
            if(self.state.isAlive==False):
                replymsg += 'REPLACE'
            elif(self.state.lowRange < lowRange or self.state.lowRange >highRange or self.state.highRange<lowRange or self.state.highRange>highRange):
                replymsg += 'REPLACE'
            else:
                replymsg+= 'CORRECT'
            protocol.sendMessage(replymsg)
        elif(self.state.isAlive==False):
            replymsg='I_AM_DEAD'
            protocol.sendMessage(replymsg)
        elif data=="HELLO":
            protocol.sendMessage("HELLO")
        elif data.startswith("JOIN_INIT"):
            protocol.sendMessage("WAIT")
            self.join(protocol,data.split(),0)
        elif data.startswith("JOIN_OKAY"):
            protocol.transport.loseConnection()
        ## this was sent by a peer multicasting about a new peer joining last level
        elif data.startswith("JOIN_BOTT"):
            # seperate out argument passed in and construct a connection object
            parameters=data.split()
            joinerip=parameters[2]
            joinerport=int(parameters[3])
            joinername=parameters[4]
            joinerlowrange=int(parameters[5])
            joinerhighrange = int(parameters[6])
            joinerconn=Conn(joinerip,joinerport,joinername,joinerlowrange,joinerhighrange)
            # add the connection to my last level
            self.state.lastlevel.append(joinerconn)
            protocol.sendMessage("JOIN_OKAY")
            self.checksplit()
            self.printinfowithranges()
        ## this was sent to new peer, receives a list of peers to add to one level
        elif data.startswith("JOIN_LIST"):
            partialparam=data.split("\n")
            leveloflist=int((partialparam[0].split())[2])
            numberofpeer=int((partialparam[0].split())[3])
            # construct new peer list of that level, note order is important
            newlist=[]
            for i in range(0,numberofpeer):
                parameters=partialparam[1+i].split()
                contactip=parameters[0]
                contactport=int(parameters[1])
                contactname=parameters[2]
                contactlowRange = int(parameters[3])
                contacthighRange = int(parameters[4])
                newconn=Conn(contactip,contactport,contactname,contactlowRange,contacthighRange)
                newlist.append(newconn)
            if leveloflist==len(self.state.conns):
                self.state.addlevel(newlist)
            else:
                stdout.write("joinlist:\twhere am I getting the list from?\n")
            protocol.sendMessage("JOIN_OKAY")
            self.printinfowithranges()
        ## this was sent to peers at a none last level, polling its states
        elif data.startswith("JOIN_POLL"):
            # response with level, max peer, key range
            #replymsg="JOIN_PRLY "+self.state.myconn.name+" "+str(self.state.curmaxlv)+" "+str(len(self.state.conns[self.state.curmaxlv]))+" "+str('123')
            replymsg="JOIN_PRLY "+self.state.myconn.name+" "+str(len(self.state.conns))+" "+str(len(self.state.lastlevel))+" "+str('123')
            protocol.sendMessage(replymsg)
        ## forwarded the join request to me
        elif data.startswith("JOIN_FRWD"):
            protocol.sendMessage("JOIN_OKAY")
            # remember [a:b] takes a to b-1, b is not included
            self.join(protocol,data.split()[:5],int(data.split()[5]))
        ## this was sent to new peer, receives a list of peers to add to last level
        elif data.startswith("JOIN_LAST"):
            partialparam=data.split("\n")
            self.state.lowRange = int((partialparam[0].split())[2])
            self.state.highRange = int((partialparam[0].split())[3])
            numberofpeer=int((partialparam[0].split())[4])
            newlist=[]
            for i in range(0,numberofpeer):
                parameters=partialparam[1+i].split()
                contactip=parameters[0]
                contactport=int(parameters[1])
                contactname=parameters[2]
                newconn=Conn(contactip,contactport,contactname,self.state.lowRange, self.state.highRange)
                newlist.append(newconn)
            self.state.lastlevel=newlist
            protocol.sendMessage("JOIN_OKAY")
            self.checksplit()
            self.printinfowithranges()
        elif data.startswith("EXIT_INIT"):
            parameters=data.split()
            exiteraddr=parameters[2]
            exiterport=int(parameters[3])
            exitername=parameters[4]
            exiterlevel=int(parameters[5])
            exiterconn=Conn(exiteraddr,exiterport,exitername)
            if exiterlevel==len(self.state.conns):pass
                # exiting at last level
                #self.exitatbottom(exiterconn)
            # do nothing if not at last level
            self.printinfowithranges()
        elif data.startswith("EXIT_ELCT"):pass
            # receive a election request
            #self.exitatbottom2()
        elif data.startswith("EXIT_POLL"):
            # response with number level, number of peers at last level, key range
            replymsg="EXIT_PRLY "+self.state.myconn.name+" "+str(len(self.state.conns))+" "+str(len(self.state.lastlevel))+" "+str('123')
            protocol.sendMessage(replymsg)
        elif data.startswith("EXIT_FRWD"):
            # receive request for peer transfer
            parameters=data.split()
            exiteraddr=parameters[2]
            exiterport=int(parameters[3])
            exitername=parameters[4]
            exiterlevel=int(parameters[5])
            exiterpos=int(parameters[6])
            exiterconn=Conn(exiteraddr,exiterport,exitername)
            #self.exitatbottom6(exiterconn,exiterlevel,exiterpos)
        elif data.startswith("EXIT_JOIN"):
            parameters=data.split()
            joineraddr=parameters[2]
            joinerport=int(parameters[3])
            joinername=parameters[4]
            joinerconn=Conn(joineraddr,joinerport,joinername)
            #self.exitatbottom7(joinerconn)
        elif data.startswith("EXIT_BRCT"):
            parameters=data.split()
            joineraddr=parameters[2]
            joinerport=int(parameters[3])
            joinername=parameters[4]
            joinerconn=Conn(joineraddr,joinerport,joinername)
            #self.exitatbottom8(joinerconn)
            self.printinfowithranges()
        elif data.startswith("EXIT_LIST"):
            partialparam=data.split("\n")
            numberofpeer=int((partialparam[0].split())[2])
            newlist=[]
            for i in range(0,numberofpeer):
                parameters=partialparam[1+i].split()
                contactaddr=parameters[0]
                contactport=int(parameters[1])
                contactname=parameters[2]
                newconn=Conn(contactaddr,contactport,contactname)
                newlist.append(newconn)
            #self.exitatbottom9(newlist)
            self.printinfowithranges()
        elif data.startswith("DELETE_ME"):
            print("We have received the Delete Me message")
            parameters = data.split()
            leaverAddr = parameters[2]
            leaverPort = int(parameters[3])
            leaverName = parameters[4]
            leaverLowRange = int(parameters[5])
            leaverHighRange = int(parameters[6])
            leaverConn = Conn(leaverAddr, leaverPort, leaverName, leaverLowRange, leaverHighRange)
            self.removeFromLastLevel(leaverConn)
            self.checkForShrinkage()
        elif data.startswith("REQUESTING_INFO_LAST_LEVEL "):
            print("We did get a request")
            replymsg = "LAST_LEVEL_INFO "+ self.state.myconn.name+" "+self.state.myconn.addr+" "+str(self.state.myconn.port)+" "+self.state.myconn.name +" "+ str(len(self.state.lastlevel))
            protocol.sendMessage(replymsg)
        elif data.startswith('REQUEST_NODES_LAST_LEVEL'):
            replymsg = "LAST_LEVEL_NODE_RESULT "+self.state.myconn.name+'#'
            lastlevelList = self.state.lastlevel[:]
            for lastLevelNode in lastlevelList:
                replymsg+=lastLevelNode.addr+" "+str(lastLevelNode.port) +" "+lastLevelNode.name+' '+ str(lastLevelNode.lowRange) +' '+ str(lastLevelNode.highRange) +"#"
            protocol.sendMessage(replymsg)
        elif data.startswith('INSERT_LAST_LEVEL_DELETE_N-1_LEVEL_SHARE_WITH_LASTLEVEL'):
            print('GOT A MESSAGE FINALLY !!!!!!!!!!!!!!!!!!!!!!!!!')
        elif data.startswith('SHRINK_ONE_LAYER_UPDATE_LAST_LEVEL'):
            self.state.lastlevel = []
            parameters = data.split('\n')
            self.state.lowRange = int(parameters[0].split()[4])
            self.state.highRange = int(parameters[0].split()[5])
            for i in range (1,len(parameters)):
                newPeer = parameters[i].split()
                newPeerAddr = newPeer[0]
                newPeerPort = int(newPeer[1])
                newPeerName = newPeer[2]
                newPeerLowRange = int(newPeer[3])
                newPeerHighRange = int(newPeer[4])
                newPeerConnection = Conn(newPeerAddr,newPeerPort,newPeerName,newPeerLowRange,newPeerHighRange)
                self.state.lastlevel.append(newPeerConnection)
            self.state.conns = self.state.conns[:len(self.state.conns)-1]
            self.printinfowithranges()
        elif data.startswith('FIND_ALTERNATE_VALUE'):
            parameters = data.split()
            level = int(parameters[1])
            lowRange = int(parameters[2])
            highRange = int(parameters[3])
            replymsg = 'FIND_ALTERNATE_VALUE_RESPONSE '
            if(level > len(self.state.conns)):
                replymsg+='FAILED'
            else:
                for conn in self.state.conns[level]:
                    if(conn.lowRange == lowRange and conn.highRange == highRange):
                        replymsg+= 'SUCCESS '+conn.addr +' '+str(conn.port)+' '+conn.name
                        break

            protocol.sendMessage(replymsg)

            '''
            nodes = data.split('#')
            

            for i in range(1, len(nodes)-1):
                site = nodes[i].split()
                print(site)
            print("The length of the last level is "+str(len(self.state.lastlevel)))

            #self.state.printinfo()
            '''
        elif data.startswith('DELETE_ONE_NODE_GRANT_ONE_NODE'):
            protocol.sendMessage("OK_HANDLING")
            parameters = data.split()
            addr = parameters[2]
            port = int(parameters[3])
            name = parameters[4]
            requesterConn = Conn(addr, port, name)
            self.findNodeToSacrifice(requesterConn)

        elif data.startswith('DELETE_SACRIFICE_NODE_LAST_LEVEL'):
            print("Got the message")
            parameters = data.split()
            sacrificeNodeAddr = parameters[2]
            sacrificeNodePort = int(parameters[3])
            sacrificeNodeName = parameters[4]
            sacrificeNodeConn = Conn(sacrificeNodeAddr, sacrificeNodePort, sacrificeNodeName)
            self.printinfowithranges()
            self.state.lastlevel.remove(sacrificeNodeConn)
            self.printinfowithranges()
            protocol.sendMessage('WILL_DELETE_SACRIFICE_NODE')

        elif data.startswith('BECOME_SACRIFICE_AND_JOIN_ANOTHER_NETWORK'):
            parameters = data.split()
            requesterConnAddr = parameters[2]
            requesterConnPort = int(parameters[3])
            requesterConnName = parameters[4]
            requesterConnLowRange = int(parameters[5])
            requesterConnHighRange = int(parameters[6])
            requesterConn = Conn(requesterConnAddr, requesterConnPort, requesterConnName,requesterConnLowRange,requesterConnHighRange)
            winnerConnAddr    = parameters[7]
            winnerConnPort    = int(parameters[8])
            winnerConnName    = parameters[9]
            winnerConnLowRange = int(parameters[10])
            winnerConnHighRange = int(parameters[11])
            winnerConn        = Conn(winnerConnAddr, winnerConnPort, winnerConnName, winnerConnLowRange, winnerConnHighRange)
            self.handleOwnSacrifice(winnerConn, requesterConn)
            protocol.sendMessage("SacrificingAndJoiningAnotherNetwork")

        elif data.startswith('REQUEST_INFO_LAST_LEVEL'):
            replymsg = 'LAST_LEVEL_DETAILS ' + str(self.state.lowRange) +" "+ str(self.state.highRange)+' '+str(len(self.state.conns))
            for peer in self.state.lastlevel:
                replymsg += '\n'+peer.addr+' '+str(peer.port)+' '+peer.name
            print('replymsg', replymsg)
            protocol.sendMessage(replymsg)
        elif data.startswith('JOIN_THIS_SACRIFICE_NODE_TO_YOUR_NETWORK'):
            parameters = data.split()
            newJoinerAddr = parameters[1]
            newJoinerPort = int(parameters[2])
            newJoinerName = parameters[3]
            connection = Conn(newJoinerAddr, newJoinerPort, newJoinerName)
            protocol.sendMessage("we'll handle this")
            for peer in self.state.lastlevel:
                ClientHandler(self.state,peer,'joinThisSacrificeNodeToOurNetwork',connection).startup()
        elif data.startswith('JOIN_THIS_SACRIFICE_NODE_TO_OUR_NETWORK'):
            parameters = data.split()
            addr = parameters[1]
            port = int(parameters[2])
            name = parameters[3]
            connection = Conn(addr, port, name)
            self.state.lastlevel.append(connection)
            self.printinfowithranges()
            protocol.sendMessage('Done. Close Connection')

        elif data.startswith('HELP_UPDATE_THIS_LEVEL'):
            parameters = data.split()
            level = int(parameters[2])
            replymsg = 'INFO_FOR_LEVEL_N ' + str(level) +' ' +str(len(self.state.conns))+' '+self.state.myconn.name
            for peer in self.state.conns[level]:
                replymsg+='\n'+peer.addr+' '+str(peer.port)+' '+peer.name+' '+str(peer.lowRange)+' '+str(peer.highRange)
            print(replymsg)
            protocol.sendMessage(replymsg)
        elif data.startswith('REQUEST_DETAILS_FOR_N+1_LEVEL_FOR_SACRIFICE'):
            parameters = data.split()
            level = str(parameters[1])
            if(level>len(self.state.conns)):
                replymsg = 'RESPONSE_DETAILS_FOR_N+1_LEVEL_FOR_SACRIFICE '+str(len(self.state.conns)+1)+' '+str(self.state.lowRange)+' '+str(self.state.highRange)
                protocol.sendMessage(replymsg)
            else:
                self.searchNetworkForAnExtraNode(level)
        elif data.startswith('CHECK_ALTERNATE_ALIVE_STATUS'):
            parameters=data.split()
            lRange = int(parameters[1])
            hRange = int(parameters[2])
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@someone is requesting things from me!!!!")
            if(self.state.isAlive==True and self.state.lowRange>=lRange and self.state.highRange<= hRange):
                replymsg = 'CHECK_ALTERNATE_ALIVE_STATUS True '+str(len(self.state.lastlevel))
                for conn in self.state.lastlevel:
                    replymsg +='\n'+conn.addr+' '+str(conn.port)+' '+conn.name

            else:
                replymsg = 'CHECK_ALTERNATE_ALIVE_STATUS False'
            protocol.sendMessage(replymsg)
        else:
            print(data)
            protocol.sendMessage("NO SUPPORT")

    #def join(self,protocol,parameters,level):
    def join(self,protocol,parameters,level):
        if level<len(self.state.conns):
            # just join
            # contact peers and poll
            # select winner
            # replace winner with new comer, and send list to comer
            # forward request for winner to handle
            self.joinatnormal(parameters,level,0)
        elif level==len(self.state.conns):
            self.joinatbottom(parameters)
            #self.checksplit()
        self.printinfowithranges()

    # a join at any level other than last level
    def joinatnormal(self,parameters,level,stage):
        # static method variable
        # self.joinatnormal_stagep: stage of the operation, 3 total
        # self.joinatnormal_responses: the list of responses from poll
        # self.joinatnormal_joinerconn: joiner's information
        if stage==0 and self.joinatnormal_stagep==0:
            # send everyone a poll message
            self.joinatnormal_stagep=1
            self.joinatnormal_responses=[]
            joinerip=parameters[2]
            joinerport=int(parameters[3])
            joinername=parameters[4]
            joinerconn=Conn(joinerip,joinerport,joinername)
            self.joinatnormal_joinerconn=joinerconn
            for peer in self.state.conns[level]:
                ClientHandler(self.state,peer,'join4',(joinerconn,self,level)).startup()
            #reactor.callLater(5,self.joinatnormal,parameters,level,2)
        elif stage==1 and self.joinatnormal_stagep==1:
            # receive responses until timeout or we have everyone's response
            # parameters is tuple level, maxpeer, key range, ip
            self.joinatnormal_responses.append(parameters)
            if len(self.joinatnormal_responses)==len(self.state.conns[level]):
                #reactor.callLater(1,self.joinatnormal,None,level,2)
                self.joinatnormal(None,level,2)
        elif stage==2 and self.joinatnormal_stagep==1:
            # clearly indicate we have timed out and can no more receive connections
            self.joinatnormal_stagep=0
            joinerconn=self.joinatnormal_joinerconn
            self.joinatnormal_responses.sort()
            # now we have the winner first send joiner a list then forward request
            # peerlist must have your own ip as well, replace winner by joiner
            newpeerlist=self.state.conns[level][:] # shallow copy the list
            winner=(filter(lambda x:(x.addr==self.joinatnormal_responses[0][3].addr and
                    x.port==self.joinatnormal_responses[0][3].port),newpeerlist))[0]
            joinerconnNew = Conn(joinerconn.addr,joinerconn.port,joinerconn.name, winner.lowRange,winner.highRange)
            try:
                newpeerlist[newpeerlist.index(winner)]=joinerconnNew
            except ValueError:
                pass
            ClientHandler(self.state,joinerconn,'join3',(newpeerlist,level)).startup()
            # forward request to the winner at next level
            ClientHandler(self.state,winner,'join5',(joinerconn,level+1)).startup()
            # there is a probability of winner being replaced by this new guy
            if winner.addr!=self.state.myconn.addr and winner.port!= self.state.myconn.port:
                if randrange(0,100)<10:
                    try:
                        mylist=self.state.conns[level]
                        #self.state.conns[level].remove(winner)
                        #self.state.conns[level].append(joinerconn)
                        mylist[mylist.index(winner)]=joinerconn
                    except ValueError:
                        pass

    def joinatbottom(self,parameters):
        # lock
        # send messages to all the peers in the group
        # and then send client a contact list
        # check split
        print('This function was called!!!!!!!!!!!!!!!!!!!!!!!!')
        joinerip=parameters[2]
        joinerport=int(parameters[3])
        joinername=parameters[4]
        joinerconn=Conn(joinerip,joinerport,joinername,self.state.lowRange,self.state.highRange)
        print('self.state.lowRange',self.state.lowRange,'self.state.highRange',self.state.highRange,'joinername',joinername)
        lastlevel=self.state.lastlevel[:]
        for peer in self.state.lastlevel:
            ClientHandler(self.state,peer,'join2',joinerconn).startup()
            #ClientHandler(self.state,peer,'join2',Conn(joinerip,joinerport,joinername)).startup()
        lastlevel.append(joinerconn)
        self.printinfowithranges()
        # Whenever adding someone to my last level, I will also send it my range!
        ClientHandler(self.state,joinerconn,'join6',(lastlevel, self.state.lowRange, self.state.highRange)).startup()
        # don't need to append because I will send myself a message
        #self.state.conns[level].append(Conn(joinerip,joinerport,joinername))

    # new checksplit
    def checksplit(self):
        self.state.chkstate()
        maxnumberofpeeratlastlevel=self.maxnumberofpeeratlastlevel
        if len(self.state.lastlevel)==maxnumberofpeeratlastlevel:
            # first split by finding mygroup and copying mygroup
            myconn=self.state.myconn
            newlist=self.state.lastlevel[:]
            newlist.sort(key=lambda x:(x.addr,x.port))
            indexofconn=newlist.index(myconn)
            mygroup=indexofconn*4/maxnumberofpeeratlastlevel
            diff =  self.state.highRange - self.state.lowRange+1
            rangeSplit = diff/4
            oldRange = self.state.lowRange
            self.state.highRange = self.state.lowRange + rangeSplit*(mygroup+1)-1
            self.state.lowRange = self.state.lowRange + rangeSplit*mygroup
            stdout.write("checksplit: my group "+str(mygroup)+"\n")
            newlastLevel=newlist[mygroup*maxnumberofpeeratlastlevel/4:(mygroup+1)*maxnumberofpeeratlastlevel/4]
            self.state.lastlevel = []
            for peer in newlastLevel:
                self.state.lastlevel.append(Conn(peer.addr, peer.port, peer.name, self.state.lowRange,self.state.highRange))
            # then get the last-1 peers and do something
            # list is supposed to be myself and random peers from each group
            list=[None]*4
            for x in range(0,4):
                lRange = oldRange + rangeSplit*(x)
                hRange = oldRange + rangeSplit*(x+1)-1
                if x==mygroup:
                    myconn=self.state.myconn
                    list[x]=Conn(myconn.addr,myconn.port, myconn.name, lRange, hRange)
                else:
                    connection=newlist[x*maxnumberofpeeratlastlevel/4+randrange(0,maxnumberofpeeratlastlevel/4)]
                    list[x] = Conn(connection.addr,connection.port, connection.name, lRange, hRange)
                #stdout.write("checksplit: group "+str(x)+"\n")
            # last update last-1 given list
            self.updatelast(list)
        self.state.chkstate()
        return

    # update last-1 level
    def updatelast(self,list):
        # first update last-1
        if len(list)!=4:pass
            #sys.stdout.write("checksplit: list not 4\n")
        self.state.addlevel(list)
        stdout.write("checksplit: level added\n")
        return

    def printinfowithranges(self):
        stdout.write("START STATE PRINT\n")
        print('My Range is '+str(self.state.lowRange) +'->'+str(self.state.highRange))
        for i in range(0,len(self.state.conns)):
            stdout.write("level"+str(i)+": "+str(len(self.state.conns[i]))+"hosts\n")
            for j in range(0,len(self.state.conns[i])):
                conn=self.state.conns[i][j]
                stdout.write(conn.addr+" "+str(conn.port)+" "+conn.name+ " "+ str(conn.lowRange) + " " +str(conn.highRange)+"\n")
        stdout.write("lastlevel: "+str(len(self.state.lastlevel))+"hosts\n")
        for j in range(0,len(self.state.lastlevel)):
            conn=self.state.lastlevel[j]
            stdout.write(conn.addr+" "+str(conn.port)+" "+conn.name+ " "+ str(conn.lowRange)+ " " + str(conn.highRange)+"\n")
        stdout.write("END STATE PRINT\n")

    def exitinit(self):
        print("exit called")
        #inform peers in lowermost level to remove me from their list
        self.state
        myconn=self.state.myconn
        newlist = self.state.lastlevel[:]
        newlist.remove(myconn)
        self.state.isAlive = False
        #sending info to everyone except self to 'DeleteMe' from their network
        for peer in newlist:
            print("Trying to send DELETE ME message")
            ClientHandler(self.state,peer,'DeleteMe').startup()

        #Add code to change state of 
        return

    def removeFromLastLevel(self, leaverConn):
        print("Number of nodes on last level now are "+str(len(self.state.lastlevel)))
        self.state.lastlevel.remove(leaverConn)
        print("Number of nodes on last level now are "+str(len(self.state.lastlevel)))

    def checkForShrinkage(self):
        if(len(self.state.lastlevel) < self.minnumberofpeeratlastlevel):
            if(len(self.state.conns) == 0):
                print("Node deleted. No need for compression")
            else:
                print("Begun Shrinking")
                self.beginShrinkingProcess()

    def beginShrinkingProcess(self):
        peerStatusList = []
        lastlevelList = self.state.lastlevel[:]
        lastlevelList.sort(key=lambda x:(x.addr,x.port))
        if(lastlevelList[0] == self.state.myconn):
            print("I am the winner")
            newlist = self.state.conns[len(self.state.conns) - 1]
            for peer in newlist:
                print("requesting info from peers")
                ClientHandler(self.state,peer,'RequestingInfoLastLevel', (peerStatusList, self)).startup()
        else:
            print("Someone Else Was the Winner")

    def UsingInfoReceivedForShrinkage(self, peerStatusList):
        max = 0
        winnerConn = 0
        for peerStatus in peerStatusList:
            peerConn, lastLevelSize = peerStatus
            if(lastLevelSize>max):
                max = lastLevelSize
                winnerConn = peerConn

        if(max <= self.minnumberofpeeratlastlevel):
            #self.searchNetworkForAnExtraNode(0)
            print("We'll have to collapse the level")
            print("requesting last level info from all my n-1 level peers")
            peerList = self.state.conns[len(self.state.conns)-1][:]
            lastLevelNodesPeerListMessage = []
            for peer in peerList:
                print("requesting info!!!",peer.name)
                ClientHandler(self.state, peer, 'RequestNodesLastLevel', (lastLevelNodesPeerListMessage, self)).startup()
        else:
            self.beginStealSequence(winnerConn)


    def searchNetworkForAnExtraNode(self,level):
        ClientHandler(self.state, self.state.myconn, 'RequestDetailsForNLevelForSacrifice', (self,levelDetails)).startup()


    def beginStealSequence(self, winnerConn):
        print("starting steal sequence")
        ClientHandler(self.state, winnerConn, 'DeleteOneNodeGrantOneNode').startup()
        print('winner was ',winnerConn.name)

    def min(self,a,b):
        if(a<b):
            return a
        return b
    def max(self,a,b):
        if(a>b):
            return a
        return b
    def reduceByOneLevelAndShareInfo(self, lastLevelNodesPeerListMessage):
        for message in lastLevelNodesPeerListMessage:
            parameters = message.split('#')
            for i in range(1,len(parameters)-1):
                vals  = parameters[i].split()
                ip = vals[0]
                port = int(vals[1])
                name = vals[2]
                lowRange = int(vals[3])
                highRange = int(vals[4])
                newConn = Conn(ip,port, name,lowRange, highRange)
                if(newConn in self.state.lastlevel):
                    print(newConn.name + " already exists in the last level!")
                else:
                    self.state.lastlevel.append(newConn)
                    print(newConn.name + " added to the last level!")
        lowMin=float("inf")
        highMax = 0
        for peer in self.state.lastlevel:
            lowMin = min(lowMin,peer.lowRange)
            highMax = max(highMax, peer.highRange)
        self.state.lowRange = lowMin
        self.state.highRange = highMax
        for peer in self.state.lastlevel:
            peer.lowRange = lowMin
            peer.highRange = highMax
        newlist = self.state.lastlevel[:]
        newlist.remove(self.state.myconn)
        for peer in newlist:
            print("Shared with Q!!!!!!!!!!!!!!!!!!!! "+peer.name)
            ClientHandler(self.state, peer, 'InsertLastLevelDeleteN-1LevelShareWithLastLevel',(self,self.state.lastlevel[:])).startup()
        print(len(self.state.conns))
        self.state.conns = self.state.conns[:len(self.state.conns)-1]
        print(len(self.state.conns))
        self.printinfowithranges()

    def findNodeToSacrifice(self, requesterConn):
        newlist = self.state.lastlevel[:]
        newlist.sort(key=lambda x:(x.addr,x.port))
        sacrificeNode = newlist[len(newlist)-1]
        print('sacrificeNode.name',sacrificeNode.name)
        newlist.remove(sacrificeNode)
        for peer in newlist:
            ClientHandler(self.state, peer, 'DeleteSacrificeNodeLastLevel', sacrificeNode).startup()
        ClientHandler(self.state, sacrificeNode, 'SacrificeAndJoinAnotherNetwork', (self, requesterConn)).startup()
        ClientHandler(self.state, requesterConn, 'JoinThisSacrificeNodeToYourNetwork', (self,sacrificeNode)).startup()

    def handleOwnSacrifice(self, winnerConn, requesterConn):
        requesterListOfLastLevelNodes = []
        newlist = self.state.lastlevel[:]
        newlist.remove(self.state.myconn)
        length = len(newlist)
        randomIndex = random.randint(0,length-1)
        index = 30
        for i in range(0,4):
            if(self.state.conns[len(self.state.conns)-1][i] == self.state.myconn):
                index = i
        self.state.conns[len(self.state.conns)-1][index] = newlist[randomIndex]
        print('winnerConn.name', winnerConn.name)
        print('requesterConn.name', requesterConn.name)
        ClientHandler(self.state, requesterConn, 'RequestInfoLastLevel', (self,requesterListOfLastLevelNodes)).startup()

    def AddingInfoToLastLevel(self, requesterListOfLastLevelNodes, lowRange, highRange, lenConns):
        oldList = self.state.lastlevel
        self.state.lastlevel = []
        myconn = self.state.myconn
        self.state.myconn = Conn(myconn.addr, myconn.port, myconn.name, lowRange, highRange)
        self.state.lastlevel.append(self.state.myconn)
        self.state.lowRange = lowRange
        self.state.highRange = highRange
        for peer in  requesterListOfLastLevelNodes:
            site = peer.split()
            addr = site[0]
            port = int(site[1])
            name = site[2]
            peerConnection = Conn(addr, port, name, lowRange, highRange)
            if(peerConnection not in self.state.lastlevel):
                self.state.lastlevel.append(peerConnection)
        self.printinfowithranges()
        self.state.conns = [None]*lenConns
        newlist = self.state.lastlevel[:]
        newlist.remove(self.state.myconn)
        for level in range(0, lenConns):
            randIndex = random.randint(0,len(newlist)-1)
            ClientHandler(self.state, newlist[randIndex], 'HelpUpdateThisLevel', (self,level)).startup()

        '''
        

        #fixingOtherLevels to be solved by heartbeats


        '''
    def heartbeatProtocol(self, val):
        level = 0
        for connList in self.state.conns:
            for connection in connList:
                ClientHandler(self.state, connection, 'HeartBeat',(self, connection, level)).startup()
            level+=1

        #Need this only when we dont have people in our last layer
        #for connection in self.state.lastlevel:
        #    ClientHandler(self.state, connection, 'HeartBeat',(self, connection)).startup()
        self.printinfowithranges()
        if self.state.isAlive:
            reactor.callLater(20, self.heartbeatProtocol, val)

    def cleanup(self, addr, port, name, level):
        for conn in self.state.conns[level]:
            if(conn.addr == addr and conn.port == port):
                self.findReplacement(conn, level)
    '''
    #we poll last 3 rings and ask people in the rings if they could provide us with an alternative for this range
    def findReplacement(self, connection, level):
        
        for conn in self.state.lastlevel:
            if(conn.addr!= self.state.myconn.addr or conn.port!= self.state.myconn.port):
            ClientHandler(self.state, conn, 'FindReplacement', (self,level, conn.lowRange,conn.highRange)).startup()
        for i in range(len(self.state.conns)-3:len(self.state.conns)):
            if(i>=0):
                for conn in self.state.conns[i]:
                    ClientHandler(self.state, conn, 'FindReplacement',(self,level, conn.lowRange,conn.highRange)).startup()
    '''
    def findReplacement(self, connection, level):
        peerConnectionsForHelp = []
        for conn in self.state.lastlevel:
            if((conn.addr!= self.state.myconn.addr or conn.port!= self.state.myconn.port) and conn not in peerConnectionsForHelp and (conn.addr!= connection.addr or conn.port!= connection.port) ):
                peerConnectionsForHelp.append(conn)
        for i in range(len(self.state.conns)-3,len(self.state.conns)):
            if(i>=0):
                for conn in self.state.conns[i]:
                    if((conn.addr!= self.state.myconn.addr or conn.port!= self.state.myconn.port) and conn not in peerConnectionsForHelp and (conn.addr!= connection.addr or conn.port!= connection.port)):
                        peerConnectionsForHelp.append(conn)
        print(peerConnectionsForHelp)
        self.startPollingConnectionHelpForReplacement(peerConnectionsForHelp, connection, level)

    def startPollingConnectionHelpForReplacement(self, peerConnectionsForHelp, connection,level):
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Checking Again~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        if len(peerConnectionsForHelp) > 0:
            currentPeerToPoll = peerConnectionsForHelp[0]
            if len(peerConnectionsForHelp)>0:
                peerConnectionsForHelp = peerConnectionsForHelp[1:]
            else:
                peerConnectionsForHelp = []
            print('Are we even getting here????????????????????????????????????')
            ClientHandler(self.state, currentPeerToPoll, 'FindAlternateValue',(self, connection,level, peerConnectionsForHelp)).startup()
        else:
            print("retrying!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    def checkAliveStatus(self, peerConnectionsForHelp, replacementConnection, level, newAlternateConnection):
        ClientHandler(self.state, newAlternateConnection, 'checkAlternateAliveStatus',(self, replacementConnection, level, peerConnectionsForHelp)).startup()
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Checking alive status!",newAlternateConnection.name)

    def replacePeerwithAlternatePeer(self, connections, replacementConnection, level):
        changeConn = 0
        for conn in self.state.conns[level]:
            if (conn.addr == replacementConnection.addr and conn.port == replacementConnection.port):
                changeConn = conn
                break
        randomIndex = random.randint(0, len(connections)-1)
        randomReplacement = connections[randomIndex]
        print('Connections',connections)
        for conn in connections:
            print('details',conn.addr, conn.port, conn.name)
        conn.addr = randomReplacement.addr
        conn.port = randomReplacement.port
        conn.name = randomReplacement.name
        print('~~~~~~~~~conn details',conn.addr, conn.port, conn.name)
        print('~~~~~~~~~random replacement details', randomReplacement.addr,randomReplacement.port, randomReplacement.name)
        self.printinfowithranges()










###########################################################################################################################################
    '''     
    def exitinit(self):
        ## tell people you are leaving, mainly for people in your last level
        # because in other levels your peer's peer may not be you
        myconn=self.state.myconn
        newlist=self.state.lastlevel[:]
        newlist.sort(key=lambda x:(x.addr,x.port))
        newlist.remove(myconn)
        for peer in newlist:
            ClientHandler(self.state,peer,'exit1',len(self.state.conns)).startup()
        return

    def exitatnormal(self):
        # received exit node not at bottom level
        return

    def exitatbottom(self,exiterconn):
        ## some node is unreachable at the last level
        # sends a election message, that ask everybody to do the same thing
        self.state.lastlevel.remove(exiterconn)
        minnumberofpeeratlastlevel=self.minnumberofpeeratlastlevel
        if len(self.state.lastlevel)<minnumberofpeeratlastlevel:
            for peer in self.state.lastlevel:
                ClientHandler(self.state,peer,'exit2',None).startup()
        return

    def exitatbottom2(self):
        ## gets called when we have an election message
        ## decide if we are the winner
        myconn=self.state.myconn
        newlist=self.state.lastlevel[:]
        newlist.sort(key=lambda x:(x.addr,x.port))
        indexofconn=newlist.index(myconn)
        if indexofconn==0:
            self.exitatbottom3()

    def exitatbottom3(self):
        # we won if we are the first person
        # poll my peers at level above last, see who has most levels
        self.exitatbottom_resultlist=[]
        for peer in self.state.conns[len(self.state.conns)-1]:
            ClientHandler(self.state,peer,'exit3',self).startup()

    def exitatbottom4(self,result):
        ## gets responses from the poll and add it to a list
        resultlist=self.exitatbottom_resultlist
        levelabovelast=self.state.conns[len(self.state.conns)-1]
        resultlist.append(result)
        if len(resultlist)==len(levelabovelast):
            self.exitatbottom5()

    def exitatbottom5(self):
        ## after the poll, find a winner, send the request, or do a shrink
        minnumberofpeeratlastlevel=self.minnumberofpeeratlastlevel
        resultlist=self.exitatbottom_resultlist
        levelabovelast=self.state.conns[len(self.state.conns)-1]
        ############
        resultlist.sort(key=lambda r:(r[0],r[1],r[2]),reverse=True)
        stdout.write("exitbot: "+resultlist[0][3].name+"\n")
        if resultlist[0][0]==len(self.state.conns) and resultlist[0][1]==minnumberofpeeratlastlevel:
            ## do a shrink
            self.shrinking()
        else:
            ## ask for a peer trasfer
            # send the winner a message with my info so i wait for contact
            winnerconn=resultlist[0][3]
            # if you do recursion, it is not always me that wants to exit
            exiterpos=levelabovelast.index(self.state.myconn)
            ClientHandler(self.state,winnerconn,'exit4',(self.state.myconn,len(self.state.conns),exiterpos)).startup()

    def exitatbottom6(self,exiterconn,exiterlevel,exiterpos):
        ## receive the peer transfer request, if we are at last level, then transfer
        ## if we are not at last level, we forward to level below
        if exiterlevel==len(self.state.conns):
            # send exit
            self.exitinit()
            # change level above last
            levelabovelast=self.state.conns[len(self.state.conns)-1]
            lastlevel=self.state.lastlevel
            myconn=self.state.myconn
            indexofmyconn=levelabovelast.index(myconn)
            levelabovelast[exiterpos]=myconn
            lastlevel.remove(myconn)
            levelabovelast[indexofmyconn]=lastlevel[randrange(0,len(lastlevel))]
            # then transfer myself
            ClientHandler(self.state,exiterconn,'exit5',self.state.myconn).startup()
        else:
            # send transfer request to next level
            self.exitatbottom3()

    def exitatbottom7(self,joinerconn):
        ## on receiving transfer reply, broadcast it to group
        lastlevel=self.state.lastlevel[:]
        for peer in self.state.lastlevel:
            ClientHandler(self.state,peer,'exit6',joinerconn).startup()
        # send a list of peers to the new peer
        lastlevel.append(joinerconn)
        ClientHandler(self.state,joinerconn,'exit7',lastlevel).startup()

    def exitatbottom8(self,joinerconn):
        ## receive new peer
        self.state.lastlevel.append(joinerconn)

    def exitatbottom9(self,bottomlist):
        ## receive peer list
        # replace last level
        stdout.write("exitbot: got peer list\n")
        self.state.lastlevel=bottomlist

    def shrinking(self):
        ## starting a shrink
        ## broadcast a lockdown
        stdout.write("shrink not yet implemented!\n")

    def shrinking2(self):
        ## after peer confirm lockdown, send info to ring leaders
        stdout.write("shrink not yet implemented!\n")

    def shrinking3(self):
        ## after getting all info, send it to peer
        stdout.write("shrink not yet implemented!\n")

    def shrinking4(self):
        ## unlock
        stdout.write("shrink not yet implemented!\n")
    '''