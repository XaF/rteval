import rtevalclient
import libxml2

print "** Creating doc"
d = libxml2.newDoc("1.0")
n = libxml2.newNode('TestNode1')
d.setRootElement(n)
n2 = n.newTextChild(None, 'TestNode2','Just a little test')
n2.newProp('test','true')

for i in range(1,100):
    n2 = n.newTextChild(None, 'TestNode3', 'Test line %i' %i)

print "** Doc to be sent"
d.saveFormatFileEnc('-','UTF-8', 1)

client = rtevalclient.rtevalclient()
client.SendReport(d)


