#!/usr/bin/python
from Cocoa import NSWindowController, NSApplication, objc, NSApp
from Foundation import NSObject, NSIndexSet
import os
import json

class Data:
    conf = os.path.expanduser('~/Library/Application Support/VhostSwitcher')

    def __init__(self):
        vhostFile = '/private/etc/apache2/extra/httpd-vhosts.conf'
        self.vhostDirectory = '/private/etc/apache2/extra/'
        if self.fileExist('/liste.json'):
            print 'loading file'
            self.liste = self.loadJsonFile('/liste.json')
        else:
            print 'parse + save'
            self.liste = self.parseVhostFile(vhostFile)
            self.saveJsonFile(self.liste)


    def parseVhostFile(self, vhostFile):
        myfile = open(vhostFile, 'r')
        row = myfile.readlines()

        liste = []
        serverName = []
        directory = []
        default = []
        for r in row:
            if r[0] != "#" and r != '\n':
                param = self.clean(r)[0]
                if param == "ServerName":
                    liste += [{ "Name": self.clean(r)[1] }]
                    serverName += [self.clean(r)[1]]
                if param == "DocumentRoot":
                    directory += [self.clean(r)[1].replace('"', '')]
                if r.find('_default_') > 0:
                    default += [1]
                else:
                    default += [0]

        for k in range(len(liste)):
            liste[k]["ServerName"] = serverName[k]
            liste[k]["DocumentRoot"] = directory[k]
            liste[k]["default"] = default[k]
        myfile.close()
        return liste

    def fileExist(self, path):
        return os.path.isfile(self.conf+path)

    def clean(self, string):
        return string.lstrip(' ').rstrip('\n').split(' ')

    def loadJsonFile(self, path):
        fileList = open(self.conf+path, 'r')
        data = json.load(fileList)
        new = []
        for k, d in enumerate(data):
            new += [data[k]]
        fileList.close()
        return new

    def saveJsonFile(self, data):
        if not os.path.exists(self.conf):
            os.makedirs(self.conf)
        fileList = open(self.conf+'/liste.json', 'w')
        fileList.write(json.dumps(data))
        fileList.close()
        self.updateVhostfile(data)
        self.writeToHost(data)
        print 'ok'

    def writeToHost(self, data):
        data = list(data)
        host = open('/private/etc/hosts', 'r+')
        for h in host.readlines():
            for i, d in enumerate(data):
                if h == "127.0.0.1\t"+d['ServerName']+"\n":
                    print data.pop(i)
        for d in data:
            host.write("127.0.0.1\t"+d['ServerName']+"\n")

    def updateVhostfile(self, data):
        newVhost = open(self.vhostDirectory+'/httpd-vhosts-copie.conf', 'w')
        for d in data:
            if d['default'] == 1:
                content = ""
                content += "ServerName " + d['ServerName'] + "\n"
                content += "DocumentRoot " + '"'+d['DocumentRoot']+'"'
                structure = "<VirtualHost _default_*:80>\n{}\n</VirtualHost>\n\n".format(content)
                newVhost.write(structure)
        for d in data:
            if d['default'] != 1:
                content = ""
                content += "ServerName " + d['ServerName'] + "\n"
                content += "DocumentRoot " + '"'+d['DocumentRoot']+'"'
                structure = "<VirtualHost *:80>\n{}\n</VirtualHost>\n\n".format(content)
                newVhost.write(structure)


ROWCOUNT = len(Data().liste)

class VhostController(NSWindowController):

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)


