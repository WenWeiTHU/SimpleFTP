#!/usr/bin/ python3
# -*- coding: utf-8 -*-

import sys, os, re
import subprocess
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from client import ClientCmd
from socket import *
import os


class FileSignals(QObject):
    filename = pyqtSignal(str)
    rename = pyqtSignal(str)
    fileinfo = pyqtSignal(str)


class DirSignals(QObject):
    dirname = pyqtSignal(str)
    removedir = pyqtSignal(str)


class CreateDirSignals(QObject):
    updatedir = pyqtSignal()
    createdir = pyqtSignal()


class FileWidget(QTreeView):
    def __init__(self):
        '''Local file widget'''
        super(FileWidget, self).__init__()
        self.model = QFileSystemModel()
        self.setModel(self.model)
        self.setRootIndex(self.model.setRootPath(os.getcwd()))
        self.fileMenu = QMenu(self)
        self.fileSignals = FileSignals()
        self.selectedFilename = ''
        self.fileMenu.addAction(QAction('Store remote', self,
        triggered = lambda: self.fileSignals.filename.emit(self.selectedFilename)))

    def mousePressEvent(self, event):
        super(FileWidget, self).mousePressEvent(event)
        if event.button() == Qt.RightButton:
            item = self.indexAt(self.viewport().mapFromGlobal(QCursor.pos()))
            self.showMenu(item)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.indexAt(self.viewport().mapFromGlobal(QCursor.pos()))
            self.selectedFilename = self.model.filePath(item)
            self.fileSignals.filename.emit(self.selectedFilename)
    
    def showMenu(self, item):
        if item and not self.model.isDir(item):
            self.selectedFilename = self.model.filePath(item)
            self.fileMenu.exec_(QCursor.pos())    


class RemoteFileWidget(QListWidget):
    def __init__(self):
        '''Remote file widget'''
        super(RemoteFileWidget, self).__init__()
        self.fileMenu = QMenu(self)
        self.dirMenu = QMenu(self)
        self.createDirMenu = QMenu(self)
        self.fileSignals = FileSignals()
        self.dirSignals = DirSignals()
        self.createDirSignals = CreateDirSignals()
        self.selectedName = ''
        self.fileMenu.addAction(QAction('Retrieve local', self,
        triggered = lambda : self.fileSignals.filename.emit(self.selectedName)))
        self.fileMenu.addAction(QAction('File info', self,
        triggered = lambda : self.fileSignals.fileinfo.emit(self.selectedName)))
        self.fileMenu.addAction(QAction('Rename file', self,
        triggered = lambda : self.fileSignals.rename.emit(self.selectedName)))
        self.dirMenu.addAction(QAction('Open directory', self,
        triggered = lambda : self.dirSignals.dirname.emit(self.selectedName)))
        self.dirMenu.addAction(QAction('Remove directory', self,
        triggered = lambda : self.dirSignals.removedir.emit(self.selectedName)))
        self.createDirMenu.addAction(QAction('Create directory', self,
        triggered = lambda : self.createDirSignals.createdir.emit()))
        self.createDirMenu.addAction(QAction('Update directory', self,
        triggered = lambda : self.createDirSignals.updatedir.emit()))

    def mousePressEvent(self, event):
        super(RemoteFileWidget, self).mousePressEvent(event)
        if event.button() == Qt.RightButton:
            item = self.indexAt(self.viewport().mapFromGlobal(QCursor.pos()))
            self.showMenu(item)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.indexAt(self.viewport().mapFromGlobal(QCursor.pos()))
            if item.data():
                self.selectedName = item.data()
                if item.data() and item.data()[-1] == '/':
                    self.dirSignals.dirname.emit(self.selectedName)
                elif item.data():
                    self.fileSignals.filename.emit(self.selectedName)

    def showMenu(self, item):
        if item.data():
            self.selectedName = item.data()
            if item.data()[-1] == '/':
                # is directory
                self.dirMenu.exec_(QCursor.pos())
            else:
                # is file
                self.fileMenu.exec_(QCursor.pos())  
        else:
            self.createDirMenu.exec_(QCursor.pos())  

    def updateFiles(self, filesStr, isRoot):
        self.clear()
        if not isRoot:
            parentDir = QListWidgetItem('../')
            parentDir.name = '..'
            self.addItem(parentDir)
        files = filesStr.split('\n')
        for line in files:
            if line.strip() == '':
                continue
            name = line.split(' ')[-1]

            if line[0] == '<':
                file_type = line[2]
            else:
                file_type = line[0]

            if file_type == 'd':
                fItem = QListWidgetItem(name + '/')
                fItem.name = name
                self.addItem(fItem)
            elif file_type == '-':
                fItem = QListWidgetItem(name)
                fItem.name = name
                self.addItem(fItem)


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()  
        self.port = 20000
        self.status = 'begin'
        self.isRoot = True
        self.initUI()
        self.initSlot()

    def initUI(self):
        '''Create UI and init the layout'''
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        self.IPLabel = QLabel('IP')
        self.PortLabel = QLabel('Port')
        self.IPText = QLineEdit()
        self.PortText = QLineEdit()
        self.PortText.setValidator(QIntValidator(0, 65535))
        self.IPText.setPlaceholderText('Input IP, like 127.0.0.1')
        self.PortText.setPlaceholderText('Input port number')
        self.ConnectButton = QPushButton('Connect')
        
        self.UserLabel = QLabel('User')
        self.PasswdLabel = QLabel('Password')
        self.UserText = QLineEdit()
        self.PasswdText = QLineEdit()
        self.UserText.setPlaceholderText('Input username')
        self.PasswdText.setPlaceholderText('Input password')
        self.PasswdText.setEchoMode(QLineEdit.Password)
        self.LoginButton = QPushButton('Login')
        self.HelpButton = QPushButton('Help')

        self.PasvModeCKBox = QCheckBox('Passive Mode')
        self.PasvModeCKBox.setChecked(True)
        self.SystButton = QPushButton('System Info')
        self.QuitButton = QPushButton('QUIT')
        self.QuitButton.setStyleSheet("background-color: red")
        self.ListButton = QPushButton('Update')
        self.TypeIButton = QPushButton('Binary mode')
        self.TypeAButton = QPushButton('Ascii mode')

        self.RequestLabel = QLabel('Request Prompt')
        self.RequestText = QTextBrowser()
        self.ResponseLabel = QLabel('Response & Error Prompt')
        self.ResponseText = QTextBrowser()
        self.BrandLabel = QLabel('- Powered by WenweiTHU')

        self.LocalFileLabel = QLabel('Local Files')
        self.RemoteFileLabel = QLabel('Remote Files')
        self.CurDirLabel = QLabel('Current Directory: ')
        self.LocalFileShow = FileWidget()
        self.RemoteFileShow = RemoteFileWidget()
        self.setStatusTip('Simple FTP Client')

        self.IPText.setClearButtonEnabled(True)
        self.PortText.setClearButtonEnabled(True)
        self.UserText.setClearButtonEnabled(True)
        self.PasswdText.setClearButtonEnabled(True)
        self.RequestText.setFontFamily('Consolas')
        self.RequestText.setFontPointSize(10)

        self.RetriProgLabel = QLabel('Progress: ')
        self.RetriProgBar = QProgressBar()
        
        self.grid.addWidget(self.IPLabel, 0, 0, 1, 1)
        self.grid.addWidget(self.IPText, 0, 1, 1, 2)
        self.grid.addWidget(self.PortLabel, 0, 4, 1, 1)
        self.grid.addWidget(self.PortText, 0, 5, 1, 2)
        self.grid.addWidget(self.ConnectButton, 0, 7)
        self.grid.addWidget(self.UserLabel, 1, 0, 1, 1)
        self.grid.addWidget(self.UserText, 1, 1, 1, 2)
        self.grid.addWidget(self.PasswdLabel, 1, 4, 1, 1)
        self.grid.addWidget(self.PasswdText, 1, 5, 1, 2)
        self.grid.addWidget(self.LoginButton, 1, 7)
        self.grid.addWidget(self.PasvModeCKBox, 2, 0)
        self.grid.addWidget(self.HelpButton, 2, 1, 1, 1)
        self.grid.addWidget(self.SystButton, 2, 2, 1, 1)
        self.grid.addWidget(self.ListButton, 2, 4)
        self.grid.addWidget(self.TypeIButton, 2, 5)
        self.grid.addWidget(self.TypeAButton, 2, 6)
        self.grid.addWidget(self.QuitButton, 2, 7)
        self.grid.addWidget(self.RequestLabel, 3, 0)
        self.grid.addWidget(self.RequestText, 4, 0, 1, 3)
        self.grid.addWidget(self.ResponseLabel, 3, 4)
        self.grid.addWidget(self.ResponseText, 4, 4, 1, 4)

        self.grid.addWidget(self.LocalFileLabel, 5, 4)
        self.grid.addWidget(self.LocalFileShow, 6, 4, 1, 4)

        self.grid.addWidget(self.RemoteFileLabel, 5, 0, 1, 1)
        self.grid.addWidget(self.CurDirLabel, 7, 0, 1, 4)
        self.grid.addWidget(self.BrandLabel, 7, 7, 1, 1)
        self.grid.addWidget(self.RemoteFileShow, 6, 0, 1, 3)
        
        self.grid.addWidget(self.RetriProgLabel, 8, 0, 1, 1)
        self.grid.addWidget(self.RetriProgBar, 8, 1, 1, 7)
            
        self.move(300, 150)
        self.resize(1000,800)
        self.setWindowTitle('SFClient')
        self.show()

    def initSlot(self):
        '''Init signal connections'''
        self.ConnectButton.clicked.connect(self.initConnect)
        self.LoginButton.clicked.connect(self.login)
        self.SystButton.clicked.connect(self.systemInfo)
        self.TypeAButton.clicked.connect(self.switchTypeA)
        self.TypeIButton.clicked.connect(self.switchTypeI)
        self.HelpButton.clicked.connect(self.helpInfo)
        self.ListButton.clicked.connect(self.updateFileList)
        self.QuitButton.clicked.connect(self.quitConnection)
        self.LocalFileShow.fileSignals.filename.connect(self.storeFile)
        self.RemoteFileShow.fileSignals.filename.connect(self.retriFile)
        self.RemoteFileShow.fileSignals.fileinfo.connect(self.infoFile)
        self.RemoteFileShow.fileSignals.rename.connect(self.renameFile)
        self.RemoteFileShow.dirSignals.dirname.connect(self.openDir)
        self.RemoteFileShow.dirSignals.removedir.connect(self.removeDir)
        self.RemoteFileShow.createDirSignals.createdir.connect(self.createDir)
        self.RemoteFileShow.createDirSignals.updatedir.connect(self.updateFileList)
        
    def initConnect(self):
        '''Connect button pushed'''
        if self.PortText.text() != '':
            self.cmd = ClientCmd(self.IPText.text(), int(self.PortText.text()))
            response = self.cmd.initConnection()
            self.RequestText.append('> Connect to '+self.IPText.text()+': '+self.PortText.text()+'\n')
            self.ResponseText.append(response)
            if response[2:5] == '220':
                self.status = 'connected'
        else:
            self.ResponseText.append('# Error: Input IP and Port first\n')

    def login(self):
        '''Login button pushed'''
        if self.status == 'connected':
            response = self.cmd.msgProc('USER '+self.UserText.text())
            self.RequestText.append('> USER '+self.UserText.text()+'\n')
            self.ResponseText.append(response)
            if response[2:5] == '331':
                response = self.cmd.msgProc('PASS '+self.PasswdText.text())
                self.RequestText.append('> PASS '+'*'*len(self.PasswdText.text())+'\n')
                self.ResponseText.append(response)
                if response[2:5] == '230':
                    self.status = 'logged'
                    self.updateFileList()
                    self.curDir()
                    self.isRoot = True
                    self.root_remote = self.cur_remote
                else:
                    self.ResponseText.append('# Error: Password invalid\n')
            else:
                self.ResponseText.append('# Error: Username invalid\n')
        elif self.status == 'logged':
            self.ResponseText.append('# Error: You have logged in\n')
        elif self.status == 'begin':
            self.ResponseText.append('# Error: Please connect first\n')

    def systemInfo(self):
        '''System info button pushed'''
        if self.status == 'begin' or self.status == 'connected':
            self.ResponseText.append('# Error: Please log in first\n')
        else:
            response = self.cmd.msgProc('SYST')
            self.RequestText.append('> SYST\n')
            self.ResponseText.append(response)

    def switchTypeA(self):
        '''Type A button pushed'''
        if self.status == 'begin' or self.status == 'connected':
            self.ResponseText.append('# Error: Please log in first\n')
        else:
            response = self.cmd.msgProc('TYPE A')
            self.RequestText.append('> TYPE A\n')
            self.ResponseText.append(response)

    def switchTypeI(self):
        '''Type I button pushed'''
        if self.status == 'begin' or self.status == 'connected':
            self.ResponseText.append('# Error: Please login first\n')
        else:
            response = self.cmd.msgProc('TYPE I')
            self.RequestText.append('> TYPE I\n')
            self.ResponseText.append(response)

    def storeFile(self, filename):
        '''Type I -> PORT/PASV -> STOR'''
        if self.status == 'begin' or self.status == 'connected':
            self.ResponseText.append('# Error: Please login first\n')
        else:
            self.switchTypeI()
            if self.PasvModeCKBox.isChecked():
                response = self.cmd.msgProc('PASV')
                self.RequestText.append('> PASV\n')
                self.ResponseText.append(response)
            else:
                ip = self.cmd.getLocalIP()
                p1 = self.port // 256
                p2 = self.port % 256
                param = ','.join(ip.split('.')) + ',' + str(p1) + ',' + str(p2)
                response = self.cmd.msgProc('PORT ' + param)
                self.ResponseText.append(response)
                self.RequestText.append('> PORT ' + param + '\n')
                self.port += 2
                if self.port > 65535:
                    self.port = 20000
            if (self.PasvModeCKBox.isChecked() and response[2:5] == '227') \
                or (not self.PasvModeCKBox.isChecked() and response[2:5] == '200'):
                self.RequestText.append('> STOR ' + filename + '\n')
                response = self.cmd.msgProc('STOR '+filename)
                self.ResponseText.append(response)
                self.updateFileList()

    def retriFile(self, filename):
        '''Type I -> PORT/PASV -> RETR'''
        if self.status == 'begin' or self.status == 'connected':
            self.ResponseText.append('# Error: Please login first\n')
        else:
            self.switchTypeI()
            if self.PasvModeCKBox.isChecked():
                response = self.cmd.msgProc('PASV')
                self.RequestText.append('> PASV\n')
                self.ResponseText.append(response)
            else:
                ip = self.cmd.getLocalIP()
                p1 = self.port // 256
                p2 = self.port % 256
                param = ','.join(ip.split('.')) + ',' + str(p1) + ',' + str(p2)
                
                response = self.cmd.msgProc('PORT ' + param)
                
                self.ResponseText.append(response)
                self.RequestText.append('> PORT ' + param + '\n')
                self.port += 2
                if self.port > 65535:
                    self.port = 20000
            if (self.PasvModeCKBox.isChecked() and response[2:5] == '227') \
                or (not self.PasvModeCKBox.isChecked() and response[2:5] == '200'):
                if os.path.exists(filename):
                    self.cmd.total_write = os.stat(filename).st_size
                    self.RequestText.append('> REST ' + str(self.cmd.total_write) + '\n')
                    response = self.cmd.msgProc('REST ' + str(self.cmd.total_write))
                    self.ResponseText.append(response)
                else:
                    self.cmd.total_write = 0
                self.RequestText.append('> RETR ' + filename + '\n')
                response = self.retriProcBar(filename)
                self.ResponseText.append(response)

    def retriProcBar(self, filename):
        out_msg = ''
        if self.cmd.transfer_mode == '':
            out_msg += '# Error: Use PASV/PORT first\n'
            return out_msg

        self.cmd.cli_sock.send(bytes('RETR ' + filename + '\r\n', encoding='utf8'))
        if self.cmd.transfer_mode == 'pasv':
            self.cmd.connect_sock = socket(AF_INET, SOCK_STREAM)
            self.cmd.connect_sock.connect((self.cmd.file_ip, self.cmd.file_port))
        elif self.cmd.transfer_mode == 'port':
            self.cmd.connect_sock, addr = self.cmd.listen_sock.accept()
          
        raw_response = self.cmd.cli_sock.recv(self.cmd.BUFSIZE)
        response = str(raw_response, encoding='utf8')
        matches = re.findall(r'(\d+) byte', response)
        if len(matches) != 0:
            self.cmd.filesize = int(matches[0])
        out_msg += '< ' 
        out_msg += response
        state_code, msg = self.cmd.parseResponse(response)
        if state_code == 150:
            with open(filename, 'ab') as f:
                while True:
                    buf_read = self.cmd.connect_sock.recv(self.cmd.BUFSIZE)
                    write_n = f.write(buf_read)
                    self.cmd.total_write += write_n
                    self.RetriProgBar.setValue(100 * (self.cmd.total_write+1) / (self.cmd.filesize+1))
                    if write_n == 0:
                        break
        else:
            out_msg += '# Error: Transfer failed\n'

        self.cmd.connect_sock.close()
        if self.cmd.transfer_mode == 'port':
            self.cmd.listen_sock.close()
        self.cmd.transfer_mode = ''
        raw_response = self.cmd.cli_sock.recv(self.cmd.BUFSIZE)
        response = str(raw_response, encoding='utf8')
        if self.cmd.total_write == self.cmd.filesize:
            self.cmd.total_write = 0
            self.cmd.filesize = 0
        out_msg += '< ' 
        out_msg += response

        return out_msg
    
    def renameFile(self, oldname):
        '''RNFR I -> RNTO'''
        newname, confirm = QInputDialog.getText(self,'Rename',"Set a new file name: ", QLineEdit.Normal, oldname)
        if not confirm:
            return
        response = self.cmd.msgProc('RNFR ' + oldname)
        self.RequestText.append('> RNFR ' + oldname + '\n')
        self.ResponseText.append(response)
        if response[2:5] == '350':
            response = self.cmd.msgProc('RNTO ' + newname)
            self.RequestText.append('> RNFR ' + newname + '\n')
            self.ResponseText.append(response)
            self.updateFileList()
        else:
            self.ResponseText.append('# Error: File not exist or permission denied\n')
    
    def createDir(self):
        '''MKD by inputDialog'''
        if self.status == 'begin' or self.status == 'connected':
            self.ResponseText.append('# Error: Please login first\n')
            return
        newdir, confirm = QInputDialog.getText(self,'Create Directory',"Set a new directory name: ", QLineEdit.Normal, 'folder')
        if not confirm:
            return
        response = self.cmd.msgProc('MKD ' + newdir)
        self.RequestText.append('> MKD ' + newdir + '\n')
        self.ResponseText.append(response)
        if response[2:5] == '250' or response[2:5] == '257':
            self.updateFileList()
        else:
            self.ResponseText.append('# Error: Permission denied\n')

    def openDir(self, dirname):
        '''CWD filename'''
        response = self.cmd.msgProc('CWD ' + dirname)
        self.RequestText.append('> CWD ' + dirname + '\n')
        self.ResponseText.append(response)
        if response[2:5] == '250' or response[2:5] == '200':
            self.curDir()
            if self.cur_remote == self.root_remote:
                self.isRoot = True
            else:
                self.isRoot = False
            self.updateFileList()
        else:
            self.ResponseText.append('# Error: Directory not exist or permission denied\n')

    def removeDir(self, dirname):
        '''RMD filename'''
        response = self.cmd.msgProc('RMD ' + dirname)
        self.RequestText.append('> RMD ' + dirname + '\n')
        self.ResponseText.append(response)
        if response[2:5] == '250':
            self.updateFileList()
        else:
            self.ResponseText.append('# Error: Permissiondenied or directory not empty\n')

    def curDir(self):
        '''PWD'''
        response = self.cmd.msgProc('PWD')
        self.RequestText.append('> PWD\n')
        self.ResponseText.append(response)
        if response[2:5] == '257':
            matches = re.findall(r'".+"', response)
            if matches:
                self.cur_remote = matches[0]
                self.CurDirLabel.setText('Current Directory: ' + self.cur_remote)
            self.updateFileList()
        else:
            self.ResponseText.append('# Error: Directory not exist or permission denied\n')

    def updateFileList(self):
        '''Invoked whenever the directory has changed'''
        fileStr = '\n'.join(self.listFile().split('\n')[1:-2])
        self.RemoteFileShow.updateFiles(fileStr, self.isRoot)

    def listFile(self, filename = ''):
        '''List Directory'''
        if self.status == 'begin' or self.status == 'connected':
            self.ResponseText.append('# Error: Please login first\n')
            return ''
        else:
            self.switchTypeA()
            if self.PasvModeCKBox.isChecked():
                response = self.cmd.msgProc('PASV')
                self.RequestText.append('> PASV\n')
                self.ResponseText.append(response)
            else:
                ip = self.cmd.getLocalIP()
                p1 = self.port // 256
                p2 = self.port % 256
                param = ','.join(ip.split('.')) + ',' + str(p1) + ',' + str(p2)
                response = self.cmd.msgProc('PORT ' + param)
                self.ResponseText.append(response)
                self.RequestText.append('> PORT ' + param + '\n')
                self.port += 2
                if self.port > 65535:
                    self.port = 20000 
            if (self.PasvModeCKBox.isChecked() and response[2:5] == '227') \
                or (not self.PasvModeCKBox.isChecked() and response[2:5] == '200'): 
                response = self.cmd.msgProc('LIST ' + filename)
                response = response.replace('\r\n', '\n')
                self.RequestText.append('> LIST ' + filename + '\n')
                self.ResponseText.append(response.split('\n')[0])
                self.ResponseText.append(response.split('\n')[-2] + '\n')
                return response
            else:
                return ''

    def infoFile(self, filename):
        '''LIST filename'''
        if self.status == 'begin' or self.status == 'connected':
            self.ResponseText.append('# Error: Please login first\n')
            return ''
        else:
            self.switchTypeA()
            if self.PasvModeCKBox.isChecked():
                response = self.cmd.msgProc('PASV')
                self.RequestText.append('> PASV\n')
                self.ResponseText.append(response)
            else:
                ip = self.cmd.getLocalIP()
                p1 = self.port // 256
                p2 = self.port % 256
                param = ','.join(ip.split('.')) + ',' + str(p1) + ',' + str(p2)
                response = self.cmd.msgProc('PORT ' + param)
                self.ResponseText.append(response)
                self.RequestText.append('> PORT ' + param + '\n')
                self.port += 2
                if self.port > 65535:
                    self.port = 20000 
            if (self.PasvModeCKBox.isChecked() and response[2:5] == '227') \
                or (not self.PasvModeCKBox.isChecked() and response[2:5] == '200'): 
                response = self.cmd.msgProc('LIST ' + filename)
                self.RequestText.append('> LIST ' + filename + '\n')
                self.ResponseText.append(response)
            else:
                self.ResponseText.append('# Error: File not exist or permission denied\n')

    def helpInfo(self):
        '''Show some help information of SFClient'''
        self.ResponseText.append('~ This is a simple FTP client based on BSD socket annd PyQt5\r\n')
        self.ResponseText.append('~ You can first connect to a remote server and then login in\r\n')
        self.ResponseText.append('~ Buttons click will be translated into standard FTP commands\r\n')
        self.ResponseText.append('~ Commands sent are show in the left prompt, and responsed in the right\r\n')
        self.ResponseText.append('~ Leading Symbols definition:\r\n')
        self.ResponseText.append('~ "~": Helping message\r\n')
        self.ResponseText.append('~ ">": Request of client\r\n')
        self.ResponseText.append('~ "<": Response from server\r\n')
        self.ResponseText.append('~ "#": Error detected\r\n')
        self.ResponseText.append('~ Double click the item of file-list for transfering\r\n')
        self.ResponseText.append('~ Right click the item or blank area for more options\r\n')
        self.ResponseText.append('~ Have a nice day!\r\n')

    def quitConnection(self):
        '''Quit button pushed'''
        if self.status == 'begin':
            self.ResponseText.append('# Error: Please log in first\n')
        else:
            response = self.cmd.msgProc('QUIT')
            self.RequestText.append('> QUIT\n')
            self.ResponseText.append(response)
            self.status = 'begin'
            if self.RemoteFileShow:
                self.RemoteFileShow.clear()


if __name__ == '__main__': 
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())
