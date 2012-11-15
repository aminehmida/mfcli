#!/usr/bin/env python

import os
import urllib2
import MediaFire
import json
import pdb
import ConfigParser
from optparse import OptionParser

class MediaFireOps:
    def __init__(self, APP_ID, APP_KEY, user, password):
        self.auth_user = MediaFire.MediaFireUser(APP_ID, API_KEY)
        self.auth_user.get_session_token(user, password)
        
    def getFolderContient(self, folder_key=None, contentType="files"):
        self.myFolder = MediaFire.MediaFireFolder(folder_key, self.auth_user)
        return self.myFolder.get_content(content_type=contentType)[contentType]

    def uploadFile(self, fileName, folderKey = None):
        self.myUploader = MediaFire.MediaFireUpload(self.auth_user)
        self.myUploader.upload(fileName, folderKey)

    def uploadFolder(self, localFolder, folderKey = None):
        self.myFolder = MediaFire.MediaFireFolder(folderKey, self.auth_user)
        
        if localFolder[-1] == '/':
            localFolderName = localFolder[0:-1]
        else:
            localFolderName = localFolder
        localFolderName = os.path.basename(localFolderName)
        
        newFolderKey = self.myFolder.create(localFolderName, folderKey)[0] #DONE: extract folder name
        for f in os.listdir(localFolder):
            if os.path.isfile(os.path.join(localFolder,f)):
                self.uploadFile(os.path.join(localFolder,f),newFolderKey)
            elif os.path.isdir(os.path.join(localFolder,f)):
                self.uploadFolder(os.path.join(localFolder,f),newFolderKey)
                
    def downloadFile(self, file_key, destFolder=None):
        self.mf_file = MediaFire.MediaFireFile(file_key, user=self.auth_user)
        try:
            url = self.mf_file.get_links()['links'][0]['direct_download']
        except:
            print 'can not extract direct link'
            exit()
        file_name = url.split('/')[-1]
        u = urllib2.urlopen(url)
        
        if not(destFolder):
            destFolder = ''
        if destFolder and destFolder[-1] != '/':
            destFolder = destFolder+'/'

        f = open(destFolder+file_name, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (file_name, file_size)

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
            print status,
        f.close()

    def getFileInfo(self, fileKey):
        self.mf_file = MediaFire.MediaFireFile(fileKey, user=self.auth_user)
        return self.mf_file.get_info()
        
    def getFolderInfo(self, folderKey):
        self.mf_folder = MediaFire.MediaFireFolder(folderKey, user=self.auth_user)
        return self.mf_folder.get_info
        
    def downloadFolder(self, folderKey=None, destFolder=None):
        #download root files
        for userFile in self.getFolderContient(folderKey):
            self.auth_user.get_session_token(user, password)
            self.downloadFile(userFile['quickkey'])
                
def optValidator(val1, val2, fatal=None):
    if val1:
        return val1
    if val2:
        return val2
    if fatal:
        print "[x] "+fatal
        exit()
    return None

def ppdic(dic, spaces=1):
    big = max([ len(str(x)) for x in dic])
    for x in dic:
        print x + ':' + (big-len(x)+spaces)*' '+dic[x]    


parser = OptionParser()

parser.add_option("-k", "--api-key", dest="API_KEY", action="store",
                  help="application API_KEY", metavar="API_KEY")
parser.add_option("-a", "--app-id", dest="APP_ID", action="store",
                  help="application API_KEY", metavar="APP_ID")
parser.add_option("-u", "--user-email", dest="user", action="store",
                  help="user email", metavar="user@email.com")
parser.add_option("-p", "--user-password", dest="password", action="store",
                  help="user password", metavar="p@ssw0rd")
parser.add_option("-o", "--operation", dest="operation", action="store",
                  help="operation to performe on your folder. Possible operations are: (Move, list)",
                  metavar="[list, move, copie, download, ...]")                 
parser.add_option("-t", "--type", dest="list_type", action="store",
                  help="listing type : files or folders", metavar="[files|folders]")
parser.add_option("-i", "--identifier", dest="ident", action="store",
                  help="file or folder identifier", metavar="xxxxxxxxxxxxx")
parser.add_option("-d", "--destination", dest="dest", action="store",
                  help="where to download file/folder to. default = current directory",
                  metavar="/home/linux/myfiles")
parser.add_option("-l", "--local-file", dest="upFile", action="store",
                  help="local file to upload", metavar="/home/linux/myfile")
parser.add_option("-c", "--config-file", dest="config", action="store",
                  help="configuration file can be used to store parameters. if configuration file is provide, it is previleged",
                  metavar="p@ssw0rd")
(options,args) = parser.parse_args()

c = ConfigParser.RawConfigParser()

#pdb.set_trace()

if options.config:
    cfgFile = options.config
else:
    cfgFile = os.path.expanduser("~/.mfcli.conf") 
    if not(os.path.exists(cfgFile)):
        cfgFile = None
if cfgFile:
    try:
        c.read(cfgFile)
        API_KEY = c.get('application_settings', 'API_KEY')
        APP_ID = c.get('application_settings', 'APP_ID')
        user = c.get('user_settings', 'user')
        password = c.get('user_settings', 'password')
    except:
        print "[!] can not open config file, ignoring it ..."

    API_KEY = optValidator(options.API_KEY, API_KEY, "Must give a valid mediafire API key")
    APP_ID = optValidator(options.APP_ID, APP_ID, "Must give a valid mediafire application ID")
    user = optValidator(options.user, user)
    if user :
        msg = "an user name is specified, must give corresponding password"
    else:
        msg = None
    password = optValidator(options.password, password, msg)

mfOps = MediaFireOps(APP_ID, API_KEY, user, password)

if options.operation == "list":
    if options.list_type == "files" :
        for f in mfOps.getFolderContient(folder_key=options.ident, contentType=options.list_type):
            print(f['quickkey']+"\t"+f['size']+"\t\t"+f['filename'])
    elif options.list_type == "folders" :
        for f in mfOps.getFolderContient(folder_key=options.ident, contentType=options.list_type):
            print(f['folderkey']+"\t"+str(int(f['file_count'])+int(f['folder_count']))+"\t\t"+f['name'])
    else:
        print '[x] Must specifie files or folders'
        
elif options.operation == "download" :
    if options.ident :
        if len(options.ident) == 13 : #folder
            mfOps.downloadFolder(options.ident, options.dest)
        else:
            mfOps.downloadFile(options.ident, options.dest)
    else:
        print '[!] Must specifie file or folder key'

elif options.operation == "upload" :
    if os.path.isfile(options.upFile):
        mfOps.uploadFile(options.upFile, options.ident)
    else:
        mfOps.uploadFolder(options.upFile, options.ident)

elif options.operation == "info" :
    if len(options.ident) == 13 : #Folder
        ppdic(mfOps.getFolderInfo(options.ident), 6)
    else:
        ppdic(mfOps.getFileInfo(options.ident), 6)
    
    
    

