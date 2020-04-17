Currently this library is pulled from a fork of httplib2 (https://github.com/shotgunsoftware/httplib2)

The reason for the fork is to make a minor fix to the imports that was causing IronPython2.7 ImportErrors. 

The fix has been submitted to httplib2 repo and already merged so this will likely not be necessary as soon as httplib2 is next released. (>v0.17.2) 