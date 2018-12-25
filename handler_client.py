from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ClientEndpoint
import sys
from data_state import Conn
#from sys import stdout

class MulClient(Protocol):
    def __init__(self,ch):
        self.clienthandler=ch
        self.transport=self.transport

    def sendMessage(self, msg):
        self.transport.write(msg+";")
        sys.stdout.write("sent: " + msg + "\n")
    
    def dataReceived(self, data):
        for datum in data.split(";"):
            if datum is None or datum=="":
                continue
            sys.stdout.write("recv: " + datum + "\n")
            self.clienthandler.processFeedback(self, datum)

def connectProtocol(endpoint, protocol):
    class OneShotFactory(Factory):
        def buildProtocol(self, addr):
            return protocol
    return endpoint.connect(OneShotFactory())

class ClientHandler:
    # instance variable
    # remote: conn object that contains remote peer info
    # state: state object of my peer lists
    # mode: mode of operation
    # - join: initiates join request
    # - join2: sends peer a new joiner
    # - join3: sends new joiner a peer list
    # - join4: poll
    # - join5: forward join
    # - join6: send a peer list for the last level
    # - exit1: send exit message
    # - exit2: elect a leader
    # - exit3: poll peers at level above last
    # - exit4: request for a transfer at last level
    # - exit5: joining new group
    # - exit6: broadcast joiner
    # - exit7: reply to joiner a peer list
    # extra: extra argument usually contain a list to send out

    def __init__(self,state,conn,mode,extra=None):
        self.remote=conn
        self.state=state
        self.mode=mode
        self.extra=extra

    def startup(self):
        point=TCP4ClientEndpoint(reactor, self.remote.addr, self.remote.port)
        myclientprotocol=MulClient(self)
        d=connectProtocol(point, myclientprotocol)
        myclienthandler=self
        d.addCallback(myclienthandler.gotProtocol)

    def gotProtocol(self, p):
        #p.sendMessage("HELLO")
        if self.mode=='join':
            replymsg="JOIN_INIT "+self.state.myconn.name+" "+self.state.myconn.addr+" "+str(self.state.myconn.port)+" "+self.state.myconn.name
            p.sendMessage(replymsg)
        elif self.mode=='join2':
            replymsg="JOIN_BOTT "+self.state.myconn.name+" "+self.extra.addr+" "+str(self.extra.port)+" "+self.extra.name+" "+str(self.extra.lowRange) +" "+str(self.extra.highRange)
            #reactor.callLater(1, p.sendMessage, replymsg)
            p.sendMessage(replymsg)
        elif self.mode=='join3':
            extra1,level=self.extra
            replymsg="JOIN_LIST "+self.state.myconn.name+" "+str(level)+" "+str(len(extra1))
            for conn in extra1:
                replymsg=replymsg+"\n"+conn.addr+" "+str(conn.port)+" "+conn.name+" "+str(conn.lowRange)+" "+str(conn.highRange)
            p.sendMessage(replymsg)
        elif self.mode=='join4':
            # simply send request for info with joiner ip and address and name
            extra1,callback,level=self.extra
            replymsg="JOIN_POLL "+self.state.myconn.name+" "+extra1.addr+" "+str(extra1.port)+" "+extra1.name
            p.sendMessage(replymsg)
        elif self.mode=='join5':
            extra1,level=self.extra
            replymsg="JOIN_FRWD "+self.state.myconn.name+" "+extra1.addr+" "+str(extra1.port)+" "+extra1.name+" "+str(level)
            p.sendMessage(replymsg)
        elif self.mode=='join6':
            lastlevel, lowRange, highRange =self.extra
            replymsg="JOIN_LAST "+self.state.myconn.name+" "+str(lowRange)+" "+str(highRange)+" "+str(len(lastlevel))
            for conn in lastlevel:
                replymsg=replymsg+"\n"+conn.addr+" "+str(conn.port)+" "+conn.name
            p.sendMessage(replymsg)
        elif self.mode=='exit1':
            # send over my detail and level i am on
            replymsg="EXIT_INIT "+self.state.myconn.name+" "+self.state.myconn.addr+" "+str(self.state.myconn.port)+" "+self.state.myconn.name+" "+str(self.extra)
            p.sendMessage(replymsg)
        elif self.mode=='exit2':
            replymsg="EXIT_ELCT "+self.state.myconn.name
            p.sendMessage(replymsg)
        elif self.mode=='exit3':
            replymsg="EXIT_POLL "+self.state.myconn.name
            p.sendMessage(replymsg)
        elif self.mode=='exit4':
            extra1,level,pos=self.extra
            replymsg="EXIT_FRWD "+self.state.myconn.name+" "+extra1.addr+" "+str(extra1.port)+" "+extra1.name+" "+str(level)+" "+str(pos)
            p.sendMessage(replymsg)
        elif self.mode=='exit5':
            replymsg="EXIT_JOIN "+self.state.myconn.name+" "+self.extra.addr+" "+str(self.extra.port)+" "+self.extra.name
            p.sendMessage(replymsg)
        elif self.mode=='exit6':
            extra=self.extra
            replymsg="EXIT_BRCT "+self.state.myconn.name+" "+extra.addr+" "+str(extra.port)+" "+extra.name
            p.sendMessage(replymsg)
        elif self.mode=='exit7':
            extra=self.extra
            replymsg="EXIT_LIST "+self.state.myconn.name+" "+str(len(extra))
            for conn in extra:
                replymsg=replymsg+"\n"+conn.addr+" "+str(conn.port)+" "+conn.name
            p.sendMessage(replymsg)
        elif self.mode=='DeleteMe':
            print("Requesting Delete")
            replymsg="DELETE_ME "+self.state.myconn.name+" "+self.state.myconn.addr+" "+str(self.state.myconn.port)+" "+self.state.myconn.name+" "+str(self.state.lowRange)+' '+str(self.state.highRange)
            p.sendMessage(replymsg)
        elif self.mode=='RequestingInfoLastLevel':
            print("Requesting state from my peers in n-1 level")
            replymsg = "REQUESTING_INFO_LAST_LEVEL "+self.state.myconn.name+" "+self.state.myconn.addr+" "+str(self.state.myconn.port)+" "+self.state.myconn.name
            p.sendMessage(replymsg)
        elif self.mode=='RequestNodesLastLevel':
            print(self.remote.name,"Requesting all peer nodes in n-1 level to share their nodes in n-1 level!!!!!!!!!!!!!!!!!!!!!!!")
            replymsg = "REQUEST_NODES_LAST_LEVEL "+self.state.myconn.name
            p.sendMessage(replymsg)
        elif self.mode=='InsertLastLevelDeleteN-1LevelShareWithLastLevel':
            print("Trying to send a message across!!!!!!!!")
            replymsg = 'SHRINK_ONE_LAYER_UPDATE_LAST_LEVEL '+self.state.myconn.addr + ' '+ str(self.state.myconn.port)+' ' +self.state.myconn.name+' '+str(self.state.lowRange)+' '+str(self.state.highRange)
            callBack, newPeers = self.extra
            print('newPeers',newPeers)
            for newPeer in newPeers:
                replymsg+='\n'+newPeer.addr+' '+str(newPeer.port)+' '+newPeer.name+' '+str(newPeer.lowRange)+' '+str(newPeer.highRange)
            p.sendMessage(replymsg)
            '''
            if(self.remote == None):
                print("remote was None")
            else:
                print(self.remote)

            #print("sharing info with peers to update their last level")
            messageQueue = (self.extra)[:]
            #print('Printing mesage Queues')
            #print(messageQueue)
            replymsg = 'INSERT_LAST_LEVEL_DELETE_N-1_LEVEL ' + self.state.myconn.name +'#'
            for i in range(0,len(messageQueue)):
                p = messageQueue[i]
                sites = p.split('#')
                text=''
                for j in range(1,len(sites)-1):
                    print('site', sites[j])
                    parameters = sites[j].split()
                    replymsg += parameters[0] +' '+parameters[1] +' '+ parameters[2]+'#'
            #print('replymsg',replymsg)
            replymsg='HELLO'
            print(replymsg)
            p.sendMessage(replymsg)
            '''
        elif self.mode=='DeleteOneNodeGrantOneNode':
            print("Did we even get here?")
            print("WTF")
            print(self.state.myconn.addr)
            #print('remote.name',remote.name)
            replymsg = 'DELETE_ONE_NODE_GRANT_ONE_NODE '+self.state.myconn.name + ' '+self.state.myconn.addr+' '+str(self.state.myconn.port)+' '+self.state.myconn.name
            print(replymsg)
            p.sendMessage(replymsg)
        elif self.mode=='DeleteSacrificeNodeLastLevel':
            sacrificeNode = self.extra
            replymsg = 'DELETE_SACRIFICE_NODE_LAST_LEVEL '+self.state.myconn.name +' '+ sacrificeNode.addr + ' ' + str(sacrificeNode.port) +' ' + sacrificeNode.name
            p.sendMessage(replymsg)
        elif self.mode =='SacrificeAndJoinAnotherNetwork':
            callback, requesterConn = self.extra
            replymsg = 'BECOME_SACRIFICE_AND_JOIN_ANOTHER_NETWORK '+self.state.myconn.name + ' ' + requesterConn.addr + ' ' + str(requesterConn.port)+' '+requesterConn.name+' '+str(requesterConn.lowRange)+' '+str(requesterConn.highRange)+' '+self.state.myconn.addr + ' ' +str(self.state.myconn.port) + ' ' + self.state.myconn.name+' '+str(self.state.myconn.lowRange)+' '+str(self.state.myconn.highRange)
            print(replymsg)
            p.sendMessage(replymsg)
            #p.sendMessage(replymsg)
        elif self.mode=='RequestInfoLastLevel':
            callback, requesterListOfLastLevelNodes = self.extra
            replymsg = 'REQUEST_INFO_LAST_LEVEL '+ self.state.myconn.name
            p.sendMessage(replymsg)
        elif self.mode=='JoinThisSacrificeNodeToYourNetwork':
            callback, sacrificeNode = self.extra
            replymsg = 'JOIN_THIS_SACRIFICE_NODE_TO_YOUR_NETWORK '+sacrificeNode.addr + ' ' + str(sacrificeNode.port) +' '+sacrificeNode.name
            p.sendMessage(replymsg)
        elif self.mode=='joinThisSacrificeNodeToOurNetwork':
            connection = self.extra
            print('connection.addr!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!',connection.addr)
            replymsg = 'JOIN_THIS_SACRIFICE_NODE_TO_OUR_NETWORK '+connection.addr + ' '+str(connection.port) + ' ' + connection.name
            p.sendMessage(replymsg)
        elif self.mode=='HelpUpdateThisLevel':
            callback, level = self.extra
            replymsg = 'HELP_UPDATE_THIS_LEVEL '+self.state.myconn.name +' '+str(level) 
            p.sendMessage(replymsg)
        else:
            p.transport.loseConnection()

    def processFeedback(self, protocol, data):
        if self.mode=='join':
            if data=="WAIT":
                protocol.sendMessage("JOIN_OKAY")
        elif self.mode=='join2':
            if data=="JOIN_OKAY":
                protocol.transport.loseConnection()
        elif self.mode=='join3':
            if data=="JOIN_OKAY":
                protocol.transport.loseConnection()
        elif self.mode=='join4':
            # should save the info received
            # callback with tuple (level, maxpeer, key range, ip)
            # be careful because python types are strange
            if data.startswith("JOIN_PRLY"):
                extra1,callback,level=self.extra
                temp=data.split()
                datum=(temp[2],temp[3],temp[4],self.remote)
                callback.joinatnormal(datum,level,1)
                protocol.sendMessage("JOIN_OKAY")
        elif self.mode=='join5':
            if data=="JOIN_OKAY":
                protocol.transport.loseConnection()
        elif self.mode=='join6':
            if data=="JOIN_OKAY":
                protocol.transport.loseConnection()
        elif self.mode=='exit1':
            protocol.transport.loseConnection()
        elif self.mode=='exit2':
            protocol.transport.loseConnection()
        elif self.mode=='exit3':
            if data.startswith("EXIT_PRLY"):
                callback=self.extra
                temp=data.split()
                datum=(temp[2],temp[3],temp[4],self.remote)
                callback.exitatbottom4(datum)
            protocol.transport.loseConnection()
        elif self.mode=='exit4':
            protocol.transport.loseConnection()
        elif self.mode=='exit5':
            protocol.transport.loseConnection()
        elif self.mode=='exit6':
            protocol.transport.loseConnection()
        elif self.mode=='exit7':
            protocol.transport.loseConnection()

        elif self.mode=='RequestingInfoLastLevel':
            if(data.startswith('LAST_LEVEL_INFO')):
                parameters = data.split()
                peerAddr = parameters[2]
                peerPort = int(parameters[3])
                peerName = parameters[4]
                peerConn = Conn(peerAddr, peerPort, peerName)
                peerLastLevelCount = int(parameters[5])
                peerStatusList, callback = self.extra
                print("OMG, Connection received, length was " + str(peerLastLevelCount))
                peerStatusList.append((peerConn, peerLastLevelCount))
                if(len(peerStatusList) == len(callback.state.conns[len(callback.state.conns)-1])):
                    callback.UsingInfoReceivedForShrinkage(peerStatusList)

        elif self.mode=='RequestNodesLastLevel':
            if(data.startswith('LAST_LEVEL_NODE_RESULT')):
                lastLevelNodesPeerListMessage, callback = self.extra
                lastLevelNodesPeerListMessage.append(data)
                protocol.transport.loseConnection()
                if(len(lastLevelNodesPeerListMessage) == len(self.state.conns[len(self.state.conns)-1])):
                    print("received results from all nodes")
                    callback.reduceByOneLevelAndShareInfo(lastLevelNodesPeerListMessage)
                    #print(lastLevelNodesPeerListMessage)
        elif self.mode=='RequestInfoLastLevel':
            print('Got response for last level')
            callback, requesterListOfLastLevelNodes = self.extra
            parameters = data.split('\n')
            lowRange = int(parameters[0].split()[1])
            highRange = int(parameters[0].split()[2])
            lenConns = int(parameters[0].split()[3])
            for i in range(1, len(parameters)):
                print(parameters[i])
                requesterListOfLastLevelNodes.append(parameters[i])
            callback.AddingInfoToLastLevel(requesterListOfLastLevelNodes, lowRange, highRange, lenConns)
            protocol.transport.loseConnection()
        elif self.mode=='HelpUpdateThisLevel':
            if data.startswith('INFO_FOR_LEVEL_N'):
                callback, l = self.extra
                params = data.split('\n')
                levels = int(params[0].split()[1])
                newPeerName = params[0].split()[3] 
                print('levels',levels)
                newConnectionLayer = []
                for i in range(1, len(params)):
                    peerDetails = params[i].split()
                    peerAddr = peerDetails[0]
                    peerPort = int(peerDetails[1])
                    peerName = peerDetails[2]
                    peerLowRange = int(peerDetails[3])
                    peerHighRange = int(peerDetails[4])
                    if(peerName == newPeerName):
                        connection = Conn(self.state.myconn.addr, self.state.myconn.port,self.state.myconn.name, peerLowRange, peerHighRange)
                    else:
                        connection = Conn(peerAddr, peerPort,peerName, peerLowRange, peerHighRange)
                    newConnectionLayer.append(connection)
                self.state.conns[levels] = newConnectionLayer
                print("We were successful")
                callback.printinfowithranges()
        else:
            print('closing connection')
            protocol.transport.loseConnection()