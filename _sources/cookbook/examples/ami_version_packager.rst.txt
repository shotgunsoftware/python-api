.. _ami_version_packager:

########################################################
Using an ActionMenuItem to Package Versions for a Client
########################################################

This is an example script to demonstrate how you can use an ActionMenuItem to launch a local 
script to package up files for a client. It performs the following:

-  Downloads Attachments from a specified field for all selected entities.
-  Creates an archive.
-  Copies the archive to a specified directory.

It is intended to be used in conjunction with the script dicussed in :ref:`ami_handler`.

::

    #!/usr/bin/env python
    # encoding: utf-8
    """
    version_packager.py

    This example script is meant to be run from an ActionMenuItem in Flow Production Tracking. The menu item uses a custom
    protocol in order to launch this script, and is followed by the action 'package4client'. So the full
    url would be something like launchme://package4client?.... See:
    https://developer.shotgridsoftware.com/python-api/cookbook/examples/ami_handler.html

    It uses the example ActionMenu Python class also located in our docs for parsing the ActionMenuItem
    POST variables. For more information about it and accessing the variables in the ActionMenuItem POST request,
    See: http://developer.shotgridsoftware.com/python-api/examples/ami_handler

    The purpose of this script is to download attachment files from Flow Production Tracking, create an archive of them
    and copy them to a specified directory. You can invoke it with the following minimal example to connect
    to Flow Production Tracking, download any file that exists in the specified field ('sg_qt') for each selected_id passed from the
    ActionMenu. Then it will create a single archive of the files and move it to the specified directory
    ('/path/where/i/want/to/put/the/archive/'). The archive is named with the Project Name, timestamp, and user
    login who ran the ActionMenuItem ('Demo_Project_2010-04-29-172210_kp.tar.gz'):

        sa = ShotgunAction(sys.argv[1])
        sg = shotgun_connect()    
        if sa.action == 'package4client':
            r = packageFilesForClient('sg_qt','/path/where/i/want/to/put/the/archive/')
     
    """

    # ---------------------------------------------------------------------------------------------
    # Imports
    # ---------------------------------------------------------------------------------------------
    import sys, os
    import logging as logger
    import subprocess
    import re
    from datetime import datetime

    from shotgun_api3 import Shotgun
    from shotgun_action import ShotgunAction
    from pprint import pprint

    # ---------------------------------------------------------------------------------------------
    # Variables
    # ---------------------------------------------------------------------------------------------
    # Flow Production Tracking server auth info
    shotgun_conf = {
        'url':'https://my-site.shotgrid.autodesk.com', 
        'name':'YOUR_SCRIPT_NAME_HERE', 
        'key':'YOUR_SCRIPT_KEY_HERE'
        }

    # location to write logfile for this script
    logfile = os.path.dirname(sys.argv[0])+"/version_packager.log"

    # temporary directory to download movie files to and create thumbnail files in
    file_dir = os.path.dirname(sys.argv[0])+"/tmp" 

    # compress command 
    # tar czf /home/user/backup_www.tar.gz -C / var/www/html
    compress_cmd = "tar czf %s -C / %s"



    # ----------------------------------------------
    # Generic Flow Production Tracking Exception Class
    # ----------------------------------------------
    class ShotgunException(Exception):
        pass



    # ----------------------------------------------
    # Set up logging
    # ----------------------------------------------
    def init_log(filename="version_packager.log"):    
        try:
            logger.basicConfig(level=logger.DEBUG,
                            format='%(asctime)s %(levelname)-8s %(message)s',
                            datefmt='%Y-%b-%d %H:%M:%s',
                            filename=filename,
                            filemode='w+')
        except IOError, e:
            raise ShotgunException ("Unable to open logfile for writing: %s" % e)
        logger.info("Version Packager logging started.") 
        return logger   


    # ----------------------------------------------
    # Extract Attachment id from entity field
    # ----------------------------------------------
    def extract_attachment_id(attachment):
        # extract the Attachment id from the url location
        attachment_id = attachment['url'].rsplit('/',1)[1]
        try:
            attachment_id = int(attachment_id)
        except:
            # not an integer. 
            return None
            # raise ShotgunException("invalid Attachment id returned. Expected an integer: %s "% attachment_id)   

        return attachment_id


    # ----------------------------------------------
    # Download Movie to Disk
    # ----------------------------------------------
    def download_attachment_to_disk(attachment,destination_filename):
        attachment_id = extract_attachment_id(attachment)
        if type(attachment_id) != int:
            return None
        # download the attachment file from Flow Production Tracking and write it to local disk
        logger.info("Downloading Attachment #%s" % (attachment_id)) 
        stream = sg.download_attachment(attachment_id)
        try:
            file = open(destination_filename, 'w')
            file.write(stream)
            file.close()
            logger.info("Downloaded attachment %s" % (destination_filename))
            return True 
        except e:
            raise ShotgunException("unable to write attachment to disk: %s"% e)   


    # ----------------------------------------------
    # Compress files
    # ----------------------------------------------
    def compress_files(files,destination_filename):
        destination_filename += ".tar.gz"
        files = [path.lstrip("/") for path in files]
        squish_me = compress_cmd % (destination_filename, " ".join(files) )
        logger.info("Compressing %s files..." % len(files))
        logger.info("Running command: %s" % squish_me)
        try:
            output = subprocess.Popen(squish_me, shell=True, stdout=subprocess.PIPE).stdout.read()
            logger.info('tar/gzip command returned: %s' % output)
        except e:
            raise ShotgunException("unable compress files: %s"% e)
        logger.info("compressed files to: %s" % destination_filename)
        return destination_filename


    # ----------------------------------------------
    # Remove downloaded files
    # ----------------------------------------------
    def remove_downloaded_files(files):
        remove_me = 'rm %s' % ( " ".join(files) )
        logger.info("Removing %s files..." % len(files))
        logger.info("Running command: %s" % remove_me)
        try:
            output = subprocess.Popen(remove_me, shell=True, stdout=subprocess.PIPE).stdout.read()
            logger.info('rm command returned: %s' % output)
            logger.info("removed downloaded files")
            return True
        except e:
            logger.error("unable remove files: %s"% e)
            return False


    # ----------------------------------------------
    # Copy files
    # ----------------------------------------------
    def copy_files(files,destination_directory):
        if type(files) == list:
            files = " ".join(files)
        copy_me_args = "%s %s" % (files, destination_directory)
        logger.info("Running command: mv %s" % copy_me_args)
        try:
            result = subprocess.Popen("mv " + copy_me_args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # 0 = success, 1 = recoverable issues
            if result.returncode > 0:
                response = result.stderr.read()
                logger.error("Copy failed: %s"% response)
                raise ShotgunException("Copy failed: %s"% response)
        except OSError, e:
            raise ShotgunException("unable copy files: %s"% e)

        logger.info("copied files to: %s" % destination_directory)
        return destination_directory

        
        
    def packageFilesForClient(file_field,destination_dir):
        
        # get entities matching the selected ids    
        logger.info("Querying Shotgun for %s %ss" % (len(sa.selected_ids_filter), sa.params['entity_type'])) 
        entities = sg.find(sa.params['entity_type'],sa.selected_ids_filter,['id','code',file_field],filter_operator='any')
        
        # download the attachments for each entity, zip them, and copy to destination directory
        files = []
        for e in entities:
            if not e[file_field]:
                logger.info("%s #%s: No file exists. Skippinsa." % (sa.params['entity_type'], e['id'])) 
            else:
                logger.info("%s #%s: %s" % (sa.params['entity_type'], e['id'], e[file_field])) 
                path_to_file = file_dir+"/"+re.sub(r"\s+", '_', e[file_field]['name'])
                result = download_attachment_to_disk(e[file_field], path_to_file )           
                
                # only include attachments. urls won't return true
                if result:
                    files.append(path_to_file)
                
        # compress files
        # create a nice valid destination filename
        project_name = ''
        if 'project_name' in sa.params:
            project_name = re.sub(r"\s+", '_', sa.params['project_name'])+'_'
        dest_filename = project_name+datetime.today().strftime('%Y-%m-%d-%H%M%S')+"_"+sa.params['user_login']
        archive = compress_files(files,file_dir+"/"+dest_filename)
        
        # now that we have the archive, remove the downloads
        r = remove_downloaded_files(files)

        # copy to directory
        result = copy_files([archive],destination_dir)

        return True

            
    # ----------------------------------------------
    # Main Block
    # ----------------------------------------------
    if __name__ == "__main__":
        init_log(logfile)
        
        try:
            sa = ShotgunAction(sys.argv[1])
            logger.info("Firing... %s" % (sys.argv[1]) )
        except IndexError, e:
            raise ShotgunException("Missing POST arguments")
        
        sg = Shotgun(shotgun_conf['url'], shotgun_conf['name'], shotgun_conf['key'],convert_datetimes_to_utc=convert_tz) 
        
        if sa.action == 'package4client':
            result = packageFilesForClient('sg_qt','/Users/kp/Documents/shotgun/dev/api/files/')
        else:
            raise ShotgunException("Unknown action... :%s" % sa.action)
            
        
        print("\nVersion Packager done!")

