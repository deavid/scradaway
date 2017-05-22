import os
import os.path

class XMLStructConfig(object):
    def __init__(self, xmltype = str, xmlsubtype = None, fntype = None, default = None):
        self.xmltype = xmltype
        self.xmlsubtype = xmlsubtype
        self.fntype = fntype
        self.default = default
    
    def formatNode(self, child):
        value = self._formatNode(child)
        if self.fntype: value = self.fntype(value)
        return value
        
    def _formatNode(self, child):
        if self.xmltype is str: return str(child.text).strip()
        if self.xmltype is int: return int(str(child.text).strip())
    
        value = None
            
        if self.xmltype is list:
            value = []
            for subchild in child:
                if issubclass(self.xmlsubtype, XMLStruct):
                    subvalue = self.xmlsubtype(subchild)
                else:
                    raise ValueError("Unsupported struct config: %r->%r" % (self.xmltype, self.xmlsubtype))
                value.append(subvalue)
                
        return value

class XMLStruct(object):
    """
        Helper which reads nodes and writtes attrs easily.
    """
    def __init__(self, xmlobj=None):
        self._attrs = []
        if xmlobj is None:
            raise ValueError("Invalid construction without XML Object")
        
        if xmlobj.tag is None:
            raise ValueError("Invalid construction XML Object without tag")
        self.__name__ = xmlobj.tag

        for k in dir(self):
            if k.startswith("_"): continue
            obj = getattr(self.__class__, k)
            if hasattr(obj, "default"):
                setattr(self, k, obj.default)
                    
        for child in xmlobj:
            key = str(child.tag).replace("-","_")
            if "<" in key: continue
            if not hasattr(self.__class__, key):  continue
        
            defvalue = getattr(self.__class__, key)
            
            if isinstance(defvalue, XMLStructConfig): 
                structconfig = defvalue
            else:
                structconfig = XMLStructConfig(xmltype=type(defvalue))
                
            value = structconfig.formatNode(child)
            setattr(self, key, value)
            self._attrs.append(key)

    def __str__(self):
        attrs = [ "%s=%s" % (str(k),repr(getattr(self,k))) for k in self._attrs if isinstance(k,str)]
        txtattrs = " ".join(attrs)
        return "<%s.%s %s>" % (self.__class__.__name__, self.__name__, txtattrs)

    def __repr__(self):
        return self.__str__()

    def _v(self, k, default=None):
        return getattr(self, k, default)


def filedir(*path):
    """  filedir(path1[, path2, path3 , ...])

        Return a path relative to this python filedir
    """
    return os.path.realpath(os.path.join(os.path.dirname(__file__), *path))

def one(x, default = None):
    """ Se le pasa una lista de elementos (normalmente de un xml) y devuelve el primero o None; sirve para ahorrar try/excepts y limpiar código"""
    try:
        return x[0]
    except IndexError:
        return default