class TableModel(NSObject):
    tableView = objc.IBOutlet()
    txtDirectory = objc.IBOutlet()
    txtServName = objc.IBOutlet()
    defaultSite = objc.IBOutlet()

    # An instance of this class is connected to the 'datasource' and
    # the 'delegate' outlet of the table view in the nib.

    def awakeFromNib(self):
        # Instantiate the Data model
        self.data = Data()
        self.rowcount = len(self.data.liste)
        self.row = 0
        # tableView is an outlet set in Interface Builder
        self.tableView.setAutosaveName_("TableView")
        self.tableView.setAutosaveTableColumns_(1)
        self.tableView.setTarget_(self)
        self.tableView.setDoubleAction_("doubleClick:")
        self.tableView.window().setDelegate_(self)

        # select the first row by default
        index = NSIndexSet.indexSetWithIndex_(0)
        self.tableView.selectRowIndexes_byExtendingSelection_(index, False)


    def init(self):
        self.row = 0
        return self

    # Actions
    @objc.IBAction
    def doubleClick_(self, sender):
        # double-clicking a column header causes clickedRow() to return -1
        print("doubleClick!", sender.clickedColumn(), sender.clickedRow())

    @objc.IBAction
    def editDocumentRoot_(self, sender):
        self.updateList("DocumentRoot", sender.stringValue())

    @objc.IBAction
    def editServerName_(self, sender):
        self.updateList("ServerName", sender.stringValue())

    @objc.IBAction
    def editName_(self, sender):
        self.updateList("Name", sender.stringValue())

    @objc.IBAction
    def setDefault_(self, sender):
        self.setDefault(self.row, sender.intValue())


    @objc.IBAction
    def editSite_(self, sender):
        controls = sender.selectedSegment()
        if controls == 0:
            # add a Site
            self.addSite()
        if controls == 1:
            # remove a Site
            self.removeSite()
        self.data.saveJsonFile(self.data.liste)

    # data source methods
    @objc.python_method
    def addSite(self):
        self.data.liste += [{ "Name" : "default", "ServerName" : "", "DocumentRoot": "", "default" : 0 }]
        self.tableView.beginUpdates()
        self.tableView.insertRowsAtIndexes_withAnimation_(NSIndexSet.indexSetWithIndex_(len(self.data.liste)+1), NSTableViewAnimationEffectFade)
        self.tableView.endUpdates()

    @objc.python_method
    def removeSite(self):
        self.tableView.beginUpdates()
        self.tableView.removeRowsAtIndexes_withAnimation_(NSIndexSet.indexSetWithIndex_(self.tableView.selectedRow()), NSTableViewAnimationEffectFade)
        self.tableView.endUpdates()
        self.data.liste.pop(self.row)

    @objc.python_method
    def updateList(self, key, value):
        liste = self.data.liste
        liste[self.row][key] = value
        self.data.saveJsonFile(liste)
        print "row "+str(self.row)+" update !"

    @objc.python_method
    def setDefault(self, row, value):
        for data in self.data.liste:
            data['default'] = 0
        self.data.liste[row]['default'] = value
        self.data.saveJsonFile(self.data.liste)

    def numberOfRowsInTableView_(self, aTableView):
        return self.rowcount

    def tableView_objectValueForTableColumn_row_(
            self, aTableView, aTableColumn, rowIndex):
        return self.data.liste[rowIndex]['Name']

    def tableView_setObjectValue_forTableColumn_row_(
            self, aTableView, anObject, aTableColumn, rowIndex):
        #self.editedFields[rowIndex] = anObject
        self.updateList('Name', anObject)

    # delegate methods
    # def tableView_shouldSelectRow_(self, aTableView, rowIndex):
    #     # only allow odd rows to be selected
    #     return rowIndex % 2
    #
    # def tableView_shouldEditTableColumn_row_(self, aTableView, aTableColumn, rowIndex):
    #     # only allow cells in the second column in odd rows to be edited
    #     return (rowIndex % 2) and aTableColumn.identifier() == "col_2"

    def tableViewSelectionDidChange_(self, notification):
        # Always use this delegate method instead of using the action to do something
        # when the selection changed: the action method is only called when the selection
        # changed by means of a mouse click; this method is also called when the
        # user uses the arrow keys.
        self.row = self.tableView.selectedRow()

        self.txtDirectory.setStringValue_(self.data.liste[self.row]['DocumentRoot'])
        self.txtServName.setStringValue_(self.data.liste[self.row]['ServerName'])
        self.defaultSite.setState_(self.data.liste[self.row]['default'])


    # def windowShouldClose_(self, sender):
    #     print("Should Close?")
    #     return 0

    def windowWillClose_(self, aNotification):
        print('window will close')
        NSApp().terminate_(self)

if __name__ == "__main__":
    app = NSApplication.sharedApplication()

    # Initiate the controller with a XIB
    viewController = VhostController.alloc().initWithWindowNibName_("VhostSwitcher")

    # Show the window
    viewController.showWindow_(viewController)

    # Bring app to top
    NSApp.activateIgnoringOtherApps_(True)

    from PyObjCTools import AppHelper
    AppHelper.runEventLoop()
