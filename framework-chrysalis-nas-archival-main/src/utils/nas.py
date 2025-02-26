from smb.SMBConnection import SMBConnection
import os
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

from .log import log

class NAS:
    def __init__(self, nas_dest_dir = None):
        if nas_dest_dir is not None:
            self.nas_dest_dir = self.addSlashtoPath(nas_dest_dir)
        else:
            if os.getenv("NAS_DEST_DIR") is not None:
                self.nas_dest_dir = self.addSlashtoPath(os.getenv("NAS_DEST_DIR"))
            else:
                self.nas_dest_dir = ""
        self.nas_base = os.getenv("NAS_BASE")
        self.conn = ''
    def nas_connect(self):
        try:
            try:
                nas_name = os.getenv('NAS_HOST')
                nas_user = os.getenv('NAS_USER')
                nas_password = os.getenv('NAS_SECRET')
            except Exception as error:
                errorMsg = "Could not retrieve environment variables. Error was: {}".format(error)
                log.critical(errorMsg)
            self.conn = SMBConnection(nas_user, nas_password, nas_name, '', domain='MS', use_ntlm_v2 = True)
            self.conn.connect(nas_name)
            infoMsg = "Connected to NAS server"
            log.info(infoMsg)
            return self.conn
        except Exception as error:
            errorMsg = "Could not connect to NAS server"
            log.critical(errorMsg)
            raise error
    def nas_disconnect(self):
        try:
            self.conn.close()
        except Exception:
            errorMsg = "Could not disconnect to NAS server"
            log.critical(errorMsg)
    def set_one_nas_file(self, local_files_dir, local_file_name, new_file_name = None, altRemoteDir = None):
        try:
            if altRemoteDir is not None:
                self.remote_dest_dir = self.addSlashtoPath(altRemoteDir)
                remoteFileList = self.listRemoteFiles(altRemoteDir)
            else:
                self.remote_dest_dir = self.nas_dest_dir
                remoteFileList = self.listRemoteFiles()
            invalidChar = [":", "/", "\\", "?", "*"]#invalid characters for a filename
            try:
                for filename in self.listLocalFiles(local_files_dir): 
                    self.containsInvalidChar = False
                    local_file_path = os.path.join(local_files_dir, filename)
                    if filename == local_file_name:
                        if new_file_name is not None:
                            if local_file_name[-4:] != new_file_name[-4:]:
                                print("The file extension of the new file name {} does not match the file extension of the old file name {}. The old file name will be used instead.".format(new_file_name, local_file_name))
                            else:
                                local_file_name = new_file_name
                        #check to see if it already exists in the NAS folder
                        if local_file_name not in remoteFileList:
                            if local_file_name.endswith((".txt", ".dat", ".TXT", ".DAT", ".json", ".xml")):
                                for char in invalidChar:
                                    if char in local_file_name:
                                        self.containsInvalidChar = True
                                        errorMsg = "Your file name {} contains {} which is an invalid character. Please change the file name".format(local_file_name, char)
                                        log.error(errorMsg)
                                if self.containsInvalidChar is False:
                                    with open(local_file_path, 'rb') as fileObj:
                                        self.conn.storeFile(self.nas_base, self.remote_dest_dir + local_file_name, fileObj)
                                        infoMsg = "Added {} to the {} directory".format(local_file_name, self.remote_dest_dir)
                                        log.info(infoMsg)
                            else:
                                errorMsg = "{} file is not a text or data file.".format(local_file_name)
                                log.error(errorMsg)
                                os._exit(-1)
                        else:
                            errorMsg = "{} already exists in the {} directory".format(local_file_name, self.remote_dest_dir)
                            log.error(errorMsg)
            except TypeError as e: # if list returned is None
                if self.listRemoteFiles() is None:
                    errorMsg = "Could not retrieve {} directory list".format(self.remote_dest_dir)
                elif self.listLocalFiles(local_files_dir) is None:
                    errorMsg = "Could not retrieve {} directory list".format(local_files_dir)
                log.error(errorMsg)
                raise e
        except Exception as error:
            errorMsg = "Could not store {} file".format(local_file_name)
            log.critical(errorMsg)
            raise error
    def set_nas_files(self, local_files_dir, altRemoteDir = None):
        try:
            if altRemoteDir is not None:
                if len(self.listLocalFiles(local_files_dir)) > 100:
                    self.set_large_nas_files(local_files_dir, altRemoteDir)
                else:
                    self.set_small_nas_files(local_files_dir, altRemoteDir)
            else: # if altRemoteDir is None
                if len(self.listLocalFiles(local_files_dir)) > 100:
                    self.set_large_nas_files(local_files_dir)
                else:
                    self.set_small_nas_files(local_files_dir)
        except Exception:
            errorMsg = "Could not store files"
            log.critical(errorMsg)
    def set_small_nas_files(self, local_files_dir, altRemoteDir = None):
        try:
            try:
                if altRemoteDir is not None:
                    if not self.directoryExists(altRemoteDir):
                        self.createDir(altRemoteDir)
                    self.remote_dest_dir = self.addSlashtoPath(altRemoteDir)
                    remoteFilesList = self.listRemoteFiles(altRemoteDir)
                else:
                    if not self.directoryExists():
                        self.createDir()
                    self.remote_dest_dir = self.nas_dest_dir
                    remoteFilesList = self.listRemoteFiles()
            except Exception:
                errorMsg = "Could not create {} directory".format(self.remote_dest_dir)
                log.error(errorMsg)
            invalidChar = [":", "/", "\\", "?", "*"]#invalid characters for a filename
            try:
                for filename in self.listLocalFiles(local_files_dir):
                    self.containsInvalidChar = False
                    local_file_path = os.path.join(local_files_dir, filename)
                    if os.path.isfile(local_file_path):
                        if filename not in remoteFilesList:
                            if filename.endswith((".txt", ".dat", ".json")):
                                for char in invalidChar:
                                    if char in filename:
                                        self.containsInvalidChar = True
                                        errorMsg = "Your file name {} contains {} which is an invalid character. Please change the file name".format(filename, char)
                                        log.error(errorMsg)
                                if self.containsInvalidChar is False:
                                    with open(local_file_path, 'rb') as fileObj:
                                        self.conn.storeFile(self.nas_base, os.path.join(self.remote_dest_dir, filename), fileObj)
                                        if len(self.listLocalFiles(local_files_dir)) <= 10:
                                            infoMsg = "Added {} to the {} directory".format(filename, self.remote_dest_dir)
                                            log.info(infoMsg)
                            else:
                                errorMsg = "{} file is not a text or data file.".format(filename)
                                log.warning(errorMsg)
                        else:
                            errorMsg = "{} already exists in the {} directory".format(filename, self.remote_dest_dir)
                            log.error(errorMsg)
                print("Finished adding files to the remote directory")
            except TypeError as e: # if list returned is None
                if self.listRemoteFiles() is None:
                    errorMsg = "Could not retrieve {} directory list".format(self.remote_dest_dir)
                    log.error(errorMsg)
                if self.listLocalFiles(local_files_dir) is None:
                    errorMsg = "Could not retrieve {} directory list".format(local_files_dir)
                    log.error(errorMsg)
                raise e
        except Exception as error:
            errorMsg = "Could not store {} file".format(filename)
            log.error(errorMsg)
            raise error
    def set_large_nas_files(self, local_files_dir, altRemoteDir = None):
        try:
            try:
                if altRemoteDir is not None:
                    self.remote_dest_dir = self.addSlashtoPath(altRemoteDir)
                    # remoteFilesList = self.listRemoteFiles(altRemoteDir)
                    if not self.directoryExists(altRemoteDir):
                        self.createDir(altRemoteDir)
                else:
                    self.remote_dest_dir = self.nas_dest_dir
                    # remoteFilesList = self.listRemoteFiles()
                    if not self.directoryExists():
                        self.createDir()  
                localFilesList = self.listLocalFiles(local_files_dir)
            except Exception as error:
                errorMsg = "Could not create {} directory".format(self.remote_dest_dir)
                log.error(errorMsg)
                raise error
            remoteFilesList = self.listRemoteFiles(self.remote_dest_dir)
            try:
                try:
                    max_threads = mp.cpu_count() # Number of threads to use
                    total_files = len(self.listLocalFiles(local_files_dir))
                    chunk_size = total_files // max_threads # Number of files to retrieve per thread
                    chunks = [[] for _ in range(max_threads)]
                    for i in range(max_threads - 1):  # Split up data into chunks based on cpu resources
                        chunks[i] += localFilesList[chunk_size * i: chunk_size * (i + 1)]
                    chunks[-1] = localFilesList[chunk_size * (max_threads - 1):]
                    chunks = [chk for chk in chunks if chk] # For smaller amount of files, make sure to take out empty chunks
                except Exception as error:
                    errorMsg = "Could not split up data into chunks"
                    log.error(errorMsg)
                    raise error
                with ThreadPoolExecutor(max_workers=max_threads) as executor:      
                    # Create a list to hold the file retrieval tasks  
                    retrieval_tasks = []
                    conn = self.nas_connect()
                    for files_chunk in chunks:
                        conn = self.nas_connect()
                        task = executor.submit(self.store_and_save_files, local_files_dir, files_chunk, conn, remoteFilesList)
                        retrieval_tasks.append(task)
                    print("File Storage Loading...")
                # Wait for all tasks to complete  
                concurrent.futures.wait(retrieval_tasks)
                log.info("Finished adding files to the remote directory")
            except TypeError as e:  # if list returned is None
                if self.listRemoteFiles(local_files_dir) is None:
                    errorMsg = "Could not retrieve {} directory list".format(self.listRemoteFiles(local_files_dir))
                    log.error(errorMsg)
                if self.remote_dest_dir is None:
                    errorMsg = "Could not retrieve {} directory list".format(self.remote_dest_dir)
                    log.error(errorMsg)
                raise e
        except Exception as error:
            errorMsg = "Could not store files"
            log.critical(errorMsg)
            raise error
    def store_and_save_files(self, local_files_dir, files_chunk, conn, remoteFilesList):
        try:
            invalidChar = [":", "/", "\\", "?", "*"]#invalid characters for a filename
            for filename in files_chunk:
                self.containsInvalidChar = False
                if filename not in remoteFilesList:
                    if filename.endswith((".txt", ".dat", ".json")):
                        for char in invalidChar:
                            if char in filename:
                                self.containsInvalidChar = True
                                errorMsg = "Your file name {} contains {} which is an invalid character. Please change the file name".format(filename, char)
                                log.error(errorMsg)
                        if self.containsInvalidChar is False:
                            with open(os.path.join(local_files_dir, filename), 'rb') as fileObj:
                                conn.storeFile(self.nas_base, os.path.join(self.remote_dest_dir, filename), fileObj)
                    else:
                        errorMsg = "{} file is not a text or data file.".format(filename)
                        log.warning(errorMsg)
                        # print(errorMsg)
                else:
                    errorMsg = "{} already exists in the {} directory".format(filename, self.remote_dest_dir)
                    log.error(errorMsg)
        except Exception as error:  
            errorMsg = f"Could not retrieve file chunk. Error was: {error}"
            log.error(errorMsg)
            raise error
            
    def get_one_nas_file(self, local_retrieved_dir, nas_file_name, altRemoteDir = None):
        try:
            try:
                if altRemoteDir is not None:
                    remoteFileList = self.listRemoteFiles(altRemoteDir)
                    self.remote_dest_dir = self.addSlashtoPath(altRemoteDir)
                    if self.directoryExists(altRemoteDir) is False:
                        self.createDir(altRemoteDir)
                else:
                    remoteFileList = self.listRemoteFiles()
                    self.remote_dest_dir = self.nas_dest_dir
                    if self.directoryExists() is False:
                        self.createDir()
            except Exception as error:
                errorMsg = "Could not create {} directory".format(self.remote_dest_dir)
                log.error(errorMsg)
                raise error
            try:
                for filename in remoteFileList:
                    if nas_file_name == filename:
                        if filename not in self.listLocalFiles(local_retrieved_dir):
                            if filename.endswith((".txt", ".dat")):
                                with open(self.addSlashtoPath(local_retrieved_dir) + filename, "wb") as fileObj:
                                    self.conn.retrieveFile(self.nas_base, os.path.join(self.remote_dest_dir, nas_file_name), fileObj)
                                    infoMsg = "{} file retrieved from the remote directory".format(filename)
                                    log.info(infoMsg)
                            else:
                                errorMsg = "{} file is not a text or data file.".format(filename)
                                log.warning(errorMsg)
                        else:
                            errorMsg = "{} file already exists in the local directory".format(filename)
                            log.error(errorMsg)
                    else:
                        errorMsg = "{} file does not exists in the remote directory".format(filename)
                        log.error(errorMsg)
            except TypeError as e: # if list returned is None
                if self.listRemoteFiles() is None:
                    errorMsg = "Could not retrieve {} directory list".format(self.remote_dest_dir)
                elif self.listLocalFiles(local_retrieved_dir) is None:
                    errorMsg = "Could not retrieve {} directory list".format(local_retrieved_dir)
                log.error(errorMsg)
                raise e
        except Exception as error:
            errorMsg = f"Could not store file chunk. Error was: {error}"
            log.error(errorMsg)
            raise error
    def get_nas_files(self, local_retrieved_dir, altRemoteDir = None):
        # retrieve files differently based on directory size
        try:
            if altRemoteDir is not None:
                if len(self.listRemoteFiles(altRemoteDir)) > 100:
                    self.get_large_nas_files(local_retrieved_dir, altRemoteDir)
                else:
                    self.get_small_nas_files(local_retrieved_dir, altRemoteDir)
            else:
                if len(self.listRemoteFiles()) > 100:
                    self.get_large_nas_files(local_retrieved_dir)
                else:
                    self.get_small_nas_files(local_retrieved_dir)
        except Exception as error:
            errorMsg = f"Could not retrieve files. Error was: {error}"
            log.critical(errorMsg)
            raise error
    def get_small_nas_files(self, local_retrieved_dir, altRemoteDir = None):
        try:
            try:
                if not os.path.exists(local_retrieved_dir):
                    os.mkdir(local_retrieved_dir)
            except Exception as error:
                errorMsg = f"Could not create local directory {local_retrieved_dir}. Error was: {error}"
                log.error(errorMsg)
                raise error
            if altRemoteDir is not None:
                remoteFilesList = self.listRemoteFiles(altRemoteDir)
                self.remote_dest_dir = self.addSlashtoPath(altRemoteDir)
            else:
                remoteFilesList = self.listRemoteFiles()
                self.remote_dest_dir = self.nas_dest_dir
            try:
                for filename in remoteFilesList:
                    if filename not in self.listLocalFiles(local_retrieved_dir):
                        if filename.endswith((".txt", ".dat")):
                            with open(self.addSlashtoPath(local_retrieved_dir) + filename, "wb") as fileObj:
                                self.conn.retrieveFile(self.nas_base, self.remote_dest_dir + filename, fileObj)
                                if len(remoteFilesList) <= 10:
                                    infoMsg = "{} file retrieved from the remote directory".format(filename)
                                    log.info(infoMsg)
                        else:
                            errorMsg = "{} file is not a text or data file.".format(filename)
                            log.warning(errorMsg)
                    else:
                        errorMsg = "{} file already exists in the local directory".format(filename)
                        log.error(errorMsg)
                print("Finished retrieving files from the remote directory")
            except TypeError as e: # if list returned is None
                if self.remoteFilesList is None:
                    errorMsg = "Could not retrieve {} directory list".format(self.remote_dest_dir)
                elif self.listLocalFiles(local_retrieved_dir) is None:
                    errorMsg = "Could not retrieve {} directory list".format(local_retrieved_dir)
                log.error(errorMsg)
                raise e
        except Exception as error:
            errorMsg = "Could not retrieve {} file".format(filename)
            log.critical(errorMsg)
            raise error
    def get_large_nas_files(self, local_retrieved_dir, altRemoteDir=None): 
        try:
            try:
                if not os.path.exists(local_retrieved_dir):
                    os.mkdir(local_retrieved_dir)
            except Exception as error:
                errorMsg = "Could not create local directory {}".format(local_retrieved_dir)
                log.error(errorMsg)
                raise error
            if altRemoteDir is not None:  
                remoteFilesList = self.listRemoteFiles(altRemoteDir)  
                remote_dest_dir = self.addSlashtoPath(altRemoteDir)  
            else:  
                remoteFilesList = self.listRemoteFiles()  
                remote_dest_dir = self.nas_dest_dir
                
            try:
                try:
                    max_threads = mp.cpu_count() # Number of threads to use
                    total_files = len(remoteFilesList)
                    chunk_size = total_files // max_threads # Number of files to retrieve per thread
                    chunks = [[] for _ in range(max_threads)]
                    for i in range(max_threads - 1):  # Split up data into chunks based on cpu resources
                        chunks[i] += remoteFilesList[chunk_size * i: chunk_size * (i + 1)]
                    chunks[-1] = remoteFilesList[chunk_size * (max_threads - 1):]
                    chunks = [chk for chk in chunks if chk] # For smaller amount of files, make sure to take out empty chunks
                except Exception as error:
                    errorMsg = "Could not split up data into chunks"
                    log.error(errorMsg)
                    raise error
                with ThreadPoolExecutor(max_workers=max_threads) as executor:  
                    # Create a list to hold the file retrieval tasks  
                    retrieval_tasks = []
                    for files_chunk in chunks:
                        conn = self.nas_connect()
                        task = executor.submit(self.retrieve_and_save_files, local_retrieved_dir, remote_dest_dir, files_chunk, conn)
                        retrieval_tasks.append(task)
                    print("File Retrieval Loading...")
                    concurrent.futures.wait(retrieval_tasks)
    
                print("Finished retrieving files from the remote directory") 
            except TypeError as e:  # if list returned is None 
                errorMsg = "Could not retrieve {} directory list".format(remote_dest_dir)
                log.error(errorMsg)
                raise e
    
        except Exception as error:  
            errorMsg = f"Could not execute task in thread. Error was: {error}"
            log.error(errorMsg)
            raise error
    def retrieve_and_save_files(self, local_retrieved_dir, remote_dest_dir, files_chunk, conn):  
        try:
            for filename in files_chunk:
                if filename not in self.listLocalFiles(local_retrieved_dir):  
                    if filename.endswith((".txt", ".dat")):  
                        with open(self.addSlashtoPath(local_retrieved_dir) + filename, "wb") as fileObj:
                            conn.retrieveFile(self.nas_base, remote_dest_dir + filename, fileObj)
        except Exception as error:  
            errorMsg = f"Could not retrieve file chunk. Error was: {error}"
            log.error(errorMsg)
            raise error
    def createParentDir(self, curr_dir):
        try:
            self.parent_dir = os.path.dirname(self.removeSlashfromPath(curr_dir))# get parent directory
            if not self.directoryExists(self.parent_dir):
                self.createParentDir(self.parent_dir)
            self.conn.createDirectory(self.nas_base, curr_dir)
        except Exception as error:
            errorMsg = "Could not create {} directory".format(curr_dir)
            log.critical(errorMsg)
            raise error
    def createDir(self, altRemoteDir = None):
        try:
            if altRemoteDir is not None:
                self.remote_dest_dir = self.addSlashtoPath(altRemoteDir)
            else:
                self.remote_dest_dir = self.nas_dest_dir
            self.parent_dir = os.path.dirname(self.removeSlashfromPath(self.remote_dest_dir))# get parent directory
            if not self.directoryExists(self.parent_dir):
                self.createParentDir(self.parent_dir)
            if self.directoryExists() is False:
                self.conn.createDirectory(self.nas_base, self.remote_dest_dir)
                infoMsg = "{} directory created".format(self.remote_dest_dir)
                log.info(infoMsg)
            else:
                warnMsg = "{} directory already exists".format(self.remote_dest_dir)
                log.warning(warnMsg)
        except Exception as error:
            errorMsg = "Could not create {} directory".format(self.remote_dest_dir)
            log.critical(errorMsg)
            raise error
    def deleteDir(self, altRemoteDir = None):
        try:
            try:
                if altRemoteDir is not None:
                    self.remote_dest_dir = self.addSlashtoPath(altRemoteDir)
                    if self.directoryExists(altRemoteDir):
                        filesToDelete = self.listRemoteFiles(altRemoteDir)
                else:
                    self.remote_dest_dir = self.nas_dest_dir
                    if self.directoryExists():
                        filesToDelete = self.listRemoteFiles()
            except Exception as error:
                errorMsg = "{} directory does not exist".format(self.remote_dest_dir)
                log.error(errorMsg)
                raise error
            try:
                if len(filesToDelete) > 0:
                    if len(filesToDelete) > 50:
                        try:
                            max_threads = mp.cpu_count() # Number of threads to use
                            total_files = len(filesToDelete)
                            chunk_size = total_files // max_threads
                            chunks = [[] for _ in range(max_threads)]
                            for i in range(max_threads - 1):
                                chunks[i] += filesToDelete[chunk_size * i: chunk_size * (i + 1)]
                            chunks[-1] = filesToDelete[chunk_size * (max_threads - 1):]
                            chunks = [chk for chk in chunks if chk]
                        except Exception:
                            errorMsg = "Could not split up data into chunks"
                            log.error(errorMsg)
                        with ThreadPoolExecutor(max_workers=max_threads) as executor:
                            retrieval_tasks = []
                            for files_chunk in chunks:
                                conn = self.nas_connect()
                                task = executor.submit(self.deleteAllRemoteFiles, files_chunk, conn)
                                retrieval_tasks.append(task)
                            print("File Deletion Loading...")
                            # Wait for all tasks to complete
                            concurrent.futures.wait(retrieval_tasks)
                    else:
                        for file in filesToDelete:
                            self.conn.deleteFiles(self.nas_base, os.path.join(self.remote_dest_dir, file))
                            infoMsg = "{} file deleted".format(file)
                            log.info(infoMsg)
                    self.conn.deleteDirectory(self.nas_base, self.remote_dest_dir)
                    #may want to add timer since directory deletes slower with files
                else:
                    self.conn.deleteDirectory(self.nas_base, self.remote_dest_dir)
                infoMsg = "{} directory deleted.\nPlease wait a few minutes for all the files to disappear from the remote directory.".format(self.remote_dest_dir)
                log.info(infoMsg)
            except TypeError as e:
                errorMsg = "Could not retrieve {} directory list".format(self.remote_dest_dir)
                log.error(errorMsg)
                raise e
        except Exception as error:
            errorMsg = "Could not delete {} directory".format(self.remote_dest_dir)
            log.critical(errorMsg)
            raise error
    def deleteAllRemoteFiles(self, chunks, conn):
        try:
            for file in chunks:
                conn.deleteFiles(self.nas_base, os.path.join(self.remote_dest_dir, file))
        except Exception as error:
            errorMsg = "Could not delete {} file".format(file)
            log.critical(errorMsg)
            raise error
    def deleteRemoteFile(self, nas_file_name, altRemoteDir = None):
        if altRemoteDir is not None:
            self.remote_dir = self.addSlashtoPath(altRemoteDir)
        else:
            self.remote_dir = self.nas_dest_dir
        try:
            try:
                if nas_file_name in self.listRemoteFiles():
                    self.conn.deleteFiles(self.nas_base, os.path.join(self.remote_dir, nas_file_name))
                    print("{} file deleted".format(nas_file_name))
                else:
                    errorMsg = "{} does not exist in the {} directory".format(nas_file_name, self.remote_dir)
                    log.error(errorMsg)
            except TypeError as e:
                errorMsg = "Could not retrieve {} directory list".format(self.remote_dir)
                log.error(errorMsg)
                raise e
        except Exception as error:
            errorMsg = "Could not delete {} file".format(nas_file_name)
            log.critical(errorMsg)
            raise error
    def listRemoteFiles(self, altRemoteDir = None):
        try:
            if altRemoteDir is not None:
                self.remote_dir = self.addSlashtoPath(altRemoteDir)
                self.directoryExistsCheck = self.directoryExists(altRemoteDir)
            else:
                self.remote_dir = self.nas_dest_dir
                self.directoryExistsCheck = self.directoryExists()
            try:
                if self.directoryExistsCheck:
                    self.destDirList = self.conn.listPath(self.nas_base, self.remote_dir)
                    self.fileList = []
                    for file in self.destDirList:
                        if file.filename.endswith(("txt", "dat")):
                            self.fileList.append(file.filename)
                    return self.fileList
            except TypeError as e:
                errorMsg = "{} directory doesn't exist".format(self.remote_dir)
                log.error(errorMsg)
                raise e
        except Exception as error:
            errorMsg = "Could not retrieve {} directory list".format(self.remote_dir)
            log.critical(errorMsg)
            raise error
    def directoryExists(self, altRemoteDir = None):
        if altRemoteDir is not None:
            self.remote_dir = self.addSlashtoPath(altRemoteDir)
        else:
            self.remote_dir = self.addSlashtoPath(self.nas_dest_dir)
        self.path = os.path.dirname(self.removeSlashfromPath(self.remote_dir))# get parent directory
        self.dirList = self.conn.listPath(self.nas_base, self.addSlashtoPath(self.path))
        self.inDirectory = False
        for dir in self.dirList:
            if dir.filename == self.remote_dir.split("/")[-2]:
                self.inDirectory = True
        return self.inDirectory
    def listLocalFiles(self, local_files_dir):
        try:
            local_files = os.listdir(local_files_dir)
            return local_files
        except Exception as error:
            errorMsg = f"Error retrieving {local_files_dir} local directory files: {error}"
            log.error(errorMsg)
            raise error
    # Case to add slash to NAS destination directory
    def addSlashtoPath(self, path):
        try:
            if path.endswith("/"):
                return path
            else:
                return path + "/"
        except Exception:
            errorMsg = "Could not add slash to {} path".format(path)
            log.error(errorMsg)
    # Case to remove slash to NAS destination directory
    def removeSlashfromPath(self, path):
        try:
            if path.endswith("/"):
                return path[:-1]
            else:
                return path
        except Exception:
            errorMsg = "Could not remove slash from {} path".format(path)
            log.error(errorMsg)