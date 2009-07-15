import rtevalclient
import libxml2
import StringIO

print "** Creating doc"
d = libxml2.newDoc("1.0")
n = libxml2.newNode('TestNode1')
d.setRootElement(n)
n2 = n.newTextChild(None, 'TestNode2','Just a little test')
n2.newProp('test','true')

for i in range(1,5):
    n2 = n.newTextChild(None, 'TestNode3', 'Test line %i' %i)

print "** Doc to be sent"
d.saveFormatFileEnc('-','UTF-8', 1)


print "** Testing API"
client = rtevalclient.rtevalclient()

server_fname = client.SendDataAsFile('test.data', "this is just a simple test file, compressed\n")
print "1:  File name on server: %s" % server_fname

server_fname = client.SendDataAsFile('test.data',
                                     "this is just a simple test file, uncompressed server side\n", True)
print "2:  File name on server: %s" % server_fname

server_fname = client.SendFile('test.log')
print "3:  File name on server: %s" % server_fname

server_fname = client.SendFile('test.log', True)
print "4:  File name on server: %s" % server_fname

status = client.SendReport(d)
print "5:  SendReport(xmlDoc): %s" % status

