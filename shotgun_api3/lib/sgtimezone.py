#! /opt/local/bin/python
# ----------------------------------------------------------------------------
#  SG_TIMEZONE module
#  this is rolled into the this shotgun api file to avoid having to require 
#  current users of api2 to install new modules and modify PYTHONPATH info.
# ----------------------------------------------------------------------------

class SgTimezone(object):
    from datetime import tzinfo, timedelta, datetime
    import time as _time

    ZERO = timedelta(0)
    STDOFFSET = timedelta(seconds = -_time.timezone)
    if _time.daylight:
        DSTOFFSET = timedelta(seconds = -_time.altzone)
    else:
        DSTOFFSET = STDOFFSET
    DSTDIFF = DSTOFFSET - STDOFFSET
    
    def __init__(self): 
        self.utc = self.UTC()
        self.local = self.LocalTimezone()
    
    class UTC(tzinfo):
        
        def utcoffset(self, dt):
            return SgTimezone.ZERO
        
        def tzname(self, dt):
            return "UTC"
        
        def dst(self, dt):
            return SgTimezone.ZERO
    
    class LocalTimezone(tzinfo):
        
        def utcoffset(self, dt):
            if self._isdst(dt):
                return SgTimezone.DSTOFFSET
            else:
                return SgTimezone.STDOFFSET
        
        def dst(self, dt):
            if self._isdst(dt):
                return SgTimezone.DSTDIFF
            else:
                return SgTimezone.ZERO
        
        def tzname(self, dt):
            return _time.tzname[self._isdst(dt)]
        
        def _isdst(self, dt):
            tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
            import time as _time
            stamp = _time.mktime(tt)
            tt = _time.localtime(stamp)
            return tt.tm_isdst > 0

