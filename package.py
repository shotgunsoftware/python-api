name = 'shotgunPythonApi'
version = 'rc.3.0.34.mikros.1.0'

# Note for core pipeline team
# Be sure that the same modifications are in both this api
# and shotgun api included in tank core
# eg. semi private shotgun support

def commands():
    
    env.PYTHONPATH.append('{root}')
